
class ToolCollection:
  def __init__(self,*tools):
    self.tools=list(tools)
    self.tool_map={t.name:t for t in self.tools}

  def to_params(self):
    return [t.to_param() for t in self.tools]


  async def execute(self,name,tool_input):
    tool=self.tool_map[name]
    return await tool(**tool_input)