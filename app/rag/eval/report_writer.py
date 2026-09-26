import json
from dataclasses import asdict
from pathlib import Path

from app.rag.eval.retrieval_evaluator import RetrievalReport


class ReportWriter:
    def write_json(self, report: RetrievalReport, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
        return destination

    def to_text(self, report: RetrievalReport) -> str:
        lines = [
            f"dataset: {report.dataset_name}",
            f"cases: {report.case_count}",
            f"Hit@k: {report.hit_at_k:.4f}",
            f"MRR: {report.mrr:.4f}",
            f"Recall@k: {report.recall_at_k:.4f}",
            "cases:",
        ]
        for case in report.cases:
            lines.append(
                f"  {case.case_id}: Hit@k={case.hit_at_k:.0f} "
                f"RR={case.reciprocal_rank:.4f} Recall@k={case.recall_at_k:.4f}"
            )
        return "\n".join(lines)

    def write_text(self, report: RetrievalReport, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.to_text(report), encoding="utf-8")
        return destination
