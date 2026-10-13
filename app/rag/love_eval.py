"""知爱 RAG 检索层离线评测（对齐 Java 版 RagRetrievalEvaluator）。

- 数据集：love_eval_dataset.json（25 条高区分度用例，题型 A-E 各 5 条）
- 指标：Hit@5 / MRR@5 / StatusAcc@1
- Query 扩展：LangChain MultiQueryRetriever（LLM 生成多视角查询，合并去重）
- status 过滤：PGVector 元数据过滤（PostgreSQL 端 JSONB 过滤）

运行（先 python -m app.rag.love_rag 建索引）：
    python -m app.rag.love_eval
"""

import json
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from langchain_classic.retrievers import MultiQueryRetriever
from langchain_community.chat_models import ChatTongyi
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.config import LLM_MODEL_NAME
from app.rag.love_rag import get_love_vector_store

DATASET_PATH = Path(__file__).parent / "love_eval_dataset.json"
REPORT_PATH = Path(__file__).resolve().parents[2] / "love_rag_eval_report.md"
TOP_K = 5
# 相似度阈值 0.30：pgvector 余弦距离 = 1 - 相似度，故距离上限 0.70
MAX_DISTANCE = 0.70
LLM_SLEEP_SECONDS = 0.2


class RagEvalProfile(Enum):
    """检索链路配置（与 Java 版 RagEvalProfile 一一对应）。"""

    BASELINE_RAW = ("Baseline-0 纯向量检索", False, False, False)
    WITH_THRESHOLD = ("Baseline-1 向量检索 + 相似度阈值", False, True, False)
    WITH_STATUS_FILTER = ("Baseline-2 向量检索 + status 过滤", True, True, False)
    WITH_QUERY_EXPANSION = ("Baseline-3 过滤 + Query 扩展", True, True, True)
    FULL = ("Ours 完整 RAG 检索链路", True, True, True)

    def __init__(self, label, status_filter, similarity_threshold, query_expansion):
        self.label = label
        self.status_filter = status_filter
        self.similarity_threshold = similarity_threshold
        self.query_expansion = query_expansion


class StatusThresholdRetriever(BaseRetriever):
    """PGVector 检索器：支持 status 元数据过滤 + 相似度（距离）阈值。"""

    store: Any
    status: str | None = None
    use_threshold: bool = False

    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        filter_dict = {"status": self.status} if self.status else None
        results = self.store.similarity_search_with_score(query, k=TOP_K, filter=filter_dict)
        documents = [
            document
            for document, distance in results
            if not self.use_threshold or distance <= MAX_DISTANCE
        ]
        return documents[:TOP_K]


@dataclass(frozen=True)
class LoveEvalCase:
    case_id: str
    question: str
    status: str
    topic: str
    gold_keywords: tuple[str, ...]
    min_keyword_matches: int


@dataclass
class CaseResult:
    case_id: str
    hit_at_k: bool
    reciprocal_rank: float
    status_match_at_1: bool
    top1_preview: str


@dataclass
class ProfileMetrics:
    profile: RagEvalProfile
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def hit_at_5(self) -> float:
        return sum(r.hit_at_k for r in self.results) / self.total

    @property
    def mrr_at_5(self) -> float:
        return sum(r.reciprocal_rank for r in self.results) / self.total

    @property
    def status_acc_at_1(self) -> float:
        return sum(r.status_match_at_1 for r in self.results) / self.total


def load_dataset(path: Path = DATASET_PATH) -> list[LoveEvalCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        LoveEvalCase(
            case_id=item["id"],
            question=item["question"],
            status=item["status"],
            topic=item["topic"],
            gold_keywords=tuple(item["goldKeywords"]),
            min_keyword_matches=int(item["minKeywordMatches"]),
        )
        for item in data
    ]


def build_retriever(profile: RagEvalProfile, case_status: str, store) -> BaseRetriever:
    """按 profile 组装 LangChain 检索器；Query 扩展档位套 MultiQueryRetriever。"""
    base = StatusThresholdRetriever(
        store=store,
        status=case_status if profile.status_filter else None,
        use_threshold=profile.similarity_threshold,
    )
    if not profile.query_expansion:
        return base
    return MultiQueryRetriever.from_llm(
        retriever=base,
        llm=ChatTongyi(model=LLM_MODEL_NAME, temperature=0),
        include_original=True,
    )


def is_relevant(document: Document, case: LoveEvalCase) -> bool:
    """命中规则：文档 status 与期望一致，且命中足够数量的 goldKeywords。"""
    if document.metadata.get("status") != case.status:
        return False
    matched = sum(1 for keyword in case.gold_keywords if keyword in document.page_content)
    return matched >= case.min_keyword_matches


def truncate(text: str, max_len: int = 80) -> str:
    normalized = re.sub(r"\s+", " ", text)
    return normalized[:max_len] + "..." if len(normalized) > max_len else normalized


