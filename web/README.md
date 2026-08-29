# 乡礼 Spark - Frontend & API Server

这是“乡礼 Spark”的前端演示与 API 说明目录。

## 当前产品

一个面向地方食品特产商家的 AI 内容策略助理：

- 输入特产信息、产地、目标人群、传播目标
- 识别传播任务
- 匹配模板
- 输出多平台内容包

## 第一版 Demo

推荐场景：

- 产品：贵州刺梨果干
- 场景：游客伴手礼
- 目标：种草引流优先，地方故事增强

## 前端职责

- 输入地方食品特产请求
- 调用 `/api/generate-local-food`
- 展示：
  - 主传播任务
  - 次传播任务
  - 命中的模板
  - 推荐表达重点
  - 小红书 / 抖音 / 朋友圈 / 故事增强
  - 视觉建议

## 运行

```bash
cd xiangli_spark/web
./node_modules/.bin/vite
```

## 构建

```bash
cd xiangli_spark/web
npm run build
```

## 后端接口

主接口：

- `POST /api/generate-local-food`

返回：

- `strategy_brief`
- `content_plan`
- `generated_pack`

## 说明

本目录为乡礼 Spark 前端，使用 React + Vite + Tailwind CSS 构建。