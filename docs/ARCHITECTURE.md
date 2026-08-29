# 物言 · 系统架构文档

> v1.0 · 两 Agent 流水线架构 · 爆款 DNA 驱动

---

## 1. 总览

物言是一个**多 Agent 流水线架构**的小红书笔记生成系统。核心设计理念：**让专业的 Agent 做专业的事**，通过流水线协作产出高质量内容。

```
用户输入（文字 + 图片）
    │
    ▼
┌─────────────────────────┐
│   Analyzer Agent        │  多模态策略分析
│  （多模态大模型）        │  → DNA匹配 + 卖点提炼 + 图片摘要
└──────────┬──────────────┘
           │ DnaStrategyBrief
           ▼
┌─────────────────────────┐
│   Creator Agent         │  纯文本内容创作
│  （文本大模型）          │  → 小红书笔记 + 配图建议
└──────────┬──────────────┘
           │ GenerateResult
           ▼
┌─────────────────────────┐
│   前端展示层            │  实时进度 + 结果展示
└─────────────────────────┘
```

---

## 2. 核心架构决策

### 2.1 为什么是两 Agent，不是更多？

| 方案 | 优点 | 缺点 |
|------|------|------|
| 单 Agent 一把梭 | 简单，调用一次 | 多模态 + 文本混在一起，质量不可控 |
| 四 Agent（分析+骨架+文案+视觉） | 分工细，理论质量高 | 调用次数多，延迟高，错误累积 |
| **两 Agent（多模态分析 + 文本创作）** | **质量可控 + 延迟可接受** | 每个 Agent 内部复杂度稍高 |

**选择两 Agent 的理由**：
1. **多模态和文本是天然分界** — 看图和写文案是两种完全不同的能力，分开调用效果更好
2. **延迟可控** — 两次 LLM 调用，总耗时 ~15 秒，用户可接受
3. **中间结果可展示** — DnaStrategyBrief 可以直接在前端展示"AI 在想什么"，增强路演效果

### 2.2 为什么用 DNA 库，不是让 LLM 自由发挥？

爆款内容有规律。DNA 库的作用：
1. **风格锚定** — 防止 LLM 输出千篇一律的"通用文案"
2. **结构保证** — 每种 DNA 有明确的内容结构和钩子模板，保证输出有传播性
3. **可解释性** — 用户能看到"为什么这么写"，增强信任感
4. **可扩展性** — 新增风格只需加 DNA 定义，不用改代码

---

## 3. 数据流详解

### 3.1 输入数据契约

```python
class LocalFoodRequest:
    product_name: str           # 产品名称，如"贵州刺梨果干"
    product_category: str       # 产品品类，如"果干"
    origin_place: str           # 产地，如"贵州贵阳"
    target_audience: str        # 目标客群，如"来贵州旅游的年轻女生"
    selling_scene: str | None   # 售卖场景，如"游客伴手礼"
    user_note: str | None       # 用户补充卖点
    image_paths: list[str]      # 上传图片路径（最多3张）
```

### 3.2 Analyzer 输出：DnaStrategyBrief

策略简报是整个系统的"中间枢纽"，连接分析和创作：

```python
class DnaStrategyBrief:
    # 原始输入透传
    product_name / product_category / origin_place / ...
    
    # DNA 匹配结果（主1 + 辅2，权重和=1.0）
    dna_matches: list[DnaMatch]
    #   DnaMatch: dna_id, dna_name, role, weight, reason
    
    # 核心卖点（3-5条）
    key_selling_points: list[str]
    
    # 避坑点（2-3条）
    avoid_points: list[str]
    
    # 用户上传图片的内容摘要（按上传顺序）
    image_summaries: list[str]
    
    # 建议的视觉方向（3-6个）
    suggested_visual_directions: list[str]
```

### 3.3 Creator 输出：GenerateResult

```python
class GenerateResult:
    post: XiaohongshuPost       # 小红书笔记（标题+正文+标签）
    image_suggestions: list[ImageSuggestion]  # 配图建议（3-6张）
    dna_matches: list[DnaMatch]              # DNA 匹配信息（路演展示用）
    key_selling_points: list[str]            # 核心卖点（路演展示用）
```

---

## 4. Agent 详解

### 4.1 Analyzer Agent（多模态策略分析师）

**职责**：看懂产品，定策略

**输入**：`LocalFoodRequest`（文字 + 图片）

**输出**：`DnaStrategyBrief`

