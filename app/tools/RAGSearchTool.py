from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.rag.vector_store import get_vector_store
from app.rag.query_rewriter import QueryRewriter

class RAGSearchInput(BaseModel):
    query: str = Field(description="搜索关键词或问题")

class RAGSearchTool(BaseTool):
    name: str = "knowledge_base"
    description: str = "搜索内部知识库，查询产品FAQ、退换货政策、价格方案、技术支持、账号安全等官方文档内容"
    parameters: type[BaseModel] = RAGSearchInput

    async def execute(self, query: str) -> str:
        rewriter = QueryRewriter()
        vs = get_vector_store()
        rewritten = rewriter.rewrite(query)
        results = vs.similarity_search(rewritten, k=3)
        return "\n---\n".join([d.page_content for d in results])
