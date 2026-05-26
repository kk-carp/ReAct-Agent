"""
tools7/__init__.py
------------------
统一导出所有工具，方便 agent6 模块引用。

本模块将三个核心工具（天气查询、计算器、文档读取）集中导出，
并提供工具列表 ALL_TOOLS，供 LangGraph ToolNode 和 LLM bind_tools 使用。
"""

# 导入天气查询工具：根据城市名获取实时天气和预报
from .weather_tool import get_weather
# 导入计算器工具：安全执行数学表达式计算
from .calculator_tool import calculator
# 导入文档读取工具：读取 docs 目录下的文档，支持关键词搜索
from .document_tool import read_document

# 工具列表，包含所有可用工具的实例
# 该列表被用于：
#   1. LangGraph 的 ToolNode 初始化，用于执行工具调用
#   2. LLM 的 bind_tools() 方法，使 LLM 知道可用的工具及其签名
ALL_TOOLS = [get_weather, calculator, read_document]

# 定义模块的公开接口：当使用 `from tools7 import *` 时，只导入以下名称
__all__ = ["get_weather", "calculator", "read_document", "ALL_TOOLS"]