# 第一阶段后端 Spec：Original Files、Intake Orchestrator 与 File Registry

> 状态：Draft  
> 版本：0.1  
> 后端技术选型：Python + FastAPI  
> 对应总体设计：[`初始路由系统-spec.md`](初始路由系统-spec.md)  
> 对应前端：[`../frontend/`](../frontend/)

## 1. 结论

第一阶段后端采用 **Python + FastAPI**。

本阶段只实现以下闭环：

```text
Browser / API Client
        |
        v
Intake API
        |
        v
Intake Orchestrator
        |--------------------|
        v                    v
Original File Store     File Registry
不可变二进制存储          文件身份、来源、哈希、重复关系
```

本阶段不实现 Inspector、Router、Review、Dispatcher 或任何类别 Handler。文件成功接入后的最终状态是 `registered`，而不是 `routing`、`review` 或 `processing`。

## 2. 技术栈与依赖

### 2.1 技术栈

- 运行时：Python 3.12+；
- Web API：FastAPI；
- API 契约：OpenAPI + JSON Schema；
- 数据校验与配置：Pydantic；
- Registry：SQLite；
- ORM 与迁移：SQLAlchemy 2、Alembic；
- 前端：React + TypeScript，通过 OpenAPI 生成 API Client；
- Original File：本地文件系统中的内容寻址存储。

### 2.2 运行依赖

- `fastapi`：HTTP API、依赖注入和 OpenAPI；
- `uvicorn`：ASGI Server；
- `pydantic`：请求、响应和领域边界数据校验；
- `pydantic-settings`：环境配置；
- `sqlalchemy`：Registry 持久化；
- `alembic`：数据库迁移；
- `python-multipart`：multipart 文件上传；
- `anyio`：异步流程与受控线程调用。

文件流式写入、SHA-256、临时文件、原子提升和路径处理优先使用 Python 标准库中的 `hashlib`、`tempfile`、`pathlib` 和 `os`。

### 2.3 开发依赖

- `pytest`；
- `pytest-asyncio`；
- `httpx`；
- `ruff`；
- `mypy`。

依赖的确切版本在 `pyproject.toml` 和锁文件中固定。本阶段不引入 Celery、Redis、Pandas、文档解析库或 LLM SDK。

## 3. 范围

### 3.1 本阶段包含

- 接收单个或多个文件上传；
- 为一次提交创建摄取批次；
- 对上传内容进行流式落盘，避免整文件进入内存；
- 上传过程中计算 SHA-256；
- 保存不可变的 Original File Blob；
- 创建 FileRecord；
- 识别物理重复内容并复用 Blob；
- 保留每次提交记录和重复关系；
- 查询摄取批次；
- 分页查询文件登记记录；
- 查询单个文件详情；
- 在权限允许时下载原始文件；
- 提供统一错误响应、结构化日志和基础健康检查；
- 为前端提供稳定的 OpenAPI 契约。

### 3.2 本阶段不包含

- 文档文本抽取和内容采样；
- PDF OCR；
- 工作表、标题、段落等结构检查；
- 五类文件分类；
- LLM 调用；
- 路由审核与人工改判；
- Handler 派发；
- 项目背景抽取或数据集画像；
- 文件移动到正式知识库；
- 解压归档文件；
- 后台任务队列和分布式执行；
- 用户账户、组织和完整 RBAC。

## 4. 领域边界

### 4.1 Original File

Original File 表示系统实际接收到的原始字节内容。

核心规则：

- 内容一旦注册成功就不可修改；
- 存储路径不能由用户提供的文件名直接决定；
- 相同 SHA-256 和大小的内容只保存一份 Blob；
- 删除、替换和覆盖不属于本阶段 API；
- 下载时恢复原始展示文件名，但磁盘存储不使用该名称；
- Handler 或未来 Agent 只能获得只读引用。

### 4.2 FileRecord