**工作流程**：
1. 调用多模态 LLM，读取产品文字信息 + 上传的图片
2. 从 6 种爆款 DNA 中匹配最优组合（主风格 60% + 两个辅助风格各 25%/15%）
3. 提炼 3-5 个核心卖点
4. 提炼 2-3 个避坑点
5. 为每张上传图片生成内容摘要
6. 给出 3-6 个视觉拍摄方向建议

**双路径实现**：
- **LLM 路径** — 多模态大模型分析，质量高
- **规则路径** — 关键词匹配 + 模板拼接，兜底用

### 4.2 Creator Agent（内容创作师）

**职责**：按策略写文案

**输入**：`DnaStrategyBrief`（纯文本）

**输出**：`GenerateResult`

**工作流程**：
1. 根据 DNA 匹配结果加载对应的 DNA 定义（风格调性、内容结构、钩子模板）
2. 调用文本 LLM，融合多种 DNA 风格生成小红书笔记
3. 自主决定配图数量（3-6 张），为每张图生成一句话拍摄建议
4. 如果有上传图片，根据图片摘要安排配图顺序

**双路径实现**：
- **LLM 路径** — 高质量文案生成
- **规则路径** — 模板拼接，保证永远有输出

---

## 5. 爆款 DNA 库

当前内置 6 种 DNA：

| DNA ID | 名称 | 核心调性 | 典型场景 |
|--------|------|---------|---------|
| `bestie_travel_share` | 闺蜜旅游分享风 | 轻松真诚、口语化、种草感 | 游客伴手礼、旅游种草 |
| `gift_guide` | 送礼实用攻略风 | 贴心攻略、场景化、解决"送什么"焦虑 | 节日送礼、长辈/领导送礼 |
| `local_recommend` | 本地人良心推荐风 | 地道正宗、避坑指南、信任感 | 地方特产、美食推荐 |
| `healthy_snack` | 健康零食测评风 | 成分党、数据控、硬核种草 | 减脂期、养生、无添加 |
| `cultural_story` | 文艺治愈故事风 | 文化感、故事性、治愈感 | 古法工艺、地方文化 |
| `contrast_review` | 反差测评种草风 | 强对比、猎奇感、反转种草 | 小众品类、强差异化卖点 |

每种 DNA 包含：
- `name` — 显示名称
- `description` — 风格描述
- `tone` — 调性关键词
- `structure` — 内容结构（段落骨架）
- `hook_patterns` — 钩子模板
- `visual_style` — 视觉风格关键词
- `hashtags_style` — 标签风格

---

## 6. 前端架构

```
App.jsx（状态机）
 ├── InputView          # 输入表单
 ├── GeneratingView     # 生成中（SSE 实时进度）
 └── ResultView         # 结果展示
      ├── XhsPostCard       # 小红书笔记卡片
      ├── ImageSuggestions  # 配图建议
      ├── DnaMatchPanel     # DNA 匹配展示
      └── InfoCard          # 数据概览卡片
```

**核心交互**：
1. 用户在 InputView 填写表单，点击生成
2. App 切换到 GeneratingView，通过 SSE 流式接收进度事件
3. 收到最终 result 事件后，切换到 ResultView 展示结果
4. 点击"重新生成"回到 InputView

---

## 7. 错误处理与兜底

### 7.1 三层容错

```
LLM 调用
  ├─ 失败？→ 重试（最多3次，指数退避）
  └─ 仍失败？→ 规则兜底生成
        └─ 格式解析失败？→ 默认值填充
```

### 7.2 SSE 容错

前端 SSE 解析：
- 事件格式错误 → 跳过，不中断
- 连接中断 → 展示错误信息，允许重试
- 最终未收到 result 事件 → 明确报错

---

## 8. 性能指标

| 指标 | 目标 | 实际（参考） |
|------|------|-------------|
| 端到端生成时间 | ≤ 20s | ~12-18s |
| Analyzer 调用 | ≤ 8s | ~5-8s |
| Creator 调用 | ≤ 10s | ~6-10s |
| 首次进度反馈 | ≤ 2s | ~1s |
| 接口可用性 | ≥ 99% | 双兜底保证 |

---

## 9. 扩展方向（v2 规划）

- [ ] **多平台扩展**：抖音脚本、朋友圈文案、海报文案
- [ ] **生图接入**：直接生成配图，不用用户拍
- [ ] **历史记录**：保存生成记录，支持二次编辑
- [ ] **DNA 自定义**：用户可以上传自己的爆款笔记，训练专属 DNA
- [ ] **批量生成**：一次输入生成多版，用户选最优
- [ ] **效果反馈**：发布后数据回流，优化 DNA 匹配算法
