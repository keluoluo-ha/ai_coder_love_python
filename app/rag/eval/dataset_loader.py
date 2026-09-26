import json
from pathlib import Path

from app.rag.eval.models import RagEvalCase, RagEvalDataset


class DatasetLoader:
    def load(self, path: str | Path) -> RagEvalDataset:
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        cases = tuple(
            RagEvalCase(
                case_id=str(item["id"]),
                query=str(item["query"]),
                relevant_docs=tuple(str(doc) for doc in item["relevant_docs"]),
                k=int(item.get("k", 3)),
            )
            for item in data["cases"]
        )
        if not cases:
            raise ValueError("RAG evaluation dataset has no cases")
        return RagEvalDataset(name=str(data.get("name", source.stem)), cases=cases)
