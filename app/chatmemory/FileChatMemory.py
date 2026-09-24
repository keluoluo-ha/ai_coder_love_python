from typing import List
import json
from pathlib import Path
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage,messages_from_dict,messages_to_dict,message_to_dict

class FileChatMemory(BaseChatMessageHistory):
  def __init__(self, session_id:str,save_dir:str="./chat_history"):
    self.path=Path(save_dir)/f"{session_id}.json"
    self.path.parent.mkdir(parents=True,exist_ok=True)

  @property
  def messages(self)->List[BaseMessage]:
    if not self.path.exists():
      return []
    with open(self.path,"r",encoding="utf-8") as f:
      data=json.load(f)
    return messages_from_dict(data)
  
  def add_message(self,message:BaseMessage)->None:
    existing=messages_to_dict(self.messages)
    existing.append(message_to_dict(message))
    with open(self.path,"w",encoding="utf-8") as f:
      json.dump(existing,f,ensure_ascii=False,indent=2)
  

  def clear(self)->None:
    if self.path.exists():
      self.path.unlink()
