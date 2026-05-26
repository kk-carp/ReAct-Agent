# -*- coding: utf-8 -*-
"""
main.py
-------
ReAct Agent 主程序入口。

提供两种运行模式：
1. 交互式 Chat 模式：多轮对话，实时流式输出推理过程
2. 批量演示模式：自动运行预设问题，展示各工具能力

特性：
- 使用 rich 库提供彩色终端输出
- 实时展示 ReAct 推理链（Thought → Action → Observation）
- 流式输出 LLM 思考过程
- 友好的错误提示
"""

import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径，确保能够导入项目内部模块
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv                # 加载 .env 环境变量
from rich.console import Console              # Rich 控制台，用于彩色输出
from rich.panel import Panel                  # 创建带边框的文本面板
from rich.text import Text                    # 富文本支持
from rich.rule import Rule                    # 绘制分隔线
from rich.markdown import Markdown            # Markdown 渲染支持
from rich import print as rprint              # 带格式的打印函数
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage  # 消息类型

load_dotenv()                                 # 从 .env 文件加载环境变量（DEEPSEEK_API_KEY 等）
console = Console()                           # 创建 Rich 控制台实例


# ── 样式常量 ──────────────────────────────────────────────────────────
# 定义不同输出类型的样式，用于控制终端显示颜色
STYLE_HUMAN    = "bold cyan"      # 用户输入样式
STYLE_THINKING = "bold yellow"    # 思考过程样式
STYLE_TOOL_CALL = "bold magenta"  # 工具调用样式
STYLE_TOOL_RESULT = "dim green"   # 工具返回结果样式
STYLE_ANSWER   = "bold green"     # 最终答案样式
STYLE_ERROR    = "bold red"       # 错误信息样式
STYLE_SYSTEM   = "dim white"      # 系统提示样式


def print_banner():
    """打印欢迎横幅，显示课程信息和技术栈"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║         🤖 ReAct Agent - 工业级 LLM 课程 第2章             ║
║                                                              ║
║  技术栈: LangGraph + LangChain + DeepSeek API               ║
║  工具集: 🌤️ 天气查询  🧮 数学计算  📄 文档读取             ║
╚══════════════════════════════════════════════════════════════╝"""
    console.print(banner, style="bold blue")   # 蓝色粗体打印


def print_agent_step(step_type: str, content: str, tool_name: str = ""):
    """
    格式化打印 ReAct 推理步骤。

    Args:
        step_type: "thought" | "action" | "observation" | "answer"
        content: 步骤内容
        tool_name: 工具名称（action 类型时使用）
    """
    # 根据步骤类型定义对应的图标
    icons = {
        "thought":     "💭",
        "action":      "🔧",
        "observation": "👁️ ",
        "answer":      "✅",
    }
    # 根据步骤类型定义显示样式
    styles = {
        "thought":     "yellow",
        "action":      "magenta",
        "observation": "cyan",
        "answer":      "green",
    }
    # 根据步骤类型定义标签文本
    labels = {
        "thought":     "Thought",
        "action":      f"Action → {tool_name}",
        "observation": "Observation",
        "answer":      "Final Answer",
    }

    icon = icons.get(step_type, "•")           # 获取图标，默认点号
    style = styles.get(step_type, "white")     # 获取样式，默认白色
    label = labels.get(step_type, step_type)   # 获取标签，默认为步骤类型名

    # 打印步骤标题（图标+标签）
    console.print(f"\n{icon} [{style}]{label}[/{style}]")
    # 打印步骤内容（使用较暗的对应颜色）
    console.print(f"   {content}", style=f"dim {style}")


