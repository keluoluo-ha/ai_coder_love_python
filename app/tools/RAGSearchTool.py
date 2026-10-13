from pydantic import BaseModel, Field

from langchain_classic.retrievers import MultiQueryRetriever
from langchain_community.chat_models import ChatTongyi

from app.config import LLM_MODEL_NAME
from app.rag.love_rag import get_love_vector_store
from app.tools.base_tool import BaseTool


class RAGSearchInput(BaseModel):
    query: str = Field(description="搜索关键词或问题")


class RAGSearchTool(BaseTool):
    name: str = "knowledge_base"
    description: str = "搜索恋爱知识库，查询单身脱单、恋爱相处、已婚经营等情感指导内容"
    args_schema: type[BaseModel] = RAGSearchInput

    def _run(self, query: str) -> str:
        vector_store = get_love_vector_store()
        retriever = MultiQueryRetriever.from_llm(
            retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
            llm=ChatTongyi(model=LLM_MODEL_NAME, temperature=0),
            include_original=True,
        )
        results = retriever.invoke(query)[:3]
        return "\n---\n".join(document.page_content for document in results)

    async def _arun(self, query: str) -> str:
        return self._run(query)
