# -*- coding: utf-8 -*-
"""
tests/test_tools.py
-------------------
工具单元测试。
不需要 API Key，可独立运行验证工具逻辑是否正确。

运行方式：
    cd chapter2_react_agent
    python -m pytest tests/ -v
"""

# 导入系统相关模块，用于修改 Python 路径
import sys
from pathlib import Path
# 将项目根目录添加到 Python 路径中，确保可以导入 tools 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入 pytest 框架（如果通过 pytest 运行，则自动使用）
import pytest
# 导入待测试的工具函数：计算器和文档读取工具
from tools.calculator_tool import calculator
from tools.document_tool import read_document


# ── 计算器测试 ────────────────────────────────────────────────────────

class TestCalculator:
    """测试 calculator 工具的各项功能"""

    def test_basic_addition(self):
        """测试基础加法运算"""
        result = calculator.invoke({"expression": "2 + 3"})
        assert "5" in result

    def test_multiplication(self):
        """测试乘法运算"""
        result = calculator.invoke({"expression": "12 * 13"})
        assert "156" in result

    def test_power(self):
        """测试幂运算（2的10次方）"""
        result = calculator.invoke({"expression": "2 ** 10"})
        # 结果可能带千位分隔符或不带
        assert "1,024" in result or "1024" in result

    def test_sqrt(self):
        """测试平方根函数"""
        result = calculator.invoke({"expression": "sqrt(144)"})
        assert "12" in result

    def test_pi_usage(self):
        """测试圆周率常量 π 的使用"""
        result = calculator.invoke({"expression": "pi * 2"})
        assert "6.28" in result

    def test_factorial(self):
        """测试阶乘函数"""
        result = calculator.invoke({"expression": "factorial(10)"})
        assert "3,628,800" in result or "3628800" in result

    def test_combination(self):
        """测试组合数计算 comb(10,3) = 120"""
        result = calculator.invoke({"expression": "comb(10, 3)"})
        assert "120" in result

    def test_complex_expression(self):
        """复利公式测试：100万 * (1.05)^10"""
        result = calculator.invoke({"expression": "1000000 * (1.05 ** 10)"})
        # 约 1,628,894，检查前几位
        assert "1,628" in result or "1628" in result

    def test_division_by_zero(self):
        """测试除以零错误，应返回错误信息"""
        result = calculator.invoke({"expression": "1 / 0"})
        assert "❌" in result or "错误" in result

    def test_security_block_import(self):
        """安全测试：import 语句应被拒绝"""
        result = calculator.invoke({"expression": "import os"})
        assert "❌" in result

    def test_security_block_dunder(self):
        """安全测试：双下划线访问（如 __import__）应被拒绝"""
        result = calculator.invoke({"expression": "__import__('os')"})
        assert "❌" in result

    def test_log(self):
        """测试对数函数 log(100,10) = 2"""
        result = calculator.invoke({"expression": "log(100, 10)"})
        assert "2" in result

    def test_trigonometry(self):
        """测试三角函数 sin(π/2) = 1.0"""
        result = calculator.invoke({"expression": "sin(pi/2)"})
        assert "1" in result

    def test_chinese_symbols(self):
        """测试中文乘除号转换（× → *，÷ → /）"""
        result = calculator.invoke({"expression": "3 × 4"})
        assert "12" in result


# ── 文档工具测试 ──────────────────────────────────────────────────────

class TestDocumentTool:
    """测试 read_document 工具的各项功能"""

    def test_list_documents(self):
        """测试列出所有文档的功能"""
        result = read_document.invoke({"filename": "list"})
        assert "product_manual.txt" in result

    def test_read_full_document(self):
        """测试读取完整文档"""
        result = read_document.invoke({"filename": "product_manual.txt"})
        assert "DeepCompute" in result
        assert "价格" in result

    def test_search_keyword_price(self):
        """测试关键词搜索：价格"""
        result = read_document.invoke({
            "filename": "product_manual.txt",
            "keyword": "价格"
        })
        assert "价格" in result
        # 应包含某个价格数值
        assert "2,850,000" in result or "980,000" in result

    def test_search_keyword_gpu(self):
        """测试关键词搜索：GPU"""
        result = read_document.invoke({
            "filename": "product_manual.txt",
            "keyword": "GPU"
        })
        assert "GPU" in result
        assert "H100" in result or "A100" in result

    def test_search_not_found(self):
        """测试搜索不存在的关键词"""
        result = read_document.invoke({
            "filename": "product_manual.txt",
            "keyword": "区块链元宇宙XYZ"
        })
        assert "未找到" in result

    def test_file_not_found(self):
        """测试读取不存在的文件"""
        result = read_document.invoke({"filename": "nonexistent.txt"})
        assert "❌" in result or "不存在" in result

    def test_path_traversal_protection(self):
        """安全测试：目录遍历攻击应被阻止（如 ../main.py）"""
        result = read_document.invoke({"filename": "../main.py"})
        # 文件名被 Path.name 处理后变成 main.py，不在 docs 目录，应返回错误
        assert "❌" in result or "不存在" in result


# ── 快速运行（不使用 pytest）────────────────────────────────────────
# 该部分允许直接运行此脚本执行测试，无需安装 pytest

if __name__ == "__main__":
    print("=" * 60)
    print("运行工具单元测试（无需 API Key）")
    print("=" * 60)

    # 运行计算器测试
    tests = TestCalculator()
    test_methods = [m for m in dir(tests) if m.startswith("test_")]

    passed = 0
    failed = 0
    for method_name in test_methods:
        try:
            getattr(tests, method_name)()
            print(f"  ✅ Calculator::{method_name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ Calculator::{method_name} - {e}")
            failed += 1

    # 运行文档工具测试
    doc_tests = TestDocumentTool()
    doc_methods = [m for m in dir(doc_tests) if m.startswith("test_")]
    for method_name in doc_methods:
        try:
            getattr(doc_tests, method_name)()
            print(f"  ✅ Document::{method_name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ Document::{method_name} - {e}")
            failed += 1

    # 输出最终统计
    print(f"\n{'='*60}")
    print(f"结果: {passed} 通过, {failed} 失败")