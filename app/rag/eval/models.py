from dataclasses import dataclass


@dataclass(frozen=True)
class RagEvalCase:
    case_id: str
    query: str
    relevant_docs: tuple[str, ...]
    k: int = 3


@dataclass(frozen=True)
class RagEvalDataset:
    name: str
    cases: tuple[RagEvalCase, ...]
