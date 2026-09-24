class RereadingAdvisor:
    """将关键约束在执行前再次呈现给模型，减少回答偏离。"""

    DEFAULT_CONSTRAINTS = (
        "回答前重新核对：只依据已知事实或工具结果；不要编造政策、价格或功能；"
        "涉及账户敏感操作、不确定事项或需要确认的信息时，必须调用 ask_human；"
        "问题解决后调用 terminate。"
    )

    def __init__(self, constraints: str | None = None):
        self.constraints = constraints or self.DEFAULT_CONSTRAINTS

    def build_prompt(self) -> str:
        return "【执行前重读约束】\n" + self.constraints