def run_agent_with_display(agent, question: str) -> str:
    """
    运行 Agent 并实时展示推理过程。

    LangGraph 的 stream() 方法逐步返回每个节点的输出，
    我们据此还原 ReAct 推理链的完整过程。

    Args:
        agent: 编译后的 LangGraph 图
        question: 用户问题

    Returns:
        最终答案字符串
    """
    # 打印用户问题
    console.print(f"\n[{STYLE_HUMAN}]👤 用户问题:[/{STYLE_HUMAN}] {question}")
    console.print(Rule(style="dim"))   # 打印浅色分隔线

    inputs = {"messages": [HumanMessage(content=question)]}  # 构建输入消息
    final_answer = ""                   # 存储最终答案
    step_count = 0                      # 推理步骤计数器

    try:
        # 流式遍历 Agent 图的每个输出块（每个块包含当前完整状态）
        for chunk in agent.stream(inputs, stream_mode="values"):
            messages = chunk.get("messages", [])
            if not messages:
                continue

            last_msg = messages[-1]      # 获取最新的一条消息

            # ── AIMessage（LLM 思考 or 最终回答）────────────────────
            if isinstance(last_msg, AIMessage):
                content = last_msg.content or ""

                # 有 tool_calls：这是一次工具调用决策
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    step_count += 1
                    console.print(f"\n[dim]── 推理步骤 {step_count} ──[/dim]")

                    # 显示思考过程（如果有内容，DeepSeek 有时会输出思考）
                    if content.strip():
                        # 超过 500 字符时截断显示
                        print_agent_step("thought", content[:500] + ("..." if len(content) > 500 else ""))

                    # 显示每个工具调用
                    for tc in last_msg.tool_calls:
                        tool_name = tc["name"]
                        tool_args = tc["args"]
                        # 将参数格式化为 "key=value" 字符串
                        args_str = ", ".join(f"{k}={repr(v)}" for k, v in tool_args.items())
                        print_agent_step("action", f"{tool_name}({args_str})", tool_name)

                # 无 tool_calls：这是最终答案
                elif content.strip():
                    console.print(f"\n[{STYLE_ANSWER}]✅ 最终答案:[/{STYLE_ANSWER}]")
                    # 使用 Rich 面板包装答案，美观显示
                    console.print(Panel(
                        content,
                        border_style="green",
                        padding=(1, 2)
                    ))
                    final_answer = content

            # ── ToolMessage（工具执行结果）─────────────────────────
            elif isinstance(last_msg, ToolMessage):
                result = last_msg.content
                # 截断过长的工具输出，避免刷屏
                display_result = result if len(result) <= 600 else result[:600] + "\n... [结果已截断，完整内容已传给 LLM]"
                print_agent_step("observation", display_result)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[{STYLE_ERROR}]❌ Agent 执行出错: {e}[/{STYLE_ERROR}]")
        import traceback
        console.print(traceback.format_exc(), style="dim red")

    return final_answer


def run_demo_mode(agent):
    """
    批量演示模式：自动运行多个预设问题，展示所有工具能力。
    适合课程演示和录屏。
    """
    # 预设的演示问题，每个元素为 (演示名称, 问题内容)
    demo_questions = [
        # 天气查询
        ("🌤️  天气工具演示", "北京今天的天气怎么样？顺便告诉我明天需要带伞吗？"),

        # 计算器
        ("🧮 计算器工具演示", "我有 100 万元本金，年利率 5.5%，复利计算 10 年后是多少钱？请用精确公式计算。"),

        # 文档读取
        ("📄 文档工具演示", "帮我查一下产品手册，DeepCompute X1 服务器的价格是多少？GPU 配置怎样？"),

        # 多工具组合
        ("🔗 多工具组合演示", "上海今天气温是多少度？如果上海今天气温是 T 度，北京比上海低 5 度，请计算北京温度比 0 度低多少度。"),

        # 文档 + 计算综合
        ("💡 文档+计算综合演示", "读取产品手册，如果买一台 DeepCompute X1，年度维保费是多少钱？"),
    ]

    console.print("\n", Panel(
        "🎬 进入演示模式，将依次展示所有工具能力",
        style="bold blue",
        padding=(0, 2)
    ))

    # 逐个运行预设问题
    for i, (demo_name, question) in enumerate(demo_questions, 1):
        console.print(f"\n\n")
        console.print(Rule(f"演示 {i}/{len(demo_questions)}: {demo_name}", style="blue"))
        run_agent_with_display(agent, question)

        # 如果不是最后一个演示，提示按 Enter 继续
        if i < len(demo_questions):
            console.print("\n[dim]按 Enter 继续下一个演示，Ctrl+C 退出...[/dim]")
            try:
                input()
            except KeyboardInterrupt:
                console.print("\n[yellow]演示结束[/yellow]")
                break


