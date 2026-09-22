import logging

from app.rag.keyword_enricher import MyKeywordEnricher

logger = logging.getLogger(__name__)


class RewriteTransformer:
    """优化检索查询；LLM 不可用时使用可预测的关键词增强结果。"""

    def __init__(self, llm=None, enricher: MyKeywordEnricher | None = None):
        self.llm = llm
        self.enricher = enricher or MyKeywordEnricher()

    def rewrite(self, query: str) -> str:
        if self.llm is None:
            return self.enricher.enrich(query)
        prompt = (
            "将用户问题改写成适合内部知识库检索的独立查询。保留关键实体和意图，"
            "补充必要同义词，只输出一行查询，不要解释。\n用户问题：" + query
        )
        try:
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", response)
            rewritten = str(content).strip()
            return rewritten or self.enricher.enrich(query)
        except Exception:
            logger.exception("query rewrite failed; using keyword enrichment")
            return self.enricher.enrich(query)
