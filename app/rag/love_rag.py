"""知爱情感智能体 RAG 链路（对齐 Java 版 ai-agent-love-backed 的 rag 包）。

- 知识库：单身 / 恋爱 / 已婚 三个用户状态的恋爱指导文档
- 向量库：PGVector（LangChain 集成），Embedding 用 DashScope text-embedding-v2（1536 维）
- 切分：按 #### 问答小节切分（对齐 Java 版 MarkdownDocumentReader 的按标题切分）
- status 元数据从文件名提取，供检索端做多维过滤

建索引：python -m app.rag.love_rag
"""
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_postgres import PGVector

from app.config import PG_CONN_STR
from app.rag.vector_store import DashScopeEmbedding

LOVE_DOC_DIR = Path(__file__).parent / "love_docs"
LOVE_COLLECTION = "love_knowledge"

# 从文件名提取用户状态：恋爱常见问题和回答 - 单身篇.md -> 单身
STATUS_PATTERN = re.compile(r"[-－]\s*(单身|恋爱|已婚)篇\.md$")


def split_by_question(text: str) -> list[str]:
    """按 '#### ' 问答标题切分；首个标题之前的内容（文档主标题）丢弃。"""
    parts = re.split(r"^####\s+", text, flags=re.MULTILINE)
    return parts[1:]


def load_love_documents() -> list[Document]:
    """加载恋爱知识库：按问答小节切分，并注入 status 元数据。"""
    documents: list[Document] = []
    for file_path in sorted(LOVE_DOC_DIR.glob("*.md")):
        match = STATUS_PATTERN.search(file_path.name)
        if not match:
            print(f"[skip] 文件名无法识别状态：{file_path.name}")
            continue
        status = match.group(1)
        sections = split_by_question(file_path.read_text(encoding="utf-8"))
        for index, section in enumerate(sections, start=1):
            content = section.strip()
            if content:
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"status": status, "source": file_path.name, "section": index},
                    )
                )
    print(f"恋爱知识库加载完成：{len(documents)} 个问答小节")
    return documents


def get_love_vector_store() -> PGVector:
    """只读连接 love_knowledge 集合，不触发重索引。"""
    return PGVector(
        embeddings=DashScopeEmbedding(),
        connection=PG_CONN_STR,
        collection_name=LOVE_COLLECTION,
        pre_delete_collection=False,
    )


if __name__ == "__main__":
    # 重建索引（会先删除旧集合）：python -m app.rag.love_rag
    store = PGVector(
        embeddings=DashScopeEmbedding(),
        connection=PG_CONN_STR,
        collection_name=LOVE_COLLECTION,
        pre_delete_collection=True,
    )
    store.add_documents(load_love_documents())
    print(f"全部小节已写入 PGVector 集合 {LOVE_COLLECTION}")
