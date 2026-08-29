---
name: wuyan-ai
description: 物言 AI — 细粒度 DNA 驱动的小红书地方特产笔记生成器。输入产品信息，自动组合场景、价值承诺、钩子、结构、语气和视觉片段，生成可直接发布的小红书笔记 + 配图建议。Use when: 地方特产内容生成、小红书文案创作、细粒度 DNA 组合、伴手礼/游客种草/送礼场景。
---

# 物言 AI Skill

## Overview

物言是一个"厚技能"目录，核心能力是**细粒度 DNA 驱动的小红书笔记生成**。它把一篇内容拆成六个可组合维度，从每个维度的候选池召回 Top 10，再由 Analyzer 一次选择组合，避免让模型从零自由发挥。

### 核心能力

1. **六维 DNA 组合** — 自动从场景、价值承诺、钩子、结构、语气和视觉六个维度各选一个片段，不需要用户挑模板
2. **两 Agent 流水线** — Analyzer（多模态策略分析）→ Creator（内容创作），专业分工保证质量
3. **多模态输入** — 支持文字 + 最多 3 张产品图片，AI 读图提炼卖点
4. **双兜底机制** — LLM 调用失败退规则模板，格式解析失败退默认值，永远有输出

### 适用场景

- 地方食品特产商家生成小红书推广文案
- 伴手礼店、合作社、地方小品牌内容创作
- 游客种草、节日送礼、自用尝鲜等场景
- 需要快速产出多个版本的运营人员

### v1 聚焦

- 平台：仅小红书（v2 扩展抖音/朋友圈）
- 品类：地方食品特产（果干、茶、零食、调味品、糕点等）
- 生图：预留接口，v2 接入

---

## First-Time Setup

在项目根目录下：

```bash
# 安装 Python 依赖
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 安装前端依赖
cd web
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 等配置
```

### 启动服务

```bash
# 后端（项目根目录）
./start_server.sh

# 前端（另开终端）
cd web
npm run dev
```

访问 `http://localhost:5173` 即可使用。

---

## Main API

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate` | 流式生成（SSE，推荐） |
| POST | `/api/generate/sync` | 同步生成（一次性返回） |
| GET | `/api/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |

### 主要输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `product_name` | string | ✅ | 产品名称，如"贵州刺梨果干" |
| `product_category` | string | ✅ | 产品品类，如"果干蜜饯" |
| `origin_place` | string | ✅ | 产地，如"贵州贵阳" |
| `target_audience` | string | ✅ | 目标人群，如"来贵州旅游的年轻女生" |
| `selling_scene` | string | ❌ | 售卖场景，如"游客伴手礼、中秋送礼" |
| `user_note` | string | ❌ | 补充说明/自定义卖点 |
| `images` | file[] | ❌ | 产品图片（最多 3 张，multipart/form-data） |

### 主要输出结构

```json
{
  "post": {
    "title": "小红书笔记标题",
    "content": "小红书笔记正文",
    "hashtags": ["#标签1", "#标签2"]
  },
  "image_suggestions": [
    {"index": 1, "content": "配图建议一句话"},
    {"index": 2, "content": "配图建议一句话"}
  ],
  "selected_fragments": [
    {"fragment_id": "scene_001", "type": "scene", "value": "下班后附近餐饮推荐", "score": 0.95, "reason": "匹配理由"},
    {"fragment_id": "hook_001", "type": "hook", "value": "价格对比 + 结果反差", "score": 0.95, "reason": "匹配理由"}
  ],
  "key_selling_points": ["卖点1", "卖点2", "卖点3"]
}
```

### SSE 事件流

调用 `/api/generate` 时，服务端通过 SSE 推送实时进度：

| 事件 | 说明 |
|------|------|
| `progress` | 步骤进度：`analyzing`（策略分析）/ `creating`（内容创作）的 start/done |
| `result` | 最终生成结果，JSON 格式 |
| `error` | 错误信息 |

---

## 细粒度 DNA 系统

### 什么是爆款 DNA？

每条片段包含：
- `fragmentId` — 片段 ID
- `type` — `scene` / `valuePromise` / `hook` / `structure` / `tone` / `visualStyle`
- `value` — 可直接注入创作策略的内容
- `score` — 当前 Mock 排序分数
- `state`、`version` 和三项分项分数 — 为后续数据闭环预留

当前仓库共有 6 个维度、每维度 20 条 Mock 片段，共 120 条。每个维度先按 score 召回 Top 10，再交给 AI 选择 1 条。

DNA 提取、缓存区晋级、发布追踪和真实淘汰机制暂未实现。

---

## How To Use

### 典型调用流程

1. 用户在前端填写产品信息（产品名、品类、产地、目标人群）
2. 可选上传产品图片（最多 3 张）
3. 点击"生成小红书笔记"
4. 实时看到两步进度：策略分析 → 内容创作
5. 结果页展示：完整笔记 + 配图建议 + 六维 DNA 片段组合 + 核心卖点

### 质量好的输入长这样

| 字段 | 好的示例 | 不好的示例 |
|------|---------|-----------|
| 产品名 | 贵州刺梨果干 | 果干 |
| 品类 | 果干蜜饯 | 食品 |
| 产地 | 贵州贵阳 | 贵州 |
| 目标人群 | 来贵州旅游的20-30岁女生 | 所有人 |
| 场景 | 游客伴手礼、闺蜜分享 | 卖货 |

> 输入越具体，DNA 匹配越精准，生成质量越高。

---

## What To Report

生成结果返回后，优先汇报：

1. **DNA 组合结果** — 六个维度分别选中了什么片段，为什么选择
2. **核心卖点** — AI 提炼的 3-5 个核心传播点
3. **笔记标题** — 第一时间看到钩子效果
4. **配图建议数量** — AI 自主决定了几张图，分别是什么
5. **完整笔记正文** — 可直接复制发布

---

## Project Structure

```
wuyan-ai/
├── wuyan_ai/              # 后端 Python 包
│   ├── core/
│   │   ├── agents/        # AI Agent（analyzer + creator）
│   │   ├── dnas/          # 细粒度 DNA 片段库（6 个 JSON + 加载器）
│   │   ├── schemas.py     # Pydantic 数据契约
│   │   └── orchestrator.py  # 流水线编排
│   ├── tools/             # LLM 客户端、图片处理等工具
│   └── server/            # FastAPI 服务
├── web/                   # React 前端
│   └── src/components/
│       ├── DnaDashboard.jsx    # 爆款 DNA 实时更新仪表盘
│       ├── InputView.jsx       # 输入表单
│       ├── GeneratingView.jsx  # SSE 实时进度展示
│       └── ResultView.jsx      # 结果展示
├── legacy/                # 历史模块（采集+调度，已隔离）
├── docs/                  # 架构文档、设计文档
├── tests/                 # 单元测试
├── SKILL.md               # 本文件
└── README.md              # 项目说明
```

---

## Notes

- v1 版本聚焦小红书单平台，DNA 片段库和仪表盘数据为 Mock 展示
- 生图功能为预留接口，v2 阶段接入
- legacy/ 目录下的采集模块为后续数据闭环准备，不影响当前主链路运行
- 项目设计遵循"双兜底"原则：任何时候 Demo 都必须能出结果
