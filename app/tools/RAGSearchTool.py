from pydantic import BaseModel, Field

from app.rag.query_expander import QueryExpander
from app.rag.query_rewriter import QueryRewriter
from app.rag.vector_store import get_vector_store
from app.tools.base_tool import BaseTool


class RAGSearchInput(BaseModel):
    query: str = Field(description="搜索关键词或问题")


class RAGSearchTool(BaseTool):
    name: str = "knowledge_base"
    description: str = "搜索内部知识库，查询产品FAQ、退换货政策、价格方案、技术支持、账号安全等官方文档内容"
    parameters: type[BaseModel] = RAGSearchInput

    async def execute(self, query: str) -> str:
        vector_store = get_vector_store()
        expanded = QueryExpander().expand(query, max_queries=4)
        rewritten = QueryRewriter().rewrite_many(expanded)
        results = QueryRewriter.multi_query_search(rewritten, vector_store, k=3)
        return "\n---\n".join(document.page_content for document in results)
