"""
tools7/document_tool.py
----------------------
文档读取与检索工具。

支持文件格式：
- .txt  纯文本文件
- .md   Markdown 文件
- .pdf  PDF 文件（使用 pypdf 库）

功能特性：
- 关键词搜索（返回包含关键词的相关段落）
- 全文读取
- 自动截断超长文档（保留头尾）
- 路径安全校验（防止目录遍历攻击）
"""

import os
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

# 文档根目录（相对于项目根目录）
# 使用 Path(__file__).parent.parent 定位到项目根目录下的 docs 文件夹
DOCS_DIR = Path(__file__).parent.parent / "docs"
MAX_CHARS = 8000   # 单次返回最大字符数，避免输出过长
CONTEXT_LINES = 5  # 关键词搜索时，返回匹配行前后各 N 行


def _read_txt(file_path: Path) -> str:
    """
    读取纯文本或 Markdown 文件的内容。

    Args:
        file_path: 文件路径（Path 对象）

    Returns:
        文件的全部文本内容（UTF-8 编码）
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _read_pdf(file_path: Path) -> str:
    """
    读取 PDF 文件，提取所有页面的文本。

    使用 pypdf 库进行文本提取，按页组织输出。

    Args:
        file_path: PDF 文件路径

    Returns:
        所有页面的文本，每页以 "--- 第 N 页 ---" 分隔，或返回错误信息
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        pages_text = []
        # 遍历每一页，提取文本
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                pages_text.append(f"--- 第 {i+1} 页 ---\n{text}")
        return "\n\n".join(pages_text)
    except ImportError:
        return "❌ 读取 PDF 需要安装 pypdf: pip install pypdf"
    except Exception as e:
        return f"❌ PDF 读取失败: {str(e)}"


def _search_in_text(content: str, keyword: str) -> str:
    """
    在文本中搜索关键词，返回匹配段落的上下文。

    类似 grep -C N 的效果：对于每个匹配行，返回该行及其前后 CONTEXT_LINES 行，
    然后将连续的行合并成段落，用分隔线隔开不同匹配块。

    Args:
        content: 要搜索的完整文本
        keyword: 要搜索的关键词（大小写不敏感）

    Returns:
        包含关键词的上下文段落，如果没有找到则返回空字符串
    """
    lines = content.split('\n')
    matched_ranges = set()   # 存储所有需要包含的行号

    # 遍历所有行，标记匹配行及其周围行
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            start = max(0, i - CONTEXT_LINES)
            end = min(len(lines) - 1, i + CONTEXT_LINES)
            for j in range(start, end + 1):
                matched_ranges.add(j)

    if not matched_ranges:
        return ""

    # 将连续的行号合并成段落
    sorted_indices = sorted(matched_ranges)
    segments = []
    segment_start = sorted_indices[0]
    prev_idx = sorted_indices[0]

    for idx in sorted_indices[1:]:
        if idx > prev_idx + 1:
            # 出现断层，结束当前段落，开始新段落
            segment = lines[segment_start:prev_idx + 1]
            segments.append("\n".join(segment))
            segment_start = idx
        prev_idx = idx

    # 处理最后一个段落
    segments.append("\n".join(lines[segment_start:prev_idx + 1]))

    # 用分隔线连接不同段落
    result = f"\n{'='*40}\n".join(segments)
    return result


def _truncate_content(content: str, max_chars: int) -> tuple[str, bool]:
    """
    超长内容截断，保留开头和结尾各一半，中间用提示信息替换。

    Args:
        content: 原始内容
        max_chars: 允许的最大字符数

    Returns:
        元组 (截断后的内容, 是否被截断)
    """
    if len(content) <= max_chars:
        return content, False

    half = max_chars // 2
    truncated = (
        content[:half] +
        f"\n\n... [内容过长，已省略中间部分，共 {len(content)} 字符] ...\n\n" +
        content[-half:]
    )
    return truncated, True