FileRecord 表示“一次提交中的一个文件”。它不是物理 Blob 本身。

同一内容被提交两次时：

```text
FileRecord A ----+
                 +----> OriginalBlob sha256:abc...
FileRecord B ----+
```

系统保留两个 FileRecord，以便追踪不同批次、项目、来源和提交时间；物理内容只保存一次。

### 4.3 IngestBatch

IngestBatch 表示一次上传操作，可以包含多个文件。

批次采用部分成功语义：某个文件失败不回滚已经成功登记的其他文件。批次最终状态由文件结果汇总得到：

- `completed`：所有文件登记成功；
- `partial`：至少一个成功、至少一个失败；
- `failed`：所有文件失败。

### 4.4 Intake Orchestrator

Intake Orchestrator 负责应用层编排：

1. 校验摄取请求；
2. 创建批次；
3. 为每个文件分配 FileRecord ID；
4. 调用 OriginalFileStore 流式保存文件并计算哈希；
5. 调用 FileRegistry 查询重复内容与已有记录；
6. 原子提交 Blob 元数据和 FileRecord；
7. 汇总并完成批次；
8. 返回每个文件的独立结果。

它不直接依赖具体磁盘路径或 SQL 表，而是通过端口接口访问存储实现。

### 4.5 OriginalFileStore 与 FileRegistry 的存储边界

| 组件 | 存储内容 | 不存储的内容 |
| --- | --- | --- |
| `OriginalFileStore` | 上传文件的真实二进制内容；相同内容只保存一个不可变 Blob | 项目、批次、来源、业务状态和路由信息 |
| `FileRegistry` | IngestBatch、FileRecord、OriginalBlob 元数据、哈希、状态、来源和重复关系 | 文件二进制正文 |
| `staging` | 上传过程中的临时字节 | 已完成登记的长期文件 |

浏览器上传的字节先进入 staging。注册成功后，staging 文件被原子提升为 OriginalFileStore 中的 Blob，或者在发现相同 Blob 已存在时被清理。因此成功流程最终只保留一份持久化原始内容，不同时保留 staging 副本。

SQLite 只保存 Registry 元数据和 `storage_key`，不使用 BLOB 字段保存文件正文。

## 5. 总体架构

```text
+-------------------+
| React Frontend    |
+---------+---------+
          | multipart/form-data / JSON
          v
+-------------------+
| FastAPI Routes    |
| validation/auth   |
+---------+---------+
          |
          v
+---------------------------+
| Intake Orchestrator       |
| batch + per-file workflow |
+------+--------------------+
       |
       +--------------------------+
       |                          |
       v                          v
+-------------------+    +----------------------+
| OriginalFileStore |    | FileRegistry         |
| temp/hash/promote |    | records/dedup/query  |
+---------+---------+    +----------+-----------+
          |                           |
          v                           v
+-------------------+    +----------------------+
| Local filesystem  |    | SQLite               |
| runtime/originals |    | registry.db          |
+-------------------+    +----------------------+
```

### 5.1 API 层

API 层只负责：

- HTTP 和 multipart 解析；
- Pydantic 请求校验；
- 调用应用服务；
- 将领域错误转换为 HTTP Problem Details；
- 返回 DTO。

API 路由不能直接操作 SQLite 或拼接文件路径。

### 5.2 应用层

应用层实现 Intake Orchestrator 和查询服务，负责事务边界、幂等性与流程编排。

### 5.3 领域层

领域层定义 IngestBatch、FileRecord、OriginalBlob、状态枚举和存储端口，不依赖 FastAPI、SQLAlchemy 或本地文件系统。

### 5.4 基础设施层

基础设施层提供：

- SQLite/SQLAlchemy Registry；
- LocalOriginalFileStore；
- 数据库迁移；
- 日志和配置实现。

## 6. 数据模型

