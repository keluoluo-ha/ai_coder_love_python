import re
from collections.abc import Iterable


class MyKeywordEnricher:
    """从中文/英文查询中提取关键词，并补充常见领域同义词。"""

    SYNONYMS = {
        "退货": ["退换货", "退款", "退货流程"],
        "退款": ["退货退款", "退款流程"],
        "价格": ["价格方案", "费用", "套餐"],
        "登录": ["账号登录", "无法登录", "账户"],
        "密码": ["密码重置", "找回密码", "账号安全"],
        "报错": ["错误", "异常", "故障排查"],
        "发票": ["开票", "电子发票", "发票申请"],
    }

    def extract_keywords(self, text: str, limit: int = 12) -> list[str]:
        normalized = text.lower()
        result: list[str] = []
        for phrase, synonyms in self.SYNONYMS.items():
            if phrase in normalized:
                for keyword in [phrase, *synonyms]:
                    if keyword not in result:
                        result.append(keyword)
        candidates = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{1,}|\d+", normalized)
        for candidate in candidates:
            if candidate not in result:
                result.append(candidate)
            if len(result) >= limit:
                break
        return result[:limit]

    def enrich(self, query: str) -> str:
        keywords = self.extract_keywords(query)
        if not keywords:
            return query.strip()
        return f"{query.strip()} 关键词：{' '.join(keywords)}"

    def enrich_many(self, queries: Iterable[str]) -> list[str]:
        return [self.enrich(query) for query in queries if query and query.strip()]
