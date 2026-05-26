# ReAct Agent 项目

## 可查天气、算数据、读文档的 ReAct Agent

> **技术栈：** LangGraph + LangChain + DeepSeek API

---

## 📁 项目结构

```
chapter2_react_agent/
├── main.py                    # 主程序入口（交互/演示双模式）
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
│
├── agent/
│   ├── __init__.py
│   ├── react_agent.py         # ⭐ 核心：LangGraph ReAct 图构建
│   ├── state.py               # Agent 状态定义（AgentState）
│   └── prompts.py             # 系统提示词（ReAct 格式规范）
│
├── tools/
│   ├── __init__.py
│   ├── weather_tool.py        # 🌤️ 天气查询工具（wttr.in / OpenWeatherMap）
│   ├── calculator_tool.py     # 🧮 安全数学计算工具
│   ├── document_tool.py       # 📄 文档读取与关键词搜索工具
│   └── visualize_graph.py     # 图结构可视化工具
│
├── docs/
│   └── product_manual.txt     # 示例文档（AI 服务器产品手册）
│
└── tests/
    └── test_tools.py          # 工具单元测试（无需 API Key）
```

---

## ⚡ 快速开始

### 第一步：安装依赖

```bash
cd chapter2_react_agent
pip install -r requirements.txt
```

### 第二步：配置 API Key

```bash
cp .env .env
# 编辑 .env，填入你的 DeepSeek API Key
```

DeepSeek API Key 申请地址：https://platform.deepseek.com/

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

> **天气功能说明：**
>
> - 默认使用 **wttr.in**（免费，无需注册，支持中文城市名）
> - 如需更稳定的数据，可申请 [OpenWeatherMap](https://openweathermap.org/api) 免费 API Key

### 第三步：运行测试（可选，无需 API Key）

```bash
python tests/test_tools.py
```

### 第四步：启动 Agent

```bash
python main.py
```

选择模式：

- **模式 1（推荐）**：交互式对话，自己输入问题
- **模式 2**：自动演示，观看 Agent 如何解决预设问题

---

## 🏗️ 架构解析

### ReAct 推理循环

```
用户输入
  ↓
┌─────────────────────────────────────────────┐
│  llm_think 节点                              │
│  ┌─────────────────────────────────────────┐ │
│  │  System Prompt (ReAct 规范)              │ │
│  │  + 对话历史 (HumanMessage/AIMessage/    │ │
│  │             ToolMessage)                │ │
│  │  → DeepSeek API                         │ │
│  └─────────────────────────────────────────┘ │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
   有 tool_calls?    没有 tool_calls?
        │                    │
        ▼                    ▼
  tools 节点            END (最终答案)
  (执行工具)
        │
        └────────────→ llm_think 节点（循环）
```

## 🛠️ 工具说明

### 1. 天气工具 `get_weather(city)`

- **数据源**：wttr.in（免费）或 OpenWeatherMap
- **返回内容**：当前温度、体感温度、湿度、风速、天气描述、3天预报
- **支持**：中文城市名（北京、上海、成都）和英文（Beijing, London）

### 2. 计算器 `calculator(expression)`

- **安全机制**：白名单 eval，禁止 import/exec/文件操作
- **支持**：四则运算、幂运算、sqrt/sin/cos/log/factorial/comb 等
- **常量**：pi、e、inf、tau

### 3. 文档工具 `read_document(filename, keyword)`

- **支持格式**：.txt、.md、.pdf
- **搜索模式**：关键词搜索返回匹配行及其上下5行
- **安全机制**：路径安全校验，防止目录遍历
- **特殊命令**：`filename="list"` 列出所有可用文档

---

## 💬 示例问题

**天气类：**

```
北京今天天气怎么样？需要带伞吗？
上海和成都今天哪个城市温度更高？
```

**计算类：**

```
100万本金，年化8%，复利20年后是多少？
从52张扑克牌中随机抽5张，有多少种不同的组合？
计算圆周率乘以地球赤道半径（6371 km）的平方
```

**文档类：**

```
查看产品手册，X1 服务器的 GPU 型号和显存是什么？
产品手册里有几种服务器型号？分别多少钱？
读取文档，专业版向量数据库每月多少钱？
```