### 6.1 IngestBatch

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `batch_id` | UUID string | 批次 ID |
| `project_id` | string | 所属项目稳定 ID |
| `source_kind` | enum | `user-upload`、`system-import`、`watcher` |
| `source_description` | string/null | 来源补充说明 |
| `submitted_by` | string/null | 提交主体；未接入认证前为可选审计字段 |
| `idempotency_key` | string | 客户端生成的幂等键 |
| `status` | enum | `receiving`、`completed`、`partial`、`failed` |
| `total_count` | integer | 请求文件数 |
| `registered_count` | integer | 成功登记数 |
| `failed_count` | integer | 失败数 |
| `created_at` | UTC datetime | 创建时间 |
| `completed_at` | UTC datetime/null | 完成时间 |

约束：`idempotency_key` 唯一。相同键重试时返回首次请求结果，不创建新批次。

### 6.2 OriginalBlob

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `sha256` | char(64) | 内容地址和主键 |
| `size_bytes` | integer | 实际接收字节数 |
| `storage_key` | string | 服务内部存储键，不是用户路径 |
| `detected_media_type` | string/null | 轻量识别结果 |
| `integrity_status` | enum | `available`、`missing`、`corrupt` |
| `created_at` | UTC datetime | 首次保存时间 |

本阶段 Blob 不提供业务删除接口。

### 6.3 FileRecord

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file_id` | UUID string | 文件登记 ID |
| `batch_id` | UUID string | 所属批次 |
| `project_id` | string | 所属项目 |
| `original_name` | string | 用户提交的原始名称，仅作为元数据 |
| `display_name` | string | 清理控制字符后的展示名称 |
| `client_media_type` | string/null | 客户端声明的 Content-Type，不视为可信事实 |
| `detected_media_type` | string/null | 服务端轻量识别结果 |
| `extension` | string/null | 规范化为小写且不含点 |
| `size_bytes` | integer | 文件大小 |
| `sha256` | char(64) | 指向 OriginalBlob |
| `duplicate_of_file_id` | UUID/null | 指向同项目或系统内最早登记记录 |
| `source_uri` | string/null | 外部来源引用；上传文件通常为空 |
| `status` | enum | `registered`、`failed` |
| `failure_code` | string/null | 标准错误码 |
| `failure_message` | string/null | 安全、可展示的错误说明 |
| `registered_at` | UTC datetime/null | 登记完成时间 |
| `created_at` | UTC datetime | 记录创建时间 |

### 6.4 重复语义

必须区分：

- **Blob 去重**：全局按 `sha256 + size_bytes` 复用物理内容；
- **Record 重复关系**：FileRecord 通过 `duplicate_of_file_id` 表示内容曾登记过；
- **批次幂等**：通过 `Idempotency-Key` 防止网络重试创建新批次。

即使是重复文件，FileRecord 状态仍为 `registered`，重复不是失败。

## 7. 状态模型

### 7.1 批次状态

```text
receiving
  -> completed
  -> partial
  -> failed
```

终态不可逆。本阶段不提供批次重开。

### 7.2 文件状态

应用内部可以经历：

```text
receiving -> hashing -> storing -> registered
                            \----> failed
```

数据库对外只需要稳定保存 `registered` 或 `failed`；进行中的细粒度状态可以通过日志表达。后续加入异步队列时再持久化完整状态机。

### 7.3 一致性边界

单个文件注册的完成条件是：

1. Blob 已经原子提升到不可变存储区；
2. OriginalBlob 元数据已存在；
3. FileRecord 已提交；
4. FileRecord 可以解析到真实存在的 Blob。

如果 Blob 已提升但数据库事务失败，该 Blob 是可回收的孤立对象。维护任务可以根据宽限期清理，但正常请求不能立即删除，以免与并发注册竞争。

## 8. Original File 存储设计

### 8.1 目录布局

```text
judge_tool/runtime/
├── staging/
│   └── {batch_id}/
│       └── {file_id}.upload
├── originals/
│   └── sha256/
│       └── ab/
│           └── cd/
│               └── abcdef...        # 完整 SHA-256 作为文件名
└── registry/
    └── registry.db
