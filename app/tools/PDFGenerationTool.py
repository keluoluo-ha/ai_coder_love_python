from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base_tool import BaseTool


class PDFGenerationInput(BaseModel):
    title: str = Field(description="报告标题")
    content: str = Field(description="报告正文")
    filename: str = Field(default="love_report.pdf", description="输出文件名")


class PDFGenerationTool(BaseTool):
    name: str = "pdf_generate"
    description: str = "生成恋爱咨询报告 PDF 并返回文件路径"
    parameters: type[BaseModel] = PDFGenerationInput

    def __init__(self, output_dir: str | Path = "pdf_reports"):
        self.output_dir = Path(output_dir).resolve()

    async def execute(self, title: str, content: str, filename: str = "love_report.pdf") -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.enums import TA_CENTER

        if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
            raise ValueError("filename must be a simple PDF filename")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / filename

        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        title_style.alignment = TA_CENTER
        body_style = styles["BodyText"]
        font_name = "Helvetica"
        for font_path in (
            "C:/Windows/Fonts/msyh.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ):
            if Path(font_path).exists():
                try:
                    pdfmetrics.registerFont(TTFont("LoveReportFont", font_path))
                    font_name = "LoveReportFont"
                    title_style.fontName = font_name
                    body_style.fontName = font_name
                    break
                except Exception:
                    pass

        document = SimpleDocTemplate(str(output_path), pagesize=A4)
        story: list[Any] = [Paragraph(title, title_style), Spacer(1, 18)]
        for paragraph in content.splitlines() or [""]:
            story.append(Paragraph(paragraph or "&nbsp;", body_style))
            story.append(Spacer(1, 8))
        document.build(story)
        return str(output_path)
