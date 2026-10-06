# test/test_rag.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.rag.vector_store import load_all_markdown, save_to_pgvector
from app.config import DASHSCOPE_API_KEY
from app.rag.query_rewriter import QueryRewriter
print(f"API KEY: {DASHSCOPE_API_KEY[:10]}..." if DASHSCOPE_API_KEY else "API KEY: None")

# 1. 加载 + 切分
docs = load_all_markdown()
print(f"第一步完成：加载了 {len(docs)} 段文本")

# 2. 向量化 + 写入 PgVector
vector_store = save_to_pgvector(docs)
print("第二步完成：向量已写入 PostgreSQL")

# 3. 检索验证 - 用一句话搜最相关的片段
rewriter = QueryRewriter()
results = rewriter.rewrite_and_search("怎么退货？", vector_store)
print("\n===== 检索结果 =====")
for i, doc in enumerate(results):
    print(f"\n--- 第 {i+1} 条 ---")
    print(doc.page_content[:200])  # 只打印前 200 字预览
