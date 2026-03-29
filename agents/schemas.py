from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """单个计划步骤"""
    step: int = Field(description="步骤编号")
    task: str = Field(description="当前步骤的执行目标")


class PlanResult(BaseModel):
    """计划列表"""
    steps: list[PlanStep] = Field(default_factory=list, description="规划出的步骤列表")


class Critique(BaseModel):
    """评估结果"""
    is_satisfactory: bool = Field(description="当前回答是否已满足用户需求、无需进一步修改")
    critique: str = Field(description="对当前回答的具体评价，指出不足之处")
    suggestions: list[str] = Field(default_factory=list, description="具体的改进建议列表")


class MemoryItem(BaseModel):
    """记忆条目"""
    iteration: int = Field(description="第几轮迭代")
    query: str = Field(description="用户原始问题")
    response: str = Field(description="当时的回答")
    critique: Critique = Field(description="评估结果")