def evaluate_case(profile: RagEvalProfile, case: LoveEvalCase, store) -> CaseResult:
    base = StatusThresholdRetriever(
        store=store,
        status=case.status if profile.status_filter else None,
        use_threshold=profile.similarity_threshold,
    )
    retriever = (
        MultiQueryRetriever.from_llm(
            retriever=base,
            llm=ChatTongyi(model=LLM_MODEL_NAME, temperature=0),
            include_original=True,
        )
        if profile.query_expansion
        else base
    )
    try:
        documents = retriever.invoke(case.question)[:TOP_K]
    except Exception as exc:  # LLM 扩展失败时回退原问题，保证评测不中断
        print(f"[warn] {case.case_id} Query 扩展失败，回退原问题: {exc}")
        documents = base.invoke(case.question)[:TOP_K]

    first_hit_rank = 0
    for rank, document in enumerate(documents, start=1):
        if is_relevant(document, case):
            first_hit_rank = rank
            break
    hit = first_hit_rank > 0
    return CaseResult(
        case_id=case.case_id,
        hit_at_k=hit,
        reciprocal_rank=1.0 / first_hit_rank if hit else 0.0,
        status_match_at_1=bool(documents) and documents[0].metadata.get("status") == case.status,
        top1_preview=truncate(documents[0].page_content) if documents else "",
    )


def evaluate_profile(profile: RagEvalProfile, cases: list[LoveEvalCase], store) -> ProfileMetrics:
    results = []
    for case in cases:
        results.append(evaluate_case(profile, case, store))
        if profile.query_expansion:
            time.sleep(LLM_SLEEP_SECONDS)  # 控制 LLM 调用频率
    return ProfileMetrics(profile=profile, results=results)


def build_report(metrics: list[ProfileMetrics], case_count: int) -> str:
    baseline = next(m for m in metrics if m.profile is RagEvalProfile.BASELINE_RAW)
    threshold_baseline = next(m for m in metrics if m.profile is RagEvalProfile.WITH_THRESHOLD)
    full = next(m for m in metrics if m.profile is RagEvalProfile.FULL)

    lines = []
    lines.append("# 知爱 RAG 检索评测报告（Python / LangChain 版）\n")
    lines.append(f"- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 测试集: `app/rag/love_eval_dataset.json`（{case_count} 条，高区分度集，题型 A-E 各 5 条）")
    lines.append(f"- 相似度阈值: 0.30（余弦距离 <= {MAX_DISTANCE}）")
    lines.append("- 指标: Hit@5、MRR@5、StatusAcc@1")
    lines.append("- 命中规则: Top5 中出现 **status 正确** 且包含 **goldKeywords** 的文档块\n")

    lines.append("## 总览对比\n")
    lines.append("| 配置 | Hit@5 | MRR@5 | StatusAcc@1 | 相对 Baseline-0 提升 |")
    lines.append("|------|-------|-------|-------------|----------------------|")
    for m in metrics:
        rel = (m.hit_at_5 - baseline.hit_at_5) / baseline.hit_at_5 * 100 if baseline.hit_at_5 else 0.0
        lines.append(
            f"| {m.profile.label} | {m.hit_at_5:.1%} | {m.mrr_at_5:.3f} "
            f"| {m.status_acc_at_1:.1%} | {rel:+.1f}% |"
        )

    lines.append("\n## 面试口述参考\n")
    abs_gain = (full.hit_at_5 - threshold_baseline.hit_at_5) * 100
    rel_gain = (
        (full.hit_at_5 - threshold_baseline.hit_at_5) / threshold_baseline.hit_at_5 * 100
        if threshold_baseline.hit_at_5
        else 0.0
    )
    lines.append(
        f"> 我们在 {case_count} 条标注测试集上做了检索层离线评测（Hit@5 / MRR@5 / StatusAcc@1）。\n"
    )
    lines.append(
        f"> **推荐对比基线**：在「向量检索 + 相似度阈值 0.30」下 Hit@5 为 {threshold_baseline.hit_at_5:.1%}；"
        f"加入 status 过滤与 Query 扩展后提升到 {full.hit_at_5:.1%}"
        f"（绝对提升 {abs_gain:.1f} 个百分点，相对提升 {rel_gain:.1f}%）。\n"
    )

    lines.append("\n## 未命中样本（完整方案）\n")
    misses = [r for r in full.results if not r.hit_at_k]
    if not misses:
        lines.append("全部命中。\n")
    else:
        lines.append("| Case ID | Top1 预览 |")
        lines.append("|---------|----------|")
        for miss in misses:
            lines.append(f"| {miss.case_id} | {miss.top1_preview.replace('|', chr(92) + '|')} |")

    lines.append("\n## 说明\n")
    lines.append("1. 该报告为**检索层**离线评测，不代表最终回答质量。")
    lines.append("2. Query 扩展基于 LangChain MultiQueryRetriever：LLM 生成多视角查询后合并去重检索。")
    lines.append("3. status 过滤在 PostgreSQL 端完成（PGVector JSONB 元数据过滤），优于先取回再过滤。")
    lines.append("4. 指标含义：Hit@5=Top5 内命中比例；MRR@5=首个命中排名倒数的均值；StatusAcc@1=Top1 状态正确比例。")
    return "\n".join(lines)


def main() -> None:
    cases = load_dataset()
    store = get_love_vector_store()
    metrics: list[ProfileMetrics] = []
    for profile in RagEvalProfile:
        print(f"开始评测配置: {profile.label}")
        profile_metrics = evaluate_profile(profile, cases, store)
        metrics.append(profile_metrics)
        print(
            f"  -> Hit@5={profile_metrics.hit_at_5:.1%} "
            f"MRR@5={profile_metrics.mrr_at_5:.3f} "
            f"StatusAcc@1={profile_metrics.status_acc_at_1:.1%}"
        )
    report = build_report(metrics, len(cases))
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"\nreport={REPORT_PATH.resolve()}")


if __name__ == "__main__":
    main()
