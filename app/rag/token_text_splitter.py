from collections.abc import Iterable
from typing import Any

import tiktoken
from langchain_core.documents import Document


class MyTokenTextSplitter:
    """按 token 切分文档，尽量保留 chunk 之间的上下文重叠。"""

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 60, encoding_name: str = "cl100k_base"):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size)")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

    def split_text(self, text: str) -> list[str]:
        if not text:
            return []
        token_ids = self.encoding.encode(text, disallowed_special=())
        step = self.chunk_size - self.chunk_overlap
        chunks: list[str] = []
        for start in range(0, len(token_ids), step):
            chunk = self.encoding.decode(token_ids[start : start + self.chunk_size]).strip()
            if chunk:
                chunks.append(chunk)
            if start + self.chunk_size >= len(token_ids):
                break
        return chunks

    def split_documents(self, documents: Iterable[Document]) -> list[Document]:
        output: list[Document] = []
        for document in documents:
            for index, text in enumerate(self.split_text(document.page_content)):
                metadata: dict[str, Any] = dict(document.metadata)
                metadata["chunk_index"] = index
                metadata["token_chunk_size"] = len(self.encoding.encode(text, disallowed_special=()))
                output.append(Document(page_content=text, metadata=metadata))
        return output
