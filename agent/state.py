"""
agent6/state.py
--------------
定义 LangGraph ReAct Agent 的状态结构。
LangGraph 中，State 是节点间传递数据的核心载体。
"""

# 导入类型提示相关工具
from typing import Annotated, Sequence
# 从 typing_extensions 导入 TypedDict，用于定义类型化的字典结构
from typing_extensions import TypedDict
# 导入 LangChain 的消息基类，所有对话消息都继承自 BaseMessage
from langchain_core.messages import BaseMessage
# 导入 LangGraph 内置的消息合并函数 add_messages
# 该 reducer 使得在状态更新时，新消息自动追加到已有消息列表末尾，而非覆盖
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    ReAct Agent 的全局状态。

    字段说明：
    - messages: 对话历史列表，使用 add_messages reducer 自动追加（不覆盖）
      这是 LangGraph 内置的消息合并策略，保证多节点并发安全

    ReAct 推理循环中，消息流动过程：
    1. HumanMessage  → [思考节点] → AIMessage(含 tool_calls)
    2. AIMessage     → [工具节点] → ToolMessage(工具执行结果)
    3. ToolMessage   → [思考节点] → AIMessage(最终答案 or 继续调用工具)
    """
    # messages 字段是一个消息序列，并使用 add_messages 作为注解的 reducer
    # 这意味着在状态更新时，新消息会追加到现有消息列表末尾
    # 而不是替换整个列表，这对于多轮对话至关重要
    messages: Annotated[Sequence[BaseMessage], add_messages]
    iterations: int  # 新增：迭代次数计数器