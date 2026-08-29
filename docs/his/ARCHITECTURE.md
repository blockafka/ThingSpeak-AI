# 乡礼 Spark · 系统架构

> 面向地方食品特产商家的小型 AI 内容策略系统。

## 一、三层结构

```text
web 层
  xiangli_spark/web
  - 输入特产信息、产地、目标人群、传播目标
  - 展示策略识别、模板命中、内容结果

api 层
  xiangli_spark/server
  - POST /api/generate-local-food

core 层
  xiangli_spark/core
  - analyzer: 传播任务识别
  - prompter: 多平台内容骨架编排
  - generator: 视觉卡片建议
  - copywriter: 多平台内容包生成
  - orchestrator: 主流程串联
  - templates: 模板库
```

## 二、主数据流

```text
LocalFoodRequest
  -> build_local_food_strategy_brief
  -> build_local_food_content_plan
  -> suggest_local_food_visual_assets
  -> generate_local_food_content_pack
  -> API response
```

返回结构：

- `strategy_brief`
- `content_plan`
- `generated_pack`

## 三、模板系统

第一版模板：

- `difference_seed`
- `gift_scene`
- `local_story_seed`
- `story_boost`

默认策略：

- 差异点种草模板（主）
- 地方故事增强段（辅）

## 四、第一版示例场景

- 特产：贵州刺梨果干
- 场景：游客伴手礼
- 目标：种草引流优先，地方故事增强

## 五、验证思路

不承诺“制造爆款”，而是验证：

- 比商家裸写更有结构
- 比普通模型裸写更有地方性
- 更贴近平台传播表达

推荐对比：

1. 商家原始裸写
2. 普通模型裸写
3. 模板策略生成

## 六、说明

该目录当前只围绕“乡礼 Spark”新项目维护。旧的家装内容生成叙事已不再作为当前项目的主要定义。