```

原始名称不出现在磁盘路径中。`ab/cd` 使用哈希前四位分片，防止单目录文件过多。

### 8.2 写入流程

1. 在当前批次 staging 目录创建随机临时文件；
2. 以配置的 chunk size 循环读取上传流；
3. 每个 chunk 同时写入磁盘并更新 SHA-256；
4. 累计实际大小并执行单文件、批次大小限制；
5. 完成后关闭文件，得到最终哈希；
6. 如果目标 Blob 已存在，校验大小后复用；
7. 如果不存在，将 staging 文件原子提升到目标路径；
8. 设置只读属性作为额外保护，但不可变性主要由服务权限和 API 保证；
9. 提交 Registry 事务。

禁止：

- 使用 `UploadFile.filename` 拼接目标路径；
- 在内存中一次性读取整个文件；
- 在数据库提交前向外返回 `registered`；
- 覆盖已经存在且大小不一致的 Blob。

### 8.3 并发写入相同 Blob

两个请求可能同时上传相同内容。LocalOriginalFileStore 必须使用排他创建或原子重命名处理竞争：

- 一个请求成功创建目标 Blob；
- 另一个请求发现目标已存在，校验大小后丢弃自己的 staging 临时文件并复用目标；
- 不允许先删除目标再替换。

## 9. API 设计

所有接口使用 `/api/v1` 前缀。时间统一返回 UTC ISO 8601，大小统一返回整数 `size_bytes`，前端负责本地化显示。

### 9.1 创建摄取批次

```http
POST /api/v1/intake/batches
Content-Type: multipart/form-data
Idempotency-Key: <client-generated-uuid>
```

表单字段：

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `project_id` | 是 | 项目稳定 ID |
| `source_kind` | 是 | 默认 `user-upload` |
| `source_description` | 否 | 用户可读来源说明 |
| `submitted_by` | 否 | 当前阶段可选 |
| `files` | 是 | 一个或多个文件，可重复字段 |

成功响应：`201 Created`

```json
{
  "batch_id": "47b0c2d7-3c76-4b93-b25c-d053a32e9df5",
  "project_id": "hlx1102-pdu-poc",
  "status": "completed",
  "total_count": 2,
  "registered_count": 2,
  "failed_count": 0,
  "created_at": "2026-09-24T02:10:00Z",
  "completed_at": "2026-09-24T02:10:03Z",
  "files": [
    {
      "file_id": "f23804c9-f6fe-44e2-9df4-148eb5fab619",
      "original_name": "项目启动会议纪要.docx",
      "display_name": "项目启动会议纪要.docx",
      "size_bytes": 2516582,
      "extension": "docx",
      "sha256": "8f07b54d...",
      "status": "registered",
      "duplicate_of_file_id": null,
      "registered_at": "2026-09-24T02:10:02Z"
    }
  ]
}
```

部分成功仍返回 `201 Created`，批次状态为 `partial`，失败文件在 `files` 中包含 `failure_code` 和安全错误说明。

整个请求无法建立批次时返回 4xx/5xx，例如元数据不合法、没有文件、文件数量超过上限或幂等键冲突。

### 9.2 查询批次

```http
GET /api/v1/intake/batches/{batch_id}
```

返回批次及其文件结果。用于上传完成后的恢复和页面刷新。

### 9.3 查询文件列表

```http
GET /api/v1/files?project_id=...&status=registered&limit=50&cursor=...
```

规则：

- 使用游标分页，不使用不稳定的大偏移分页；
- 默认按 `created_at desc, file_id desc`；
- `limit` 默认 50，最大值由配置决定；
- 第一阶段支持按 `project_id`、`status`、`sha256` 筛选；
- 返回 Registry 字段，不伪造路由类别、置信度或 Handler 状态。

### 9.4 查询文件详情

```http
GET /api/v1/files/{file_id}
```

返回 FileRecord、批次来源摘要和 Blob 完整性状态。

### 9.5 下载原始文件

```http
GET /api/v1/files/{file_id}/content
```

要求：

- 通过 FileRecord 解析 Blob，不能接收任意磁盘路径；
- 使用安全的 `Content-Disposition`；
- 支持流式响应；
- 记录下载审计事件；
- 接入认证后必须执行项目权限检查。

### 9.6 健康检查

```http
GET /api/v1/health/live
GET /api/v1/health/ready
```

- `live` 只表示进程存活；
- `ready` 检查 Registry 可连接、存储根目录可访问且配置有效。

## 10. 错误契约

错误响应采用 `application/problem+json`：

```json
{
  "type": "https://context-router.local/problems/file-too-large",
  "title": "File exceeds configured size limit",
  "status": 413,
  "code": "file-too-large",
  "detail": "文件超过当前允许的单文件大小。",
  "request_id": "req_..."
}
```

首版错误码至少包括：

- `invalid-request`；
- `missing-idempotency-key`；
- `idempotency-conflict`；
- `too-many-files`；
- `file-too-large`；
- `batch-too-large`；
- `unsupported-extension`；
- `empty-file`；
- `storage-unavailable`；
- `registry-unavailable`；
- `integrity-conflict`；
- `batch-not-found`；
- `file-not-found`。

响应不得暴露绝对磁盘路径、数据库语句或 Python 堆栈。

## 11. 配置

使用环境变量和 Pydantic Settings。建议前缀为 `CONTEXT_ROUTER_`。

| 配置 | 示例 | 说明 |
| --- | --- | --- |
| `ENV` | `development` | 运行环境 |
| `DATABASE_URL` | `sqlite:///.../registry.db` | Registry 连接 |
| `RUNTIME_ROOT` | `.../judge_tool/runtime` | 运行数据根目录 |
| `MAX_FILE_BYTES` | `262144000` | 单文件上限；示例 250 MiB |
| `MAX_BATCH_BYTES` | `1073741824` | 单批次总大小上限；示例 1 GiB |
| `MAX_FILES_PER_BATCH` | `100` | 单批次文件数上限 |
| `UPLOAD_CHUNK_BYTES` | `1048576` | 流式写入块大小 |
| `ALLOWED_EXTENSIONS` | `pdf,docx,xlsx,md,csv,txt` | 初始允许扩展名 |
| `CORS_ORIGINS` | `http://127.0.0.1:5173` | 开发环境前端地址 |

