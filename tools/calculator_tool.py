"""
tools7/calculator_tool.py
------------------------
安全数学计算工具。

使用 Python 内置的 math 模块 + 受限 eval 实现，
拒绝执行任何非数学操作（文件访问、系统调用等）。

支持运算：
- 基础四则运算: +, -, *, /
- 幂运算: ** 或 pow()
- 整除和取模: //, %
- 数学函数: sqrt, sin, cos, tan, log, log10, ceil, floor, abs 等
- 常数: pi, e, inf
- 括号嵌套
"""

import math
import re
from langchain_core.tools import tool


# 白名单：只允许这些安全的数学函数和常量
# 这个字典将函数名（字符串）映射到实际的函数对象或常量值
SAFE_MATH_NAMES = {
    # 常量
    'pi': math.pi,          # 圆周率 π
    'e': math.e,            # 自然常数 e
    'inf': math.inf,        # 无穷大
    'tau': math.tau,        # 2π

    # 基础函数（Python 内置，但需要显式提供）
    'abs': abs,             # 绝对值
    'round': round,         # 四舍五入
    'pow': pow,             # 幂运算
    'max': max,             # 最大值
    'min': min,             # 最小值
    'sum': sum,             # 求和

    # math 模块函数
    'sqrt': math.sqrt,      # 平方根
    'cbrt': lambda x: x ** (1/3),  # 立方根（通过指数实现）
    'exp': math.exp,        # 指数函数 e^x
    'log': math.log,        # 自然对数或指定底数的对数
    'log2': math.log2,      # 以2为底的对数
    'log10': math.log10,    # 以10为底的对数

    # 三角函数（弧度制）
    'sin': math.sin,        # 正弦
    'cos': math.cos,        # 余弦
    'tan': math.tan,        # 正切
    'asin': math.asin,      # 反正弦
    'acos': math.acos,      # 反余弦
    'atan': math.atan,      # 反正切
    'atan2': math.atan2,    # 反正切（两个参数）
    'sinh': math.sinh,      # 双曲正弦
    'cosh': math.cosh,      # 双曲余弦
    'tanh': math.tanh,      # 双曲正切

    # 角度转换
    'radians': math.radians,  # 角度转弧度
    'degrees': math.degrees,  # 弧度转角度

    # 取整函数
    'ceil': math.ceil,      # 向上取整
    'floor': math.floor,    # 向下取整
    'trunc': math.trunc,    # 截断取整（向零取整）

    # 其他数学函数
    'factorial': math.factorial,  # 阶乘
    'gcd': math.gcd,              # 最大公约数
    'hypot': math.hypot,          # 欧几里得距离 sqrt(x^2 + y^2)
    'isnan': math.isnan,          # 判断是否为 NaN
    'isinf': math.isinf,          # 判断是否为无穷大
    'comb': math.comb,            # 组合数 C(n,k)
    'perm': math.perm,            # 排列数 P(n,k)
}


def _safe_eval(expression: str) -> float:
    """
    安全执行数学表达式。

    安全策略：
    1. 使用白名单替代全局命名空间（__builtins__ = None）
    2. 正则检测危险字符（下划线开头的特殊属性访问等）
    3. 限制表达式长度

    Args:
        expression: 数学表达式字符串

    Returns:
        计算结果（float）

    Raises:
        ValueError: 表达式包含非法内容
        ZeroDivisionError: 除以零
        OverflowError: 结果溢出
    """
    # 长度限制：防止超长表达式导致性能问题或栈溢出
    if len(expression) > 500:
        raise ValueError("表达式过长（最多500字符）")

    # 检测危险模式：通过正则表达式匹配可能的安全漏洞
    dangerous_patterns = [
        r'__\w+__',           # 双下划线属性访问（如 __class__, __import__）
        r'\bimport\b',        # import 语句
        r'\bexec\b',          # exec 函数
        r'\beval\b',          # 嵌套 eval 调用
        r'\bopen\b',          # 文件操作
        r'\bcompile\b',       # compile 函数
        r'\\x[0-9a-fA-F]{2}', # 十六进制转义（可能绕过过滤）
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, expression):
            raise ValueError(f"表达式包含不允许的操作: {expression}")

    # 执行表达式，使用受限的命名空间
    # 第一个参数：表达式字符串
    # 第二个参数：全局命名空间，禁用所有内置函数（__builtins__=None）
    # 第三个参数：局部命名空间，仅包含白名单中的数学函数和常量
    result = eval(
        expression,
        {"__builtins__": None},   # 禁用所有内置函数
        SAFE_MATH_NAMES            # 只允许白名单中的名称
    )
    return result


@tool
def calculator(expression: str) -> str:
    """
    执行数学表达式计算，返回精确结果。

    支持：加减乘除(+,-,*,/)、幂运算(**)、整除(//)、取模(%)、
    括号嵌套、数学函数(sqrt/sin/cos/log/factorial/comb等)、
    常数(pi/e)。

    示例：
    - "2 + 3 * 4" → 14
    - "sqrt(144)" → 12.0
    - "log(100, 10)" → 2.0
    - "factorial(10)" → 3628800
    - "comb(10, 3)" → 120（从10中选3的组合数）
    - "sin(pi/6)" → 0.5

    Args:
        expression: 数学表达式字符串

    Returns:
        计算结果字符串
    """
    try:
        # 预处理：清理输入，将中文符号转换为英文符号
        expression = expression.strip()
        expression = expression.replace('×', '*').replace('÷', '/').replace('，', ',')

        # 执行安全计算
        result = _safe_eval(expression)

        # 格式化输出结果
        if isinstance(result, float):
            # 如果结果是整数（如 2.0），则显示为整数格式
            if result == int(result) and not math.isinf(result):
                formatted = f"{int(result):,}"  # 加千位分隔符
            else:
                # 浮点数保留最多10位有效数字
                formatted = f"{result:.10g}"
        elif isinstance(result, int):
            formatted = f"{result:,}"  # 整数加千位分隔符
        else:
            formatted = str(result)

        # 返回格式化的结果，包含表达式和精确值
        return (
            f"📊 计算结果\n"
            f"  表达式: {expression}\n"
            f"  结果: {formatted}\n"
            f"  精确值: {result}"
        )

    except ZeroDivisionError:
        return f"❌ 计算错误: 除数不能为零\n  表达式: {expression}"
    except OverflowError:
        return f"❌ 计算错误: 结果超出数值范围（数值太大）\n  表达式: {expression}"
    except ValueError as e:
        return f"❌ 表达式错误: {str(e)}\n  表达式: {expression}"
    except SyntaxError:
        return f"❌ 语法错误: 请检查表达式格式\n  表达式: {expression}"
    except NameError as e:
        return f"❌ 未知函数或常量: {str(e)}\n  支持的函数: sqrt, sin, cos, tan, log, exp, factorial, comb 等"
    except Exception as e:
        return f"❌ 计算失败: {str(e)}\n  表达式: {expression}"