from langchain_community.chat_models import ChatTongyi

from app.config import DASHSCOPE_API_KEY, LLM_MODEL_NAME
from app.rag.query_expander import QueryExpander
from app.rag.rewrite_transformer import RewriteTransformer


class QueryRewriter:
    def __init__(self, llm=None):
        self.llm = llm
        if self.llm is None and DASHSCOPE_API_KEY:
            try:
                self.llm = ChatTongyi(model=LLM_MODEL_NAME)
            except Exception:
                self.llm = None
        self.transformer = RewriteTransformer(llm=self.llm)
        self.expander = QueryExpander()

    def rewrite(self, query: str) -> str:
        return self.transformer.rewrite(query)

    def rewrite_many(self, queries: list[str]) -> list[str]:
        rewritten = [self.rewrite(query) for query in queries]
        unique: list[str] = []
        seen = set()
        for query in rewritten:
            normalized = " ".join(query.split()).casefold()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(query)
        return unique

    def rewrite_and_search(self, query: str, vector_store, k: int = 5):
        queries = self.expander.expand(query)
        rewritten_queries = self.rewrite_many(queries)
        return self.multi_query_search(rewritten_queries, vector_store, k=k)

    @staticmethod
    def multi_query_search(queries: list[str], vector_store, k: int = 5):
        rankings: dict[tuple[str, str], tuple[object, float]] = {}
        for query in queries:
            for rank, document in enumerate(vector_store.similarity_search(query, k=k), start=1):
                key = (document.metadata.get("source", ""), document.page_content)
                previous = rankings.get(key)
                score = 1.0 / (60 + rank)
                if previous is None:
                    rankings[key] = (document, score)
                else:
                    rankings[key] = (previous[0], previous[1] + score)
        return [item[0] for item in sorted(rankings.values(), key=lambda item: item[1], reverse=True)[:k]]
