from abc import ABC,abstractmethod
from typing import Any, Type,Dict
from pydantic import BaseModel



class BaseTool(ABC):
  name:str
  description:str
  parameters:Type[BaseModel]

  @abstractmethod
  async def execute(self,**kwargs)->Any:
    """工具执行逻辑，由子类实现"""
    raise NotImplementedError

  async def __call__(self, **kwargs)->Any:
    """直接 await tool(xxx) 调用，自动校验参数"""
    # 使用Pydantic自动校验入参
    validated_params=self.parameters(**kwargs)
    return await self.execute(**validated_params.model_dump())


  def to_param(self)->Dict[str,Any]:
    """转换为标准 OpenAI function calling JSON"""
    schema= self.parameters.model_json_schema()
    return{
      "type":"function",
      "function":{
        "name":self.name,
        "description":self.description,
        "parameters":schema
      }
    }