def _list_available_docs() -> str:
    """
    列出 docs 目录下所有支持的文档文件（.txt, .md, .pdf）。

    Returns:
        格式化后的文档列表字符串，或错误信息
    """
    if not DOCS_DIR.exists():
        return "docs 目录不存在"

    files = []
    # 递归遍历 docs 目录下的所有文件
    for f in DOCS_DIR.rglob("*"):
        if f.is_file() and f.suffix in {'.txt', '.md', '.pdf'}:
            rel_path = f.relative_to(DOCS_DIR)
            size_kb = f.stat().st_size / 1024
            files.append(f"  - {rel_path}  ({size_kb:.1f} KB)")

    if not files:
        return "docs 目录中暂无文档"

    return "可用文档：\n" + "\n".join(files)


@tool
def read_document(filename: str, keyword: Optional[str] = None) -> str:
    """
    读取 docs 目录下的文档内容。支持 .txt、.md、.pdf 格式。

    Args:
        filename: 文件名（如 "product_manual.txt"）。
                  填写 "list" 可列出所有可用文档。
        keyword: 可选，在文档中搜索包含该关键词的段落。
                 不填则返回全文（超长时自动截断）。

    Returns:
        文档内容或搜索结果字符串

    示例：
        read_document("product_manual.txt")          → 读取全文
        read_document("product_manual.txt", "价格")  → 搜索含"价格"的段落
        read_document("list")                        → 列出所有文档
    """
    # 特殊命令：列出文档
    if filename.strip().lower() == "list":
        return _list_available_docs()

    try:
        # 安全校验：防止目录遍历攻击，只取文件名部分
        safe_filename = Path(filename).name  # 去掉路径，仅保留文件名
        file_path = DOCS_DIR / safe_filename

        # 验证文件存在
        if not file_path.exists():
            available = _list_available_docs()
            return (
                f"❌ 文件不存在: '{filename}'\n\n"
                f"{available}"
            )

        # 验证是真实文件（非符号链接到外部，但此检查较简单）
        if not file_path.is_file():
            return f"❌ '{filename}' 不是一个文件"

        # 根据文件扩展名选择读取方法
        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            content = _read_pdf(file_path)
        elif suffix in {'.txt', '.md', ''}:
            content = _read_txt(file_path)
        else:
            return f"❌ 不支持的文件格式: {suffix}（支持 .txt .md .pdf）"

        # 关键词搜索模式
        if keyword and keyword.strip():
            kw = keyword.strip()
            search_result = _search_in_text(content, kw)
            if search_result:
                # 对搜索结果进行截断（搜索结果可能很长）
                truncated, was_truncated = _truncate_content(search_result, MAX_CHARS)
                header = (
                    f"📄 文件: {filename}\n"
                    f"🔍 关键词 '{kw}' 的相关段落:\n"
                    f"{'='*50}\n"
                )
                footer = "\n[结果已截断]" if was_truncated else ""
                return header + truncated + footer
            else:
                return (
                    f"📄 文件: {filename}\n"
                    f"🔍 未找到包含 '{kw}' 的内容\n"
                    f"提示：尝试使用更短的关键词，或不加关键词读取全文"
                )

        # 全文读取模式
        truncated, was_truncated = _truncate_content(content, MAX_CHARS)
        header = (
            f"📄 文件: {filename}  "
            f"({len(content):,} 字符)\n"
            f"{'='*50}\n"
        )
        footer = f"\n\n[文件较长，已截断显示前后各 {MAX_CHARS//2} 字符，共 {len(content):,} 字符]" if was_truncated else ""
        return header + truncated + footer

    except PermissionError:
        return f"❌ 权限不足，无法读取文件: {filename}"
    except UnicodeDecodeError:
        return f"❌ 文件编码不支持，请确保文件为 UTF-8 编码: {filename}"
    except Exception as e:
        return f"❌ 读取文件时出错: {str(e)}"