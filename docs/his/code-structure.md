# 乡礼 Spark · 代码结构

> 路径：`/Users/kafka/Desktop/files/bussiness_test/Hackathon/trae_ai_creativity_content/xiangli-spark`

---

## 一、项目定位

乡礼 Spark 是一个面向地方食品特产商家的 AI 内容策略助理。

- 第一版聚焦：种草引流优先 + 地方故事增强
- 主案例：贵州刺梨果干 / 游客伴手礼
- 主接口：`POST /api/generate-local-food`

---

## 二、目录结构

```text
xiangli-spark/
├── README.md                          # 项目入口
├── docs/
│   ├── ARCHITECTURE.md                # 系统架构
│   ├── code-structure.md              # 本文件
│   └── superpowers/
│       ├── specs/                     # 设计文档
│       └── plans/                     # 实施计划
├── hermes/                            # 轻量 cron 调度引擎（可选）
├── skills/
│   └── xhs_content_collector/         # 小红书采集工具（独立，非主链路）
├── tests/
│   └── test_xiangli_spark.py          # 全部测试
├── xiangli_spark/                     # 核心包
│   ├── __init__.py
│   ├── SKILL.md                       # 技能说明
│   ├── pyproject.toml                 # 包定义
│   ├── README.md                      # 核心模块说明
│   ├── server/
│   │   └── main.py                    # FastAPI 服务
│   ├── web/                           # React 前端
│   │   ├── src/
│   │   │   ├── App.jsx
│   │   │   └── components/
│   │   │       ├── InputView.jsx
│   │   │       ├── GeneratingView.jsx
│   │   │       └── ResultView.jsx
│   │   ├── index.html
│   │   ├── package.json
│   │   └── README.md
│   └── core/
│       ├── __init__.py
│       ├── schemas.py                 # 数据契约
│       ├── orchestrator.py            # 主编排器
│       └── agents/
│           ├── __init__.py
│           ├── analyzer/
│           │   ├── __init__.py
│           │   └── agent.py           # 传播任务分析 + 模板匹配
│           ├── prompter/
│           │   ├── __init__.py
│           │   └── agent.py           # 多平台内容骨架编排
│           ├── generator/
│           │   ├── __init__.py
│           │   └── agent.py           # 视觉资产建议器
│           └── copywriter/
│               ├── __init__.py
│               └── agent.py           # 多平台内容包生成
└── .venv/                             # Python 虚拟环境（不入库）
```

---

## 三、核心数据流

```text
LocalFoodRequest
  → build_local_food_strategy_brief()    → ContentStrategyBrief
  → build_local_food_content_plan()      → dict[str, list[str]]
  → suggest_local_food_visual_assets()   → list[str]
  → generate_local_food_content_pack()   → GeneratedContentPack
  → run_local_food_pipeline()            → dict result
```

---

## 四、模块职责

### schemas.py
定义所有 Pydantic 数据契约：
- `LocalFoodRequest` — 用户输入
- `ContentStrategyBrief` — 传播策略
- `TemplateMatch` — 模板命中
- `GeneratedContentPack` — 多平台内容包
- `VisualAssetSuggestion` — 视觉建议

### orchestrator.py
主编排器，只有一个入口：
- `run_local_food_pipeline(request) -> dict`

### agents/analyzer/agent.py
传播任务分析：
- 识别产品类型、目标人群、传播目标
- 匹配模板（difference_seed / gift_scene）
- 输出 `ContentStrategyBrief`

### agents/prompter/agent.py
多平台内容骨架编排：
- 根据 brief 组装各平台内容骨架
- 输出 `dict[str, list[str]]`（xiaohongshu / douyin / moments / hero）

### agents/generator/agent.py
视觉资产建议器：
- 根据 brief 生成有序的视觉卡片建议
- 输出 `list[str]`

### agents/copywriter/agent.py
多平台内容包生成：
- 根据请求、brief、内容骨架生成完整内容包
- 输出 `GeneratedContentPack`
- 包含：小红书文案 / 抖音脚本 / 朋友圈文案 / 封面标题 / 故事增强段 / 视觉建议

### server/main.py
FastAPI 服务：
- `POST /api/generate-local-food` — 主接口
- `GET /api/health` — 健康检查

---

## 五、模板库

定义在 `core/templates/local_food_templates.py`：

| 模板名 | 用途 |
|---|---|
| `difference_seed` | 差异点种草模板（默认主模板） |
| `gift_scene` | 送礼场景模板 |
| `local_story_seed` | 地方故事种草模板 |
| `story_boost` | 地方故事增强段（默认辅模板） |

---

## 六、测试

```bash
cd xiangli-spark
source .venv/bin/activate
pytest tests/test_xiangli_spark.py -q
```

测试覆盖：
- `TestSchemas` — schema 验证
- `TestLocalFoodTemplates` — 模板库
- `TestLocalFoodAnalyzer` — 传播任务分析
- `TestLocalFoodPrompter` — 多平台骨架编排
- `TestLocalFoodCopywriter` — 多平台内容包生成
- `TestLocalFoodGenerator` — 视觉建议器
- `TestLocalFoodOrchestrator` — 主编排器串联
- `TestLocalFoodAPI` — API 接口

---

## 七、前端

```bash
cd xiangli_spark/web
npm install
./node_modules/.bin/vite
```

前端组件：
- `InputView.jsx` — 特产信息输入表单
- `GeneratingView.jsx` — 提交并调用 `/api/generate-local-food`
- `ResultView.jsx` — 展示策略识别 + 模板命中 + 多平台内容结果
