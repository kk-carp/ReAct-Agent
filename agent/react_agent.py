"""
agent6/react_agent.py
--------------------
使用 LangGraph 手动构建 ReAct Agent 的核心实现。

【ReAct 架构图】
                    ┌──────────────────────────────────────────┐
                    │              LangGraph StateGraph        │
                    │                                          │
   Human Input ──→  │  ┌─────────┐     has_tool_call    ┌─────┐│
                    │  │  llm_   │ ──── YES ──────────→ │tool ││
                    │  │  think  │                      │node ││
                    │  │  节点    │ ←─────────────────── │     ││
                    │  └────┬────┘                      └─────┘│
                    │       │ NO (final answer)                │
                    │       ▼                                  │
                    │     END                                  │
                    └──────────────────────────────────────────┘

【节点说明】
- llm_think_node: 调用 DeepSeek LLM，根据对话历史决定下一步行动
  - 如果返回 tool_calls → 路由到 tool_node 执行工具
  - 如果没有 tool_calls → 路由到 END，返回最终答案

- tool_node: 执行 LLM 选择的工具（天气/计算器/文档）
  - LangGraph 内置的 ToolNode 自动处理工具调用和结果回填
  - 执行完毕后自动路由回 llm_think_node（新一轮思考）
"""

import os
from typing import Literal
from dotenv import load_dotenv   # 加载 .env 文件中的环境变量

from langchain_openai import ChatOpenAI          # 使用 OpenAI 兼容的接口调用 DeepSeek
from langchain_core.messages import SystemMessage  # 系统消息类型，用于构建提示
from langgraph.graph import StateGraph, END      # StateGraph: 状态图构建器, END: 终止节点
from langgraph.prebuilt import ToolNode          # 预置工具节点，自动执行工具调用

from .state import AgentState                    # 自定义的状态类型
from .prompts import get_system_prompt           # 获取系统提示词（带时间）
from tools import ALL_TOOLS                      # 所有可用工具的列表

load_dotenv()   # 从 .env 读取配置（如 DEEPSEEK_API_KEY）


def build_react_agent():
    """
    构建并编译 ReAct Agent 图。

    Returns:
        compiled_graph: 可直接调用 .invoke() 或 .stream() 的编译后图
    """

    # ── 1. 初始化 DeepSeek LLM ────────────────────────────────────────
    llm = ChatOpenAI(
        model="deepseek-chat",                                      # 使用 DeepSeek 模型
        api_key=os.getenv("DEEPSEEK_API_KEY"),                      # API 密钥从环境变量获取
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),  # API 地址
        temperature=0,          # ReAct 推理需要确定性输出，temperature=0
        max_tokens=4096,
    )

    # 绑定工具：让 LLM 知道有哪些工具可以调用（写入函数签名到 system prompt）
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # ── 2. 定义节点函数 ───────────────────────────────────────────────
    def llm_think_node(state: AgentState) -> AgentState:
        """
        思考节点：LLM 接收当前对话历史，决定：
        (A) 调用某个工具 → 返回包含 tool_calls 的 AIMessage
        (B) 给出最终答案 → 返回普通文本 AIMessage
        """
        # 在消息列表最前面插入系统提示（每次更新时间）
        system_msg = SystemMessage(content=get_system_prompt())
        messages = [system_msg] + list(state["messages"])

        # 调用带工具的 LLM 进行推理
        response = llm_with_tools.invoke(messages)

        # 新增：每次思考后，迭代次数 +1
        current_iterations = state.get("iterations", 0) + 1
        
        # 返回更新后的状态（仅添加新消息，LangGraph 的 add_messages 会处理合并）
        return {"messages": [response], "iterations": current_iterations}

    # ── 3. 定义路由函数（条件边）─────────────────────────────────────
    def should_continue(state: AgentState) -> Literal["tools7", "end"]:
        """
        检查最新的 AIMessage 是否包含 tool_calls：
        - 有 tool_calls → 继续执行工具（"tools7"）
        - 无 tool_calls → 结束推理（"end"）
        """
        MAX_ITERATIONS = 6  # 设置最大迭代阈值
        if state.get("iterations", 0) >= MAX_ITERATIONS:
            return "end"  # 超过最大迭代次数，结束推理

        last_message = state["messages"][-1]
        # 判断最新消息是否有 tool_calls 属性且非空
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools7"      # 路由到工具节点
        return "end"              # 路由到结束节点

    # ── 4. 创建 ToolNode ─────────────────────────────────────────────
    # LangGraph 内置 ToolNode：
    # - 自动解析 AIMessage 中的 tool_calls
    # - 并发执行多个工具调用（如果 LLM 一次调用了多个工具）
    # - 将结果包装成 ToolMessage 追加到 state.messages
    tool_node = ToolNode(ALL_TOOLS)

    # ── 5. 构建 StateGraph ───────────────────────────────────────────
    graph_builder = StateGraph(AgentState)   # 创建状态图构建器，指定状态类型

    # 添加节点
    graph_builder.add_node("llm_think", llm_think_node)   # 思考节点
    graph_builder.add_node("tools7", tool_node)           # 工具执行节点

    # 设置入口节点
    graph_builder.set_entry_point("llm_think")

    # 添加条件边：llm_think → tools7 | END
    graph_builder.add_conditional_edges(
        source="llm_think",
        path=should_continue,
        path_map={
            "tools7": "tools7",   # 继续调用工具
            "end": END            # 结束
        }
    )

    # 添加固定边：tools7 → llm_think（工具执行后继续思考）
    graph_builder.add_edge("tools7", "llm_think")

    # ── 6. 编译图 ────────────────────────────────────────────────────
    compiled_graph = graph_builder.compile()

    return compiled_graph


# 单例模式：模块级别只创建一次
_agent_instance = None


def get_agent():
    """获取 Agent 单例（懒加载，避免重复初始化）"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = build_react_agent()   # 首次调用时构建
    return _agent_instance