表中大小是初始示例，实际值应由运行环境确认，不写死在业务代码中。

## 12. SQLite 与运行约束

第一阶段使用 SQLite，原因是系统当前定位为本地单实例原型，部署和备份成本最低。

约束：

- 开启 foreign keys；
- 开启 WAL；
- 设置合理 busy timeout；
- 本地 MVP 使用一个 Uvicorn worker；
- 数据库变更通过 Alembic 管理；
- Registry Repository 不泄漏 SQLite 特性，未来可替换 PostgreSQL。

以下情况应迁移到 PostgreSQL：

- 多实例部署；
- 持续高并发写入；
- 需要复杂审核查询和权限模型；
- 需要集中式备份、高可用或跨主机访问。

## 13. 安全要求

- 文件名按不可信输入处理，移除控制字符并限制显示长度；
- 禁止 `..`、绝对路径、盘符和符号链接影响目标路径；
- 不信任客户端 Content-Type；
- 扩展名只用于接入政策，不能证明真实格式；
- 上传必须流式处理并在读取期间执行大小限制；
- 空文件默认拒绝，可通过未来政策显式放开；
- 本阶段不解压 ZIP，不执行宏，不渲染文档；
- 服务进程对 originals 目录只需要创建和读取权限，不暴露通用文件浏览接口；
- 日志不得记录文件正文或完整敏感路径；
- SHA-256 用于完整性和去重，不替代恶意文件扫描；
- 正式部署前需要在 API 前增加身份认证、项目权限检查和请求限流。

