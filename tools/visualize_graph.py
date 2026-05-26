"""
tools7/visualize_graph.py
------------------------
可视化 LangGraph Agent 的图结构。
帮助学生直观理解 ReAct 的工作流。

运行方式：
    cd chapter2_react_agent
    python tools7/visualize_graph.py

输出：
1. ASCII 文本图（终端直接显示）
2. graph.png 图片（如果安装了 graphviz）
"""

import sys
from pathlib import Path
# 将项目根目录添加到 Python 路径，以便导入 agent 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# 加载 .env 中的环境变量（DEEPSEEK_API_KEY 等），但本脚本实际不需要 API Key，只是为了兼容可能存在的依赖
load_dotenv()

from rich.console import Console
from rich.panel import Panel

# 创建 Rich 控制台对象，用于美化输出
console = Console()


def print_ascii_graph():
    """打印 ASCII 格式的 Agent 图结构"""
    # 预定义的 ASCII 艺术图，展示 ReAct Agent 的 LangGraph 结构
    # 包括入口节点 __start__、思考节点 llm_think、工具节点 tools7、结束节点 __end__
    # 以及条件分支（根据是否有 tool_calls 决定路由）和循环边（tools7 → llm_think）
    graph_art = """
    ┌─────────────────────────────────────────────────────────┐
    │              ReAct Agent - LangGraph 图结构              │
    └─────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │   __start__      │  ← 入口节点（LangGraph 自动生成）
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   llm_think      │  ← 思考节点
    │                  │     接收消息历史
    │  DeepSeek API    │     调用 LLM 推理
    │  (deepseek-chat) │     决定下一步行动
    └────────┬─────────┘
             │
      ┌──────┴──────┐
      │             │
      │ has         │ no
      │ tool_calls? │ tool_calls?
      │             │
      ▼             ▼
    ┌──────────┐  ┌───────────┐
    │  tools7   │  │  __end__  │  ← 返回最终答案
    │          │  └───────────┘
    │ ToolNode │  (LangGraph 自动生成)
    │          │
    │ 3 Tools: │
    │ ┌──────┐ │
    │ │天气  │ │  ← get_weather()
    │ └──────┘ │
    │ ┌──────┐ │
    │ │计算器│ │  ← calculator()
    │ └──────┘ │
    │ ┌──────┐ │
    │ │文档  │ │  ← read_document()
    │ └──────┘ │
    └─────┬────┘
          │
          │ (always)
          ▼
    ┌──────────────────┐
    │   llm_think      │  ← 回到思考节点（继续 ReAct 循环）
    └──────────────────┘

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ReAct 循环示例：

    用户: "北京天气怎样？如果气温低于 0 度，比 -10 低多少？"

    步骤 1: llm_think
      → AIMessage(tool_calls=[get_weather(city="北京")])
      → 路由到 tools7

    步骤 2: tools7
      → ToolMessage("北京当前 -3°C, 晴...")
      → 路由回 llm_think

    步骤 3: llm_think
      → AIMessage(tool_calls=[calculator(expression="-3 - (-10)")])
      → 路由到 tools7

    步骤 4: tools7
      → ToolMessage("结果: 7")
      → 路由回 llm_think

    步骤 5: llm_think
      → AIMessage("北京今天 -3°C，比 -10°C 高 7 度...")
      → 无 tool_calls，路由到 __end__
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    console.print(graph_art, style="cyan")


def export_graph_image():
    """
    尝试导出图结构为 PNG 图片。
    需要安装: pip install grandalf pygraphviz
    """
    try:
        from agent import get_agent
        agent = get_agent()   # 获取编译后的 LangGraph 图实例

        # 使用 LangGraph 内置的 draw_mermaid_png 方法导出图片
        try:
            img_data = agent.get_graph().draw_mermaid_png()
            output_path = Path(__file__).parent.parent / "graph.png"
            with open(output_path, "wb") as f:
                f.write(img_data)
            console.print(f"\n[green]✓ 图结构已导出: {output_path}[/green]")
        except Exception:
            # 如果生成图片失败（例如缺少 graphviz 依赖），降级输出 Mermaid 格式文本
            mermaid_str = agent.get_graph().draw_mermaid()
            console.print("\n[yellow]Mermaid 格式图定义（可粘贴到 https://mermaid.live 查看）:[/yellow]")
            console.print(Panel(mermaid_str, border_style="yellow"))

    except Exception as e:
        # 如果无法获取 agent（例如未设置 API Key 或其他错误），给出友好提示
        console.print(f"\n[yellow]⚠️ 无法导出图片: {e}[/yellow]")
        console.print("[dim]提示: 需要设置 DEEPSEEK_API_KEY 且安装 graphviz[/dim]")


if __name__ == "__main__":
    # 当直接运行此脚本时，执行以下代码
    console.print(Panel("🗺️  LangGraph ReAct Agent 图结构可视化", style="bold blue"))
    print_ascii_graph()      # 打印 ASCII 图
    export_graph_image()     # 尝试导出图片（需额外依赖）