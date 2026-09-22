import sys
from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))
from typing import List
import dashscope
from langchain_community.document_loaders import TextLoader
from langchain.embeddings.base import Embeddings
from app.config import DASHSCOPE_API_KEY,PG_CONN_STR
from app.rag.keyword_enricher import MyKeywordEnricher
from app.rag.token_text_splitter import MyTokenTextSplitter
from langchain_postgres import PGVector



#初始化DashScope Embedding（输出1536维向量）
class DashScopeEmbedding(Embeddings):
   def __init__(self):
      dashscope.api_key=DASHSCOPE_API_KEY
       # 通义文本向量化模型，输出固定1536维
      self.model_name = "text-embedding-v2"

   def embed_documents(self, texts: List[str]) -> List[List[float]]:
       all_embeddings = []
    # 每批最多10条，符合DashScope限制
       batch_size = 10
       #初始向量化
       for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        resp = dashscope.TextEmbedding.call(
            model=self.model_name,
            input=batch_texts,
        )
        batch_embeds = [item["embedding"] for item in resp.output["embeddings"]]
        all_embeddings.extend(batch_embeds)
       return all_embeddings
   

   def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


DOC_DIR=Path(__file__).parent/"docs"
MD_SUFIX="*.md"

text_splitter=MyTokenTextSplitter(chunk_size=400, chunk_overlap=60)
keyword_enricher=MyKeywordEnricher()

# 1.加载全部md文件
def load_all_markdown():
  all_docs=[]
  for file_path in DOC_DIR.rglob(f"{MD_SUFIX}"):
    if file_path.is_file():
      print(f"正在加载文档：{file_path.name}")
      loader=TextLoader(str(file_path),encoding="utf_8")
      raw_docs=loader.load()
      #2.切分
      split_docs=text_splitter.split_documents(raw_docs)
      for document in split_docs:
        keywords = keyword_enricher.extract_keywords(document.page_content)
        document.metadata["keywords"] = keywords
      all_docs.extend(split_docs)
  print(f"总共加载并切割完成 {len(all_docs)} 段文本")
  return all_docs


#3. 写入PostgreSQL向量库
def save_to_pgvector(docs):
    # 初始化向量模型
   embeddings=DashScopeEmbedding()
   
    # 连接PG向量库
   vector_store = PGVector(
        connection=PG_CONN_STR,
        collection_name="rag_knowledge",  # 向量集合名，自定义
        embeddings=embeddings,
        pre_delete_collection=True  
    )
    # 批量插入向量
   vector_store.add_documents(docs)
   print("全部文档向量存入PGVector完成！")
   return vector_store

def get_vector_store():
   """返回只读的 PGVector 对象，不触发重索引"""
   return PGVector(
        embeddings=DashScopeEmbedding(),
        connection=PG_CONN_STR,
        collection_name="rag_knowledge",
        pre_delete_collection=False,   # 关键：不要删库！
        )
   