## 14. 可观测性

每个请求生成 `request_id`，每次摄取保留 `batch_id`，每个文件保留 `file_id`。结构化日志至少包含：

- 请求开始和结束；
- 批次创建与完成；
- 单文件登记成功或失败；
- 接收字节数和耗时；
- 是否复用已有 Blob；
- 错误码；
- 数据库和存储健康状态。

不得在普通日志中记录文件内容、完整哈希以外的敏感业务字段或服务器绝对路径。

首版指标：

- `intake_batches_total`；
- `intake_files_total{status}`；
- `intake_bytes_total`；
- `intake_duration_seconds`；
- `duplicate_blobs_total`；
- `storage_errors_total`；
- `registry_errors_total`。

## 15. 后端代码目录规划

```text
judge_tool/
├── backend/
│   ├── pyproject.toml
│   ├── README.md
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   ├── error_handlers.py
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── intake.py
│   │   │       └── files.py
│   │   ├── application/
│   │   │   ├── intake/
│   │   │   │   ├── commands.py
│   │   │   │   ├── orchestrator.py
│   │   │   │   └── results.py
│   │   │   └── queries/
│   │   │       ├── get_batch.py
│   │   │       ├── get_file.py
│   │   │       └── list_files.py
│   │   ├── domain/
│   │   │   ├── models.py
│   │   │   ├── enums.py
│   │   │   ├── errors.py
│   │   │   └── ports/
│   │   │       ├── file_registry.py
│   │   │       └── original_file_store.py
│   │   ├── infrastructure/
│   │   │   ├── database/
│   │   │   │   ├── base.py
│   │   │   │   ├── session.py
│   │   │   │   ├── tables.py
│   │   │   │   └── registry_repository.py
│   │   │   └── storage/
│   │   │       └── local_original_file_store.py
│   │   ├── schemas/
│   │   │   ├── batches.py
│   │   │   ├── files.py
│   │   │   └── problems.py
│   │   └── core/
│   │       ├── config.py
│   │       ├── logging.py
│   │       ├── ids.py
│   │       └── clock.py
│   └── tests/
│       ├── unit/
│       │   ├── test_intake_orchestrator.py
│       │   └── test_local_original_file_store.py
│       ├── integration/
│       │   ├── test_intake_api.py
│       │   ├── test_file_queries.py
│       │   └── test_registry_repository.py
│       ├── contract/
│       │   ├── test_file_registry_contract.py
│       │   └── test_original_file_store_contract.py
│       └── fixtures/
├── frontend/
├── specs/
└── runtime/                 # 不纳入 Git
    ├── staging/
    ├── originals/
    └── registry/
```

### 15.1 依赖方向

```text
api -> application -> domain
infrastructure -------> domain ports
```

领域层不能导入 FastAPI、SQLAlchemy 或本地存储实现。Application 层依赖端口，`main.py` 负责组装实际实现。

### 15.2 依赖管理

运行依赖和开发依赖以第 2 节为准，由 `pyproject.toml` 统一声明并通过锁文件固定。应用代码不得依赖仅在开发环境安装的测试、格式化或类型检查工具。

## 16. 与现有前端的契约

现有前端的 `RoutingFile` 同时包含 Registry、Router 和 Handler 字段。第一阶段后端不能为了适配 Mock 数据而伪造尚不存在的路由结果。

前端接入时应拆分类型：

```typescript
interface FileRecordDto {
  fileId: string;
  batchId: string;
  projectId: string;
  originalName: string;
  displayName: string;
  extension?: string;
  sizeBytes: number;
  sha256: string;
  status: "registered" | "failed";
  duplicateOfFileId?: string;
  registeredAt?: string;
}
```

前端第一阶段页面状态应表达：

