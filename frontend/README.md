# Context Router Frontend

基于 React 与 TypeScript 的知识文件摄取和路由工作台，对应《初始路由系统 Spec》中的控制面与处理器状态展示。

视觉设计与复用规则见 [`docs/视觉设计规范.md`](docs/视觉设计规范.md)。

## 已实现页面

- **路由总览**：核心指标、摄取管线、类别分布与最近文件；
- **文件摄取**：拖拽或选择文件，展示统一入口和摄取记录；
- **路由审核**：搜索、分类筛选、置信度展示、人工改判与确认派发；
- **类别处理器**：分别展示项目资料、业务知识、架构、结果和问题五个独立 Handler；
- **文件详情**：展示分类建议、次级信号、判断依据、来源、哈希和策略版本。
- **显示偏好**：支持持久化字号档位及日间/夜间模式切换。

第一阶段已经接入 FastAPI 后端，文件选择会执行真实上传、SHA-256 计算、Blob 去重和 File Registry 登记。完整的 Inspector、Router、人工复核和五个 Handler 前端结构继续保留；尚未实现的模块显示明确的实施状态，不生成虚假的类别、置信度、处理数量或成功率。

后端数据库不会为相同内容新增第二条文件或空重复批次记录。重复上传项只保留在当前前端状态中，并在最新文件和全部文件列表显示“内容重复”；“Reset 去重”由前端直接移除这些临时项，不调用后端接口。

## 本地运行

```bash
pnpm install
pnpm run dev
```

默认地址为 `http://127.0.0.1:5173/`。

启动前需要在 `../backend/` 运行后端服务：

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

默认 API 地址为 `http://127.0.0.1:8000/api/v1`。需要修改时设置：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## 构建验证

```bash
pnpm run typecheck
pnpm run build
```

## 当前后端接口

```text
POST /api/v1/intake/batches
GET  /api/v1/intake/batches/:batchId
GET  /api/v1/files
GET  /api/v1/files/:fileId
GET  /api/v1/files/:fileId/content
```

前端 API DTO 位于 `src/api/client.ts`，Handler 实施目录位于 `src/data/systemCatalog.ts`。`src/data/mockData.ts` 仅保留早期视觉样例，不会载入运行界面，也不参与文件上传、登记或 Handler 状态展示。
