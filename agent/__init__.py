"""
agent6/__init__.py

该模块是 agent6 包的初始化文件，负责导出核心组件，使得外部可以通过 `from agent6 import ...` 直接使用。
"""

# 从 react_agent 模块导入构建和获取 agent 的函数
# - build_react_agent: 创建并返回一个编译好的 ReAct Agent 图（StateGraph）
# - get_agent: 懒加载单例模式，避免重复构建 agent
from .react_agent import build_react_agent, get_agent

# 从 state 模块导入 AgentState 类型，用于类型提示和状态管理
# AgentState 定义了 ReAct 流程中传递的消息列表结构
from .state import AgentState

# __all__ 指定当使用 `from agent6 import *` 时，哪些名称会被导出
# 这有助于明确模块的公开接口，避免意外暴露内部实现细节
__all__ = ["build_react_agent", "get_agent", "AgentState"]