```text
uploading -> registered | failed
```

以下字段在 Router 上线前必须为空或不展示：

- `category`；
- `secondarySignals`；
- `confidence`；
- `disposition`；
- 路由 `reasons`；
- Handler 处理状态。

推荐从 `/openapi.json` 生成 API Client，并在前端 Adapter 中完成：

- `size_bytes` 到本地显示字符串；
- ISO 时间到本地时间；
- snake_case DTO 到现有视图模型的转换。

## 17. 测试策略

### 17.1 单元测试

- 文件名清理但保留 Unicode；
- chunk 边界与 SHA-256 正确；
- 单文件和批次大小限制；
- 幂等键重复；
- 批次状态汇总；
- 重复 Blob 复用；
- duplicate FileRecord 关系；
- Orchestrator 部分失败行为；
- 路径穿越输入不能影响存储路径。

### 17.2 Contract 测试

对 FileRegistry 和 OriginalFileStore 的所有实现运行同一套端口契约，保证未来替换 PostgreSQL 或对象存储时语义不变。

### 17.3 集成测试

- 单文件上传并查询；
- 多文件全部成功；
- 多文件部分失败；
- 相同文件重复提交只保存一个 Blob；
- 相同幂等键重试返回原批次；
- 相同幂等键但元数据冲突返回 409；
- 上传超限返回标准错误；
- 服务重启后记录和文件仍可读取；
- 数据库存在但 Blob 缺失时详情显示完整性异常；
- 下载响应使用安全文件名且内容哈希一致。

### 17.4 验收测试

使用真实浏览器从当前前端提交 PDF、DOCX、XLSX、Markdown、CSV 和 TXT 文件：

1. 页面显示上传进度；
2. 上传完成后显示 `registered`；
3. 刷新页面后记录仍存在；
4. 文件详情显示真实大小、哈希、来源和重复关系；
5. 后端磁盘中没有使用原始文件名构造的路径；
6. 重复提交不会复制 Blob；
7. 前端不显示虚假的分类和置信度。

## 18. 实施顺序

### M1：工程骨架

- 建立 FastAPI 应用、配置、日志和 Problem Details；
- 建立 SQLite、SQLAlchemy 和 Alembic；
- 实现健康检查。

### M2：Original File Store

- 实现 staging、流式写入、SHA-256 和原子提升；
- 实现大小限制、路径安全和并发重复处理；
- 完成端口 Contract 测试。

### M3：File Registry

- 实现三张核心表和 Repository；
- 实现重复查询、批次查询和文件分页；
- 完成数据库迁移及集成测试。

### M4：Intake Orchestrator 与 API

- 实现多文件编排、部分成功和幂等性；
- 实现上传、批次、文件列表、详情和下载 API；
- 发布 OpenAPI。

### M5：前端接入

- 生成 TypeScript Client；
- 将模拟上传替换为真实 API；
- 分离 Registry DTO 与未来 Routing DTO；
- 完成浏览器验收测试。

## 19. 第一阶段完成定义

满足以下条件时，本阶段后端完成：

1. 所有上传通过唯一的 Intake API 进入；
2. 上传过程不会一次性把完整文件读入内存；
3. 每个成功文件都具有稳定 FileRecord、SHA-256 和可解析的只读 Blob；
4. 相同内容只保存一份 Blob，但每次提交都保留独立 FileRecord；
5. 多文件批次支持部分成功，并能在刷新后查询；
6. 幂等重试不会重复创建批次；
7. 原始名称不能影响磁盘路径；
8. 前端能够显示真实登记记录、失败原因和重复关系；
9. API 不返回虚假的路由类别、置信度或 Handler 状态；
10. 单元、Contract、集成和浏览器验收测试全部通过；
11. Registry 数据和 Original Blob 能够通过备份一起恢复；
12. Inspector 可以在下一阶段仅通过 FileRecord 和只读 Blob 引用接入，而不修改本阶段接口。
