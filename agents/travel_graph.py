"""旅行规划 LangGraph 工作流"""

from typing import TypedDict, Annotated

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from client import LLMClient
from services import (
    get_weather,
    get_pois,
    get_location,
    get_distance,
    tavily_search,
)


# ──────────────────────────────────────────────
# State 定义
# ──────────────────────────────────────────────

class TravelState(TypedDict):
    """旅行规划工作流的状态"""

    messages: Annotated[list, add_messages]  # 对话历史，自动累积
    intent: str             # 用户意图：travel_plan / general_query
    plan_steps: list[dict]  # 规划出的步骤列表
    current_step: int       # 当前执行到第几步（从0开始）
    step_results: list[str] # 每步执行结果


# ──────────────────────────────────────────────
# 结构化输出模型
# ──────────────────────────────────────────────

class IntentResult(BaseModel):
    """意图分类结果"""

    intent: str = Field(
        description="用户意图分类，只能是 'travel_plan' 或 'general_query'"
    )


class PlanStep(BaseModel):
    """单个规划步骤"""

    step: int = Field(description="步骤编号")
    task: str = Field(description="当前步骤的执行目标")


class PlanResult(BaseModel):
    """规划结果"""

    steps: list[PlanStep] = Field(description="规划出的步骤列表")


# ──────────────────────────────────────────────
# 共享资源
# ──────────────────────────────────────────────

# 模型实例（按职责分配不同模型）
_zhipu = LLMClient("zhipu").get_llm("glm-4.5-air")
_dashscope = LLMClient("dashscope").get_llm("qwen3.5-flash")

# 可用工具列表
_tools = [
    get_weather,
    get_pois,
    get_location,
    get_distance,
    tavily_search,
]


# ──────────────────────────────────────────────
# 节点函数
# ──────────────────────────────────────────────

_classify_prompt = """你是一个意图分类器，根据用户消息判断意图类型。

规则：
- 用户想规划旅行、制定行程、安排出游 → travel_plan
- 其他所有情况（问天气、搜景点、闲聊等）→ general_query

只返回 intent 字段，不要解释。"""


async def classify_intent(state: TravelState) -> dict:
    """分类用户意图"""

    classify_llm = _zhipu.with_structured_output(IntentResult, method="function_calling")
    last_msg = state["messages"][-1].content

    result = await classify_llm.ainvoke([
        SystemMessage(content=_classify_prompt),
        *state["messages"],
    ])

    print(f"[意图分类] {last_msg} → {result.intent}")
    return {"intent": result.intent}


_general_prompt = """你是一个旅行助手，可以回答关于旅行、天气、景点、美食等问题。
请根据用户的问题，使用工具获取信息后给出回答。"""


async def handle_general(state: TravelState) -> dict:
    """处理普通查询（天气、搜索、闲聊等）"""

    agent = create_agent(
        model=_zhipu,
        system_prompt=_general_prompt,
        tools=_tools,
    )

    response = await agent.ainvoke({"messages": state["messages"]})
    answer = response["messages"][-1].content

    print(f"[普通查询] 回答: {answer[:80]}...")
    return {"messages": [{"role": "assistant", "content": answer}]}


_plan_prompt = """你是旅行规划师，负责把用户的旅行需求拆解成可执行的子步骤。

要求：
1. 每个步骤必须具体且可执行（如"查询XX城市的天气"、"搜索XX景点"）
2. 步骤数量控制在3-5个
3. 不要生成"向用户追问信息"的步骤

用户需求：
{user_message}
"""


async def plan_travel(state: TravelState) -> dict:
    """制定旅行计划"""

    plan_llm = _zhipu.with_structured_output(PlanResult, method="function_calling")

    last_msg = state["messages"][-1].content
    prompt = _plan_prompt.format(user_message=last_msg)

    plan = await plan_llm.ainvoke(prompt)
    plan_steps = [s.model_dump() for s in plan.steps]

    print(f"[旅行规划] 生成 {len(plan_steps)} 个步骤:")
    for s in plan_steps:
        print(f"  步骤 {s['step']}: {s['task']}")

    return {
        "plan_steps": plan_steps,
        "current_step": 0,
        "step_results": [],
    }


_execute_system_prompt = """你是任务执行器，根据给定的任务上下文完成当前步骤。

你可以使用工具，但必须遵守以下规则：
1. 只围绕当前步骤执行，不要擅自扩展任务
2. 如果已有历史步骤结果，优先使用，避免重复调用工具
3. 只输出当前步骤的简洁结论"""

_execute_query_template = """
原始需求：{user_query}

最近已完成的任务与结果：
{recent_steps}

当前步骤的任务 [{step_num}/{total_steps}]：{step_task}

请只完成当前步骤。"""


async def execute_step(state: TravelState) -> dict:
    """执行当前计划步骤"""

    idx = state["current_step"]
    step = state["plan_steps"][idx]
    total = len(state["plan_steps"])
    last_msg = state["messages"][-1].content

    # 格式化最近步骤结果（只取最近2条避免上下文过长）
    recent = state["step_results"][-2:]
    recent_steps = "\n".join(recent) if recent else "暂无"

    query = _execute_query_template.format(
        user_query=last_msg,
        recent_steps=recent_steps,
        step_num=step["step"],
        total_steps=total,
        step_task=step["task"],
    )

    executor = create_agent(
        model=_zhipu,
        system_prompt=_execute_system_prompt,
        tools=_tools,
    )

    response = await executor.ainvoke({"messages": [{"role": "user", "content": query}]})
    result = response["messages"][-1].content

    print(f"[执行步骤 {idx + 1}/{total}] {step['task']} → {result[:60]}...")

    new_results = state["step_results"] + [f"步骤 {step['step']}: {step['task']}\n结果: {result}"]
    return {
        "current_step": idx + 1,
        "step_results": new_results,
    }


_summarize_prompt = """你是旅行助手，根据用户需求和每一步的执行结果，生成一份完整的旅行规划回答。

要求：
1. 基于步骤结果总结，不补充未出现的信息
2. 回答结构清晰，按天/按主题组织
3. 直接回应用户的原始需求

用户需求：{user_query}

已完成步骤与结果：
{completed_steps}
"""


async def summarize(state: TravelState) -> dict:
    """总结所有步骤结果"""

    last_msg = state["messages"][-1].content
    completed = "\n\n".join(state["step_results"])

    prompt = _summarize_prompt.format(user_query=last_msg, completed_steps=completed)
    response = await _dashscope.ainvoke(prompt)

    print(f"[总结] 生成最终回答: {response.content[:80]}...")
    return {"messages": [{"role": "assistant", "content": response.content}]}


# ──────────────────────────────────────────────
# 条件边函数
# ──────────────────────────────────────────────

def route_by_intent(state: TravelState) -> str:
    """根据意图分类结果路由"""

    return "plan_travel" if state["intent"] == "travel_plan" else "handle_general"


def should_continue_exec(state: TravelState) -> str:
    """判断是否还有步骤需要执行"""

    if state["current_step"] < len(state["plan_steps"]):
        return "execute_step"

    return "summarize"


# ──────────────────────────────────────────────
# 构建并编译图
# ──────────────────────────────────────────────

def build_travel_graph():
    """构建旅行规划工作流图"""

    graph = StateGraph(TravelState)

    # 添加节点
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("handle_general", handle_general)
    graph.add_node("plan_travel", plan_travel)
    graph.add_node("execute_step", execute_step)
    graph.add_node("summarize", summarize)

    # 添加边
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges("classify_intent", route_by_intent)
    graph.add_edge("plan_travel", "execute_step")
    graph.add_conditional_edges("execute_step", should_continue_exec)
    graph.add_edge("handle_general", END)
    graph.add_edge("summarize", END)

    # 编译（带内存持久化）
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# 导出编译好的图实例
travel_graph = build_travel_graph()
