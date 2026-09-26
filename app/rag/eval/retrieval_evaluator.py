from collections.abc import Callable
from dataclasses import dataclass

from app.rag.eval.models import RagEvalCase, RagEvalDataset

Retriever = Callable[[str, int], list[str]]


@dataclass(frozen=True)
class RetrievalMetrics:
    case_id: str
    hit_at_k: float
    reciprocal_rank: float
    recall_at_k: float
    retrieved_docs: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalReport:
    dataset_name: str
    case_count: int
    hit_at_k: float
    mrr: float
    recall_at_k: float
    cases: tuple[RetrievalMetrics, ...]


class RetrievalEvaluator:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever

    def evaluate(self, dataset: RagEvalDataset) -> RetrievalReport:
        metrics = tuple(self._evaluate_case(case) for case in dataset.cases)
        count = len(metrics)
        return RetrievalReport(
            dataset_name=dataset.name,
            case_count=count,
            hit_at_k=sum(item.hit_at_k for item in metrics) / count,
            mrr=sum(item.reciprocal_rank for item in metrics) / count,
            recall_at_k=sum(item.recall_at_k for item in metrics) / count,
            cases=metrics,
        )

    def _evaluate_case(self, case: RagEvalCase) -> RetrievalMetrics:
        retrieved = tuple(self.retriever(case.query, case.k)[: case.k])
        relevant = set(case.relevant_docs)
        hits = [index for index, doc_id in enumerate(retrieved, start=1) if doc_id in relevant]
        hit_count = len(hits)
        return RetrievalMetrics(
            case_id=case.case_id,
            hit_at_k=1.0 if hit_count else 0.0,
            reciprocal_rank=1.0 / hits[0] if hits else 0.0,
            recall_at_k=hit_count / len(relevant) if relevant else 0.0,
            retrieved_docs=retrieved,
        )
