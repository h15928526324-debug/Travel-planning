# 🗺️ 智行规划师 — 基于多智能体协同的一站式旅行全案定制系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> 用户只需用自然语言说出旅行需求，系统就能自动输出一份可直接落地的完整旅行全案，涵盖行程、预算、避坑、攻略、应急等全维度内容。

---

## 🎯 核心亮点

- **多 Agent 专业分工**: 调研、规划、预算、避坑、文案 5 大专业 Agent 协同工作
- **真实数据驱动**: 集成天气 API、地图 API，方案基于实时数据而非凭空想象
- **完整产品闭环**: 从需求输入到完整方案导出，一站式完成
- **多轮对话迭代**: 支持用户反馈修改，自动调整行程
- **可视化前端**: Streamlit Web UI，行程日历、预算表、清单 checkbox 全部可视化

---

## 🏗️ 系统架构

```
用户输入 (自然语言/表单)
        │
        ▼
┌──────────────────────────┐
│   LangGraph 工作流引擎    │
│                          │
│  ┌──────────────────┐    │
│  │  需求解析 Node     │    │
│  └────────┬─────────┘    │
│           ▼               │
│  ┌──────────────────┐    │
│  │  调研 Agent       │ ← 天气/地图/搜索 API
│  │  景点+美食+住宿+   │    │
│  │  天气+交通+政策    │    │
│  └────────┬─────────┘    │
│           ▼               │
│  ┌───────┴───────┐       │
│  │ 规划 Agent     │       │
│  │ 每日行程编排    │       │
│  └───────┬───────┘       │
│          ▼                │
│  ┌───────┴───────┐       │
│  │ 预算 Agent     │       │
│  │ 明细预算表     │       │
│  └───────┬───────┘       │
│          ▼                │
│  ┌──────────────────┐    │
│  │ 避坑攻略 Agent    │    │
│  │ 避坑+清单+拍照+   │    │
│  │ 应急             │    │
│  └────────┬─────────┘    │
│           ▼               │
│  ┌──────────────────┐    │
│  │ 文案 Agent        │    │
│  │ 总览+金句+社交文案 │    │
│  └────────┬─────────┘    │
│           ▼               │
│  ┌──────────────────┐    │
│  │ 汇总导出 Node     │    │
│  └────────┬─────────┘    │
│           │               │
│     用户反馈? ──→ 迭代    │
└──────────────────────────┘
        │
        ▼
   完整旅行全案
   (Markdown/PDF/可视化)
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key:
#   - OPENAI_API_KEY (必填)
#   - WEATHER_API_KEY (可选，无则使用模拟数据)
#   - MAP_API_KEY (可选，无则使用模拟数据)
```

### 4. 启动

```bash
# Web UI 模式 (推荐)
python main.py

# 或直接启动 Streamlit
streamlit run frontend/app.py

# CLI 模式
python main.py --cli "我和朋友想去成都玩4天，预算3000，喜欢美食和拍照"
```

### 5. 访问

打开浏览器访问 `http://localhost:8501`

---

## 📂 项目结构

```
travel-planner/
├── main.py                  # 主入口 (Web UI / CLI)
├── requirements.txt         # 依赖
├── .env.example             # 环境变量模板
├── README.md
│
├── config/                  # 配置管理
│   └── settings.py          # 全局配置单例 (LLM/API/DB)
│
├── models/                  # 数据模型
│   └── schemas.py           # Pydantic 模型 + AgentState
│
├── agents/                  # 专业 Agent 层
│   ├── base.py              # Agent 基类 + LLM 工厂
│   ├── research_agent.py    # 调研 Agent (景点/美食/住宿/天气/交通)
│   ├── planning_agent.py    # 行程规划 Agent (每日精细化行程)
│   ├── budget_agent.py      # 预算 Agent (明细预算表)
│   ├── tips_agent.py        # 避坑攻略 Agent (避坑/清单/拍照/应急)
│   └── copywriting_agent.py # 文案 Agent (总览/金句/社交文案)
│
├── tools/                   # 工具层 (Agent 可调用的外部 API)
│   ├── weather.py           # 天气查询 (OpenWeatherMap / 和风天气)
│   ├── geo.py               # 地理编码 & 距离计算 (高德地图)
│   ├── search.py            # 搜索 & 数据聚合 (景点/美食/酒店)
│   └── export.py            # 导出 (Markdown / PDF)
│
├── workflows/               # LangGraph 工作流
│   ├── state.py             # AgentState 定义
│   └── graph.py             # 主工作流 DAG + 节点 + 路由
│
├── frontend/                # Streamlit 前端
│   └── app.py               # Web UI (表单输入 + 结果展示 + 反馈迭代)
│
├── data/templates/          # 导出模板
└── output/                  # 导出文件目录
```

---

## 🤖 多 Agent 分工详解

| Agent | 角色定位 | 核心能力 | 输出 |
|-------|---------|---------|------|
| 🔍 **ResearchAgent** | 旅行情报专家 | 搜集目的地景点/美食/住宿/天气/交通/政策 | `ResearchResult` |
| 📅 **PlanningAgent** | 金牌行程规划师 | 地理聚类、体力管理、时间把控、餐食推荐 | `list[DayPlan]` |
| 💰 **BudgetAgent** | 财务顾问 | 逐项费用估算、人均分摊、省钱建议 | `BudgetTable` |
| ⚠️ **TipsAgent** | 资深背包客 | 防骗避坑、物品清单、拍照攻略、应急预案 | `PitfallTips + PackingList + EmergencyPlan + PhotoGuide` |
| ✍️ **CopywritingAgent** | 内容主编 | 行程总览摘要、每日金句、社交分享文案 | 总览 + 金句 + 社交文案 |

---

## 🔧 技术栈

| 模块 | 技术选型 |
|------|---------|
| Agent 编排 | LangGraph (状态图 + 并行节点 + 条件路由 + 迭代循环) + LangChain |
| 大模型 | GPT-4o (可替换为任何 OpenAI 兼容模型) |
| 前端 | Streamlit (响应式 Web UI) |
| 数据模型 | Pydantic v2 (类型安全 + 序列化) |
| 导出 | Markdown / 可扩展 PDF (WeasyPrint) |
| 工具 | 天气 API / 高德地图 API / 搜索聚合 |
| 状态管理 | LangGraph MemorySaver (支持中断恢复) |

---

## 🎨 功能演示流程

1. **输入需求**: 自然语言描述或表单填写
2. **系统自动调研**: 并行搜集天气、景点、美食、交通等数据
3. **生成行程**: 按日编排，上午/下午/晚上各 2-3 个活动 + 餐厅推荐
4. **预算计算**: 交通/住宿/餐饮/门票/购物 逐项估算
5. **攻略输出**: 避坑指南 + 拍照机位 + 物品清单 + 应急预案
6. **导出分享**: Markdown 文件 + 社交分享文案
7. **反馈迭代**: 输入修改意见，系统自动调整

---

## 🔜 后续扩展方向

- [ ] 接入真实搜索 API (马蜂窝/携程/小红书)
- [ ] Vue3 + Element Plus 前端替代 Streamlit
- [ ] MySQL 持久化用户方案历史
- [ ] 行程日历拖拽编辑
- [ ] 多人协作规划
- [ ] 实时价格监控 & 降价提醒
- [ ] 语音输入支持
- [ ] 多语言目的地支持

---

## 📄 License

MIT License

---

*🤖 Built with LangGraph + Multi-Agent Architecture*