def run_interactive_mode(agent):
    """
    交互式对话模式：持续接收用户输入，直到输入 exit/quit。
    支持多轮对话语境（每次都是独立对话，无记忆）。
    """
    # 显示交互模式说明面板
    console.print(Panel(
        "💬 进入交互模式\n输入问题开始对话，输入 [bold]exit[/bold] 或 [bold]quit[/bold] 退出\n\n"
        "提示问题示例：\n"
        "  • 深圳现在天气如何？\n"
        "  • 计算 1 到 100 的整数之和（用公式 n*(n+1)/2）\n"
        "  • 查看 product_manual.txt 里关于 GPU 的信息\n"
        "  • 如果 DeepSeek-R1 处理 100 万 tokens，输入输出各一半，总费用多少？",
        title="ReAct Agent",
        border_style="blue",
        padding=(1, 2)
    ))

    # 主循环
    while True:
        try:
            console.print(f"\n[{STYLE_HUMAN}]💬 请输入您的问题（exit 退出）:[/{STYLE_HUMAN}] ", end="")
            user_input = input().strip()

            if not user_input:
                continue

            # 检查退出命令
            if user_input.lower() in {"exit", "quit", "退出", "q"}:
                console.print("[yellow]👋 再见！[/yellow]")
                break

            # 运行 Agent 处理问题
            run_agent_with_display(agent, user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]👋 再见！[/yellow]")
            break
        except EOFError:
            break


def check_environment():
    """检查运行环境配置，验证必要的环境变量和目录"""
    issues = []   # 记录检查中发现的任何问题

    # 检查 DeepSeek API Key 是否已设置
    if not os.getenv("DEEPSEEK_API_KEY"):
        issues.append("❌ DEEPSEEK_API_KEY 未设置（必须）")
    else:
        key = os.getenv("DEEPSEEK_API_KEY")
        console.print(f"[green]✓[/green] DEEPSEEK_API_KEY: {key[:8]}***")   # 仅显示前8位

    # 显示 API Base URL（可配置，默认为 DeepSeek 官方）
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    console.print(f"[green]✓[/green] DEEPSEEK_BASE_URL: {base_url}")

    # 检查 OpenWeatherMap API Key（可选）
    owm_key = os.getenv("OPENWEATHER_API_KEY", "")
    if owm_key:
        console.print(f"[green]✓[/green] OPENWEATHER_API_KEY: {owm_key[:8]}*** (将使用 OpenWeatherMap)")
    else:
        console.print(f"[yellow]ℹ[/yellow] OPENWEATHER_API_KEY: 未设置（将使用免费的 wttr.in）")

    # 检查 docs 目录是否存在
    docs_dir = PROJECT_ROOT / "docs"
    if docs_dir.exists():
        doc_count = len(list(docs_dir.glob("*.*")))
        console.print(f"[green]✓[/green] docs 目录: {doc_count} 个文件")
    else:
        issues.append("⚠️  docs 目录不存在")

    # 如果有问题，全部打印出来并返回 False
    if issues:
        for issue in issues:
            console.print(f"[red]{issue}[/red]")
        return False

    return True


def main():
    """主程序入口"""
    print_banner()

    # 环境检查
    console.print(Rule("环境检查", style="dim"))
    if not check_environment():
        console.print("\n[red]请先配置 .env 文件（参考 .env），然后重新运行[/red]")
        sys.exit(1)

    # 初始化 Agent
    console.print(Rule("初始化 Agent", style="dim"))
    console.print("正在构建 ReAct Agent 图...", style="dim")
    try:
        from agent import get_agent   # 导入 agent 模块的单例获取函数
        agent = get_agent()           # 获取已编译的 LangGraph 图
        console.print("[green]✓ Agent 构建成功[/green]")
    except Exception as e:
        console.print(f"[red]✗ Agent 构建失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc(), style="dim red")
        sys.exit(1)

    # 选择运行模式
    console.print(Rule("运行模式选择", style="dim"))
    console.print("[1] 交互式对话模式（手动输入问题）")
    console.print("[2] 批量演示模式（自动运行预设问题）")
    console.print("请选择 (默认 1): ", end="")

    try:
        choice = input().strip() or "1"   # 读取用户输入，默认 "1"
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    console.print(Rule(style="dim"))

    # 根据选择启动对应模式
    if choice == "2":
        run_demo_mode(agent)
    else:
        run_interactive_mode(agent)


if __name__ == "__main__":
    main()