# Context Router Frontend

基于 React 与 TypeScript 的知识文件摄取和路由工作台，对应《初始路由系统 Spec》中的控制面与处理器状态展示。

视觉设计与复用规则见 [`docs/视觉设计规范.md`](docs/视觉设计规范.md)。

## 已实现页面

- **路由总览**：核心指标、摄取管线、类别分布与最近文件；
- **文件摄取**：拖拽或选择文件，展示统一入口和摄取记录；
- **路由审核**：搜索、分类筛选、置信度展示、人工改判与确认派发；
- **类别处理器**：分别展示项目资料、业务知识、架构、结果和问题五个独立 Handler；
- **文件详情**：展示分类建议、次级信号、判断依据、来源、哈希和策略版本。

当前使用类型完整的本地模拟数据。文件选择会模拟“登记 → 路由 → 人工复核”流程，不会读取或上传文件内容。

## 本地运行

```bash
pnpm install
pnpm run dev
```

默认地址为 `http://127.0.0.1:5173/`。

## 构建验证

```bash
pnpm run typecheck
pnpm run build
```

## 后端接入边界

后续接入真实服务时，保留 `src/types.ts` 中的前端领域类型，并将 `src/data/mockData.ts` 替换为 API Client。推荐对应以下接口：

```text
POST /api/ingest
GET  /api/files
GET  /api/files/:fileId
GET  /api/routing/reviews
POST /api/routing/reviews/:decisionId/approve
GET  /api/handlers
```

后端返回字段应以 Spec 中的 `FileRecord`、`RoutingDecision` 和 `HandlerResult` 为准。
