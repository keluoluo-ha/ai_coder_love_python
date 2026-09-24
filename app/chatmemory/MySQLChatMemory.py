from typing import List
import json
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage,messages_from_dict,messages_to_dict,message_to_dict
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker  # ← 补上 sessionmaker
from app.db.models import Base


class MySqlChatMemory(BaseChatMessageHistory):
  def __init__(self,session_id:str,db_url:str):
    self.session_id=session_id
   # 1. 创建数据库连接引擎
    self.engine = create_engine(db_url, echo=True)
    # 2. 根据你自己写的ORM模型自动建表（没有就创建，已有则跳过）
    Base.metadata.create_all(self.engine)
    # 3. 创建数据库会话工厂，用来生成操作数据库的会话对象
    self.Session = sessionmaker(bind=self.engine)
    # 4. 内存缓存，减少重复查数据库
    self._cache_messages: List[BaseMessage] = []

  
  @property
  def messages(self)->List[BaseMessage]:
    if self._cache_messages:
      return self._cache_messages
    db_session=self.Session()
    try:
      sql=text("""
                SELECT message FROM message_store 
                WHERE session_id = :sid 
                ORDER BY created_at ASC
            """)
      result = db_session.execute(sql, {"sid": self.session_id}).fetchall()
      # JSON字符串转dict列表
      msg_dict_list = [json.loads(row.message) for row in result]
      # dict还原为LangChain消息对象
      self._cache_messages = messages_from_dict(msg_dict_list)
      return self._cache_messages
    finally:
      db_session.close()

  
  def add_message(self,message:BaseMessage)->None:
    self._cache_messages.append(message)
    msg_dict=message_to_dict(message)
    msg_json=json.dumps(msg_dict,ensure_ascii=False)
    db_session=self.Session()
    try:
          insert_sql = text("""
                INSERT INTO message_store (session_id, message)
                VALUES (:sid, :msg_json)
            """)
          db_session.execute(insert_sql, {
                "sid": self.session_id,
                "msg_json": msg_json
            })
          db_session.commit()
    except Exception as e:
            db_session.rollback()
            raise e
    finally:
            db_session.close()


  def clear(self) -> None:
        """清空当前会话所有对话记录"""
        # 清空内存缓存
        self._cache_messages.clear()
        db_session = self.Session()
        try:
            del_sql = text("DELETE FROM message_store WHERE session_id = :sid")
            db_session.execute(del_sql, {"sid": self.session_id})
            db_session.commit()
        finally:
            db_session.close()
