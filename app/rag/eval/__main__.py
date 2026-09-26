import argparse
import re
from pathlib import Path

from app.rag.eval.dataset_loader import DatasetLoader
from app.rag.eval.report_writer import ReportWriter
from app.rag.eval.retrieval_evaluator import RetrievalEvaluator

DEFAULT_DATASET = Path(__file__).with_name("default_dataset.json")
DEFAULT_REPORT = Path("rag_eval_report.txt")
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


def keyword_retriever(query: str, k: int) -> list[str]:
    terms = set(re.findall(r"[A-Za-z0-9]{2,}", query.lower()))
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]+", query))
    for size in (2, 3, 4):
        terms.update(chinese[index:index + size] for index in range(max(0, len(chinese) - size + 1)))
    expansions = {"退款": "退款 退货", "密码": "密码 忘记密码", "价格": "价格 套餐", "未授权": "401 未授权"}
    for term, expansion in expansions.items():
        if term in query:
            terms.update(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]+", expansion.lower()))
    scored: list[tuple[int, str]] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").lower()
        score = sum(text.count(term) for term in terms)
        scored.append((score, path.name))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [name for score, name in scored[:k] if score > 0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline RAG retrieval evaluation")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    dataset = DatasetLoader().load(args.dataset)
    report = RetrievalEvaluator(keyword_retriever).evaluate(dataset)
    text_path = ReportWriter().write_text(report, args.output)
    json_path = ReportWriter().write_json(report, Path(args.output).with_suffix(".json"))
    print(ReportWriter().to_text(report))
    print(f"report_text={text_path.resolve()}")
    print(f"report_json={json_path.resolve()}")


if __name__ == "__main__":
    main()
