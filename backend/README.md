# Context Router Backend

第一阶段后端实现 Original Files、Intake Orchestrator 和 File Registry。

## 安装

```powershell
uv sync
```

## 数据库迁移

```powershell
uv run alembic upgrade head
```

应用启动时也会自动执行 `alembic upgrade head`，保证本地运行与正式迁移使用同一路径。

## 启动

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- OpenAPI：`http://127.0.0.1:8000/openapi.json`
- Swagger UI：`http://127.0.0.1:8000/docs`
- Ready check：`http://127.0.0.1:8000/api/v1/health/ready`

数据库对已登记文件的 SHA-256 施加唯一约束，同一内容只保留一条 `file_records` 记录；纯重复上传不会保留新的 `ingest_batches`。重复项只通过本次上传响应的 `duplicates` 返回给前端，不写入 Registry，后端不提供 Reset 接口。

## 验证

```powershell
uv run ruff check .
uv run mypy app
uv run pytest
```

默认运行数据位于 `../runtime/`，不会进入 Git。
