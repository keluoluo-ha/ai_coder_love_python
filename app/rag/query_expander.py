from app.rag.keyword_enricher import MyKeywordEnricher


class QueryExpander:
    """生成原始问题及领域关键词扩展问题。"""

    def __init__(self, enricher: MyKeywordEnricher | None = None):
        self.enricher = enricher or MyKeywordEnricher()

    def expand(self, query: str, max_queries: int = 4) -> list[str]:
        original = query.strip()
        if not original:
            return []
        candidates = [original, self.enricher.enrich(original)]
        for keyword in self.enricher.extract_keywords(original, limit=max_queries):
            if keyword not in original and len(candidates) < max_queries:
                candidates.append(f"{keyword} {original}")
        unique: list[str] = []
        seen = set()
        for candidate in candidates:
            normalized = " ".join(candidate.split()).casefold()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(candidate)
            if len(unique) >= max_queries:
                break
        return unique
