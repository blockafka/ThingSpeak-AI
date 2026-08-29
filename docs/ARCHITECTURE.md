# 物言 · 系统架构

> v1.1 · 两 Agent 流水线 · 六维细粒度 DNA 组合

## 1. 总览

用户输入产品文字和可选图片后，Analyzer 从六个独立 DNA 维度各选一个片段，Creator 将这六个片段融合成一篇小红书笔记。

Analyzer 和 Creator 使用 OpenAI 兼容协议调用 SiliconFlow；默认模型为 `Pro/moonshotai/Kimi-K2.6`。

```text
用户输入（文字 + 图片）
    │
    ▼
┌──────────────────────────────┐
│ Fine-grained DNA Library      │  6 个 JSON 文件 × 20 条
│ scene / value / hook / ...    │  按 score 取每维度 Top 10
└──────────────┬───────────────┘
               │ 六组候选池
               ▼
┌──────────────────────────────┐
│ Analyzer Agent                │  一次 LLM 调用
│ 多模态策略分析                │  每个维度选 1 条 + 卖点/视觉摘要
└──────────────┬───────────────┘
               │ DnaStrategyBrief
               ▼
┌──────────────────────────────┐
│ Creator Agent                │  纯文本 LLM
│ 内容创作                      │  融合六条片段 → 笔记 + 配图建议
└──────────────┬───────────────┘
               │ GenerateResult
               ▼
          前端展示层
```

## 2. DNA 片段库

### 2.1 文件组织

```text
wuyan_ai/core/dnas/
├── fragments/
│   ├── scene.json
│   ├── value_promise.json
│   ├── hook.json
│   ├── structure.json
│   ├── tone.json
│   └── visual_style.json
├── library.py
└── __init__.py
```

每个 JSON 是一个数组，包含 20 条同类型片段。旧的整体风格 JSON 已删除，不再作为运行时数据源。

### 2.2 片段数据结构

```json
{
  "fragmentId": "hook_001",
  "type": "hook",
  "value": "价格对比 + 结果反差",
  "state": "stable",
  "score": 0.95,
  "performanceScore": 0.93,
  "freshnessScore": 0.97,
  "confidenceScore": 0.86,
  "evidenceIds": ["mock_seed_hook_001"],
  "version": "1.0"
}
```

当前的三个分项分数和 `evidenceIds` 是 Mock 数据，暂不代表真实平台数据。

### 2.3 加载和召回 API

`wuyan_ai.core.dnas.library` 提供：

- `list_fragments(type=None)`：读取全部片段或某个维度
- `get_fragment(fragment_id)`：按 ID 读取片段
- `get_top_fragments(type, limit=10)`：按 score 取单维度 Top-K，过滤 `retired`
- `get_top_fragments_by_type(limit=10)`：一次返回六组候选池
- `reload_library()`：清空缓存并重新读取 JSON

库在首次访问时加载并缓存在内存中；修改 JSON 后调用 `reload_library()` 或重启服务即可生效。

## 3. Analyzer Agent

### 输入

`LocalFoodRequest`：产品名、品类、产地、目标人群、可选售卖场景、备注和最多 3 张图片。

### 工作流

1. 调用 `get_top_fragments_by_type(limit=10)`，得到六组候选。
2. 将产品信息、图片情况和六组候选拼成一个提示词。
3. 一次调用多模态或纯文本 LLM。
4. 校验模型返回的 `fragmentId` 是否来自对应候选池，且六个维度各出现一次。
5. 根据合法 ID 补回片段内容、score 和 version，生成 `DnaStrategyBrief`。

LLM 返回不合法或调用失败时，规则兜底选择每个维度的 Top 1，并继续生成结果。

### 输出

```python
class DnaStrategyBrief:
    selected_fragments: list[DnaFragmentSelection]  # 六个维度各一条
    key_selling_points: list[str]
    avoid_points: list[str]
    image_summaries: list[str]
    suggested_visual_directions: list[str]
```

## 4. Creator Agent

Creator 只接收文本，不重复读取图片。它根据 `selected_fragments` 中的六条内容，分别把它们用于：

- `scene`：决定叙事场景
- `valuePromise`：决定用户收益
- `hook`：决定开头
- `structure`：决定正文顺序
- `tone`：决定表达口吻
- `visualStyle`：决定配图建议

输出仍然是标题、正文、标签和 3-6 条配图建议。

## 5. 前端数据流

SSE 事件保持两步进度：

1. `analyzing/start`：开始分析
2. `analyzing/done`：返回 `selected_fragments` 和核心卖点预览
3. `creating/start`：开始创作
4. `creating/done`：内容生成完成
5. `result`：返回 `GenerateResult`

结果页按六个维度展示片段值和静态 score，不再显示“主 DNA / 辅助 DNA / 权重”。

## 6. 明确暂不实现的部分

- 参考笔记的多模态 DNA 自动提取
- 候选片段缓存区和候选晋级
- 一键发布、发布记录和指标回收
- performance/freshness/confidence 的真实计算
- DNA 状态机和自动淘汰

这些字段已经留在 Mock 数据中，后续接入真实数据时无需重新设计调用方契约。
