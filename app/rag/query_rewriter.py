from langchain_community.chat_models import ChatTongyi
from app.config import LLM_MODEL_NAME

class QueryRewriter:
    def __init__(self):
        self.llm = ChatTongyi(model=LLM_MODEL_NAME)

    def rewrite(self, query: str) -> str:
        """把用户问题改写成更适合检索的关键词"""
        prompt = f"""你是一个智能客服系统的查询优化器。请把用户问题重写成更适合检索知识库的关键词或问题。
            规则：
            1. 提取核心意图（退换、价格、功能、技术支持等）
            2. 补全可能的同义词（如"退货"→"退换货、退款、退货流程"）
            3. 只输出改写后的查询文本，不要解释

            用户问题：{query}

            改写后的查询：
                """
        response = self.llm.invoke(prompt)
        return response.content.strip()
    

    def rewrite_and_search(self, query: str, vector_store, k: int = 5):
        rewritten = self.rewrite(query)
        print(f"改写前：{query}")
        print(f"改写后：{rewritten}")
        results = vector_store.similarity_search(rewritten, k=k)
        return results
