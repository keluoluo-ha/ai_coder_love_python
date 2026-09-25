from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import PDF_SAVE_DIR

router = APIRouter(prefix="/files", tags=["files"])


def _pdf_dir() -> Path:
    path = Path(PDF_SAVE_DIR).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_pdf_path(filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持下载 PDF 文件")
    candidate = (_pdf_dir() / filename).resolve()
    try:
        candidate.relative_to(_pdf_dir())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="路径越界") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return candidate


@router.get("/pdf/list")
def list_pdfs():
    files = sorted(
        path.name
        for path in _pdf_dir().iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    return {"directory": str(_pdf_dir()), "files": files}


@router.get("/pdf/{filename}")
def download_pdf(filename: str):
    path = _safe_pdf_path(filename)
    return FileResponse(path, media_type="application/pdf", filename=path.name)
