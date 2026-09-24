# 初始路由系统 Spec

> 状态：Draft  
> 版本：0.1  
> 适用范围：`judge_tool` 文件摄取与知识管理流水线  
> 顶层分类依据：[`../知识管理存储清单.md`](../知识管理存储清单.md)  
> 首个类别处理器依据：[`../project_materials/项目资料甄别规则.md`](../project_materials/项目资料甄别规则.md)

## 1. 背景

项目已经定义五类知识文件：

1. 项目资料；
2. 业务知识；
3. 架构；
4. 结果；
5. 问题。

其中，`project_materials` 已经具备相对完整的专用处理规则，包括文件登记、项目背景抽取、数据集识别、数据集画像和人工审核。后续业务知识、架构、结果和问题也会形成各自独立的处理逻辑。

当前缺少的是位于所有处理逻辑之前的统一起始入口。系统需要先接收文件、登记来源、作出可追溯的主类别判断，再将任务派发给对应处理器，而不能要求调用方预先知道应该调用哪个处理器。

## 2. 目标

初始路由系统需要实现以下目标：

- 成为整个项目唯一的文件摄取入口；
- 对所有输入先执行统一登记、去重、读取检查和安全检查；
- 将每个文件路由到一个主要类别；
- 保留可能属于其他类别的次级信号，但不复制原文件；
- 将路由后的文件交给对应类别 Handler；
- 对低置信度、冲突和不可读文件提供正式的人工复核路径；
- 保留每次判断的证据、规则版本和人工改判记录；
- 保证原始文件不可被 Agent 或 Handler 直接移动、覆盖或删除；
- 支持后续以插件式方式增加类别处理器，而不修改入口主流程。

## 3. 非目标

初始版本暂不负责：

- 一次性完成五类文件的全部深层处理能力；
- 自动批准内容进入正式知识库；
- 从一个混合文件中直接生成所有正式知识资产；
- 使用扩展名直接决定业务类别；
- 由 LLM 执行文件移动、覆盖、删除和最终写入；
- 建设面向最终用户的完整 Web 管理界面。

## 4. 核心设计原则

### 4.1 Router 是唯一入口

生产流程中，外部调用者不得绕过 Router 直接调用 `project-materials` 或其他 Handler。

所有摄取请求统一进入：

```text
ingest(request)
  -> register
  -> inspect
  -> route
  -> review if needed
  -> dispatch
  -> handler process
  -> handler review
  -> accept or reject
```

Handler 可以在单元测试或维护命令中被直接调用，但这不属于正式摄取路径。

### 4.2 路由和处理分离

Router 只负责：

- 判断主要类别；
- 给出次级信号；
- 记录判断证据和置信度；
- 决定自动派发或进入人工复核。

Handler 负责：

- 执行类别内部的抽取、分析和校验；
- 生成该类别的审核产物；
- 提交正式收录候选。

Router 不应包含数据集画像、架构决策抽取或结果验证等类别专属逻辑。

### 4.3 原始证据优先

未经提炼的项目原始材料优先路由为 `project-materials`。会议纪要、需求原文或方案原文即使包含架构、结果和问题，也首先作为项目证据保存。

此类文件可以产生 `architecture-candidate`、`result-candidate` 或 `issue-candidate` 等次级信号，由 Handler 后续生成跨类别候选资产。原文件只保留一个主要类别。

### 4.4 规则优先，模型补充，允许拒判

路由采用混合决策：

1. 可信显式声明；
2. 确定性强规则；
3. LLM 语义判断；
4. 决策策略合并。

当证据不足时，系统必须进入 `needs-review`，不能为了覆盖率强制分类。

### 4.5 决策可重放、可解释、可修订

每次路由都记录输入指纹、分类政策版本、提示词版本、模型信息、规则命中、判断理由和输出。相同输入可以按指定版本重放。

人工改判生成新的决策修订，不覆盖历史决策。

## 5. 总体架构

```text
                         +----------------------+
                         | CLI / API / Watcher  |
                         +----------+-----------+
                                    |
                                    v
+----------------+       +----------------------+       +------------------+
| Original Files | ----> | Intake Orchestrator  | ----> | File Registry    |
+----------------+       +----------+-----------+       +------------------+
                                    |
                                    v
                         +----------------------+
                         | Inspector            |
                         | metadata/text/shape  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Router               |
                         | rules + LLM + policy |
                         +----+------------+----+
                              |            |
                 high confidence            low/conflict/unsupported
                              |            |
                              v            v
                     +-----------+   +----------------+
                     | Dispatcher|   | Routing Review |
                     +-----+-----+   +-------+--------+
                           ^                 |
                           +-----------------+
                           |
                           v
              +--------------------------+
              | Handler Registry         |
              +------------+-------------+
                           |
       +-------------------+-------------------+-------------------+-------------------+
       |                   |                   |                   |                   |
       v                   v                   v                   v                   v
+--------------+  +----------------+  +---------------+  +---------------+  +---------------+
| Project      |  | Business       |  | Architecture  |  | Results       |  | Issues        |
| Materials    |  | Knowledge      |  | Handler       |  | Handler       |  | Handler       |
| Handler      |  | Handler        |  |               |  |               |  |               |
+------+-------+  +--------+-------+  +-------+-------+  +-------+-------+  +-------+-------+
       |                   |                  |                  |                  |
       +-------------------+------------------+------------------+------------------+
                                    |
                                    v
                         +----------------------+
                         | Category Review      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Accepted Knowledge   |
                         +----------------------+
```

### 5.1 控制面与处理面

系统划分为两部分：

- **控制面**：Intake、Registry、Inspector、Router、Review、Dispatcher 和状态机；
- **处理面**：五个类别 Handler 及其确定性工具、Agent 提示词和审核产物。

控制面保持稳定，处理面可以独立演进。

### 5.2 五个独立的类别处理器

五种顶层类别分别对应五个独立 Handler。它们只共享统一的 Handler 契约、基础设施和审核入口，不共享类别内部的状态模型与处理规则。

尤其是 `Results Handler` 与 `Issues Handler` 必须保持独立：

- `Results Handler` 处理已经发生并得到确认的测试、验证、交付和运行事实，重点校验对象、条件、观察结果、结论和限制；
- `Issues Handler` 处理尚未解决或仍需确认的缺失、冲突、风险和缺陷，重点维护影响、状态、责任人和所需证据；
- Result 可以被后续验证补充或取代，Issue 则沿着 `open -> investigating -> resolved` 等问题生命周期演进；
- 两者发生关联时使用关系引用，例如某个 Result 证明或关闭某个 Issue，不通过合并 Handler 表达。

## 6. 端到端处理流程

### 6.1 接收入站请求

调用方提交一个 `IngestRequest`，至少包含：

- 输入文件或目录；
- 所属项目标识；
- 来源描述；
- 提交人或调用系统；
- 可选的可信类别提示；
- 可选的敏感级别和访问范围。

目录输入会展开为多个文件项，但共享同一个 `batch_id`。

### 6.2 文件登记

Registry 使用确定性程序记录：

- 文件名、扩展名、MIME；
- 原始位置；
- 文件大小和修改时间；
- SHA-256；
- 所属项目和批次；
- 来源、提交者和登记时间；
- 重复文件关系；
- 当前处理状态。

登记完成后生成稳定 `file_id`。后续模块只通过 `file_id` 和只读文件引用访问输入。

### 6.3 轻量检查

Inspector 为路由提取最小必要信息，而不执行类别深层分析：

- 可读性、加密、损坏和格式支持情况；
- 文件名、路径、已有 frontmatter；
- 标题、目录和章节标题；
- 文本头尾及有限采样；
- 表格的工作表名、表名和表头；
- 页数、段落数、工作表数等基本结构；
- 敏感信息风险标记。

Inspector 输出只用于路由，不等于正式内容抽取结果。

### 6.4 生成候选分类

Router 依次执行：

1. `ExplicitHintClassifier`：读取受信任的类别声明；
2. `RuleClassifier`：匹配少量可解释的强规则；
3. `SemanticClassifier`：根据文件用途进行语义分类；
4. `DecisionPolicy`：合并候选、计算置信度和类别差距；
5. `RouteValidator`：校验输出结构和 Handler 可用性。

### 6.5 自动派发或人工复核

满足以下条件时可以自动派发：

- 主类别合法且对应 Handler 已启用；
- 置信度达到配置阈值；
- 第一、第二候选之间差距达到配置阈值；
- 不存在显式声明冲突；
- 文件可读且未被隔离；
- 分类输出通过 Schema 校验。

其他情况进入路由审核队列。审核人可以批准、改判、拒绝或要求补充信息。

### 6.6 Handler 处理

Dispatcher 将标准 `HandlerRequest` 发送给目标 Handler。Handler 不获得修改原文件的权限，只能向自己的工作区写入产物。

首个正式 Handler 为 `project-materials.v1`，执行现有规则定义的：

1. 文件清单整理；
2. 背景文档识别；
3. 项目背景抽取；
4. 数据集识别；
5. 数据集画像；
6. 类别内部人工审核。

## 7. 顶层分类模型

### 7.1 类别枚举

```typescript
type FileCategory =
  | "project-materials"
  | "business-knowledge"
  | "architecture"
  | "results"
  | "issues";
```

`manual-review` 不是第六种文件类别，而是路由状态。

### 7.2 分类语义

| 类别 | 文件的主要用途 | 典型内容 |
| --- | --- | --- |
| `project-materials` | 还原项目上下文或保存原始证据 | 项目说明、需求、会议纪要、方案原文、输入数据、交付材料 |
| `business-knowledge` | 解释业务是什么以及如何运行 | 概念、对象、流程、方法、指标、业务规则 |
| `architecture` | 说明系统如何设计以及为什么选择 | 系统、组件、接口、数据流、工作流、架构决策 |
| `results` | 记录已经发生并得到确认的产出 | 测试结果、验证结论、交付结果、运行指标、项目总结 |
| `issues` | 管理尚未解决或仍需确认的事项 | 缺失、冲突、风险、缺陷、待确认事项 |

### 7.3 混合文件规则

一个文件可能包含多类信息，但必须选择一个主要类别：

- 原始证据属性高于内容片段属性；
- 主要沟通目的高于关键词数量；
- “尚未解决”与“已经确认”必须区分；
- 生命周期阶段只能作为辅助信息，不能直接决定类别；
- 其他类别通过 `secondary_signals` 表达。

### 7.4 初始置信度策略

初始版本建议采用保守阈值，具体数值放在配置中：

- `auto_route_threshold`：允许自动派发的最低置信度；
- `minimum_margin`：第一、第二候选的最低差距；
- `explicit_conflict_requires_review`：显式声明冲突时强制复核；
- `unsupported_requires_review`：不支持或不可读取时强制复核。

置信度不是模型自行声称的概率。它由规则强度、证据覆盖、候选一致性和分类差距共同计算。

## 8. 核心数据契约

### 8.1 摄取请求

```typescript
interface IngestRequest {
  projectId: string;
  inputs: InputReference[];
  source: {
    kind: "user" | "system" | "import" | "watcher";
    submittedBy?: string;
    description?: string;
  };
  categoryHint?: {
    category: FileCategory;
    trusted: boolean;
    reason?: string;
  };
  sensitivity?: string;
}
```

### 8.2 文件登记

```typescript
interface FileRecord {
  fileId: string;
  batchId: string;
  projectId: string;
  originalName: string;
  originalLocation: string;
  mimeType?: string;
  extension?: string;
  size: number;
  sha256: string;
  modifiedAt?: string;
  registeredAt: string;
  duplicateOf?: string;
  status: IntakeStatus;
}
```

### 8.3 路由决定

```typescript
interface RoutingDecision {
  decisionId: string;
  revision: number;
  fileId: string;
  primaryCategory?: FileCategory;
  candidates: Array<{
    category: FileCategory;
    score: number;
  }>;
  secondarySignals: string[];
  disposition: "auto-route" | "needs-review" | "quarantine" | "reject";
  reasons: Array<{
    source: "hint" | "rule" | "semantic" | "policy" | "reviewer";
    code: string;
    evidence: string;
  }>;
  policyVersion: string;
  promptVersion?: string;
  model?: string;
  createdAt: string;
  supersedes?: string;
}
```

### 8.4 Handler 请求与结果

```typescript
interface HandlerRequest {
  jobId: string;
  file: ReadonlyFileReference;
  record: FileRecord;
  routing: RoutingDecision;
  projectContext?: ProjectContextReference;
}

interface HandlerResult {
  jobId: string;
  handler: string;
  handlerVersion: string;
  status: "completed" | "needs-review" | "failed";
  artifacts: ArtifactReference[];
  issues: ProcessingIssue[];
  secondaryCandidates: SecondaryCandidate[];
  startedAt: string;
  completedAt: string;
}
```

## 9. Handler 插件契约

每个类别 Handler 都应实现统一接口：

```typescript
interface CategoryHandler {
  readonly id: string;
  readonly version: string;
  readonly category: FileCategory;
  readonly capabilities: string[];

  supports(request: HandlerRequest): Promise<SupportResult>;
  process(request: HandlerRequest): Promise<HandlerResult>;
  validate(result: HandlerResult): Promise<ValidationResult>;
}
```

约束如下：

- Handler 不能修改 Registry 和 RoutingDecision；
- Handler 不能移动、覆盖或删除原始文件；
- Handler 只能写入分配给本次 Job 的暂存目录；
- Handler 产物必须通过自身 Schema 校验；
- Handler 发现跨类别内容时只返回候选，不直接调用其他 Handler；
- 是否派生新任务由 Orchestrator 决定，防止递归失控；
- Handler 必须幂等，同一 `jobId` 重试不能生成互相冲突的结果。

## 10. 状态机

```text
received
  -> registered
  -> inspecting
  -> routing
      -> routing-review
          -> routing
          -> rejected
      -> quarantined
      -> dispatched
          -> processing
          -> category-review
              -> accepted
              -> rejected
          -> failed
```

状态转换由 Orchestrator 控制。Handler 只能返回结果，不能自行推进全局状态。

失败分为：

- `retryable`：临时读取失败、模型服务暂时不可用；
- `non-retryable`：文件损坏、Schema 不合法；
- `review-required`：语义冲突、证据不足、格式暂不支持。

## 11. 代码目录规划

建议以 `judge_tool` 为应用根目录，形成以下结构：

```text
judge_tool/
├── README.md
├── package.json
├── tsconfig.json
├── 知识管理存储清单.md
├── specs/
│   └── 初始路由系统-spec.md
├── project_materials/
│   └── 项目资料甄别规则.md
├── config/
│   ├── categories.yaml
│   ├── routing-policy.yaml
│   ├── handlers.yaml
│   └── logging.yaml
├── schemas/
│   ├── ingest-request.schema.json
│   ├── file-record.schema.json
│   ├── inspection-result.schema.json
│   ├── routing-decision.schema.json
│   └── handler-result.schema.json
├── prompts/
│   └── router/
│       ├── system.md
│       └── classify-file.md
├── src/
│   ├── cli.ts
│   ├── api.ts
│   ├── app/
│   │   ├── create-app.ts
│   │   └── dependencies.ts
│   ├── intake/
│   │   ├── ingest.ts
│   │   ├── expand-inputs.ts
│   │   └── input-reference.ts
│   ├── registry/
│   │   ├── file-registry.ts
│   │   ├── hash-file.ts
│   │   └── duplicate-detector.ts
│   ├── inspector/
│   │   ├── inspect-file.ts
│   │   ├── metadata-inspector.ts
│   │   ├── content-sampler.ts
│   │   └── adapters/
│   │       ├── text.ts
│   │       ├── markdown.ts
│   │       ├── pdf.ts
│   │       ├── word.ts
│   │       └── spreadsheet.ts
│   ├── router/
│   │   ├── route-file.ts
│   │   ├── explicit-hint-classifier.ts
│   │   ├── rule-classifier.ts
│   │   ├── semantic-classifier.ts
│   │   ├── decision-policy.ts
│   │   ├── route-validator.ts
│   │   └── types.ts
│   ├── orchestrator/
│   │   ├── intake-orchestrator.ts
│   │   ├── state-machine.ts
│   │   ├── dispatcher.ts
│   │   ├── retry-policy.ts
│   │   └── job-store.ts
│   ├── handlers/
│   │   ├── handler.ts
│   │   ├── handler-registry.ts
│   │   ├── project-materials/
│   │   │   ├── index.ts
│   │   │   ├── background-extractor.ts
│   │   │   ├── dataset-matcher.ts
│   │   │   ├── dataset-profiler.ts
│   │   │   └── result-validator.ts
│   │   ├── business-knowledge/
│   │   │   └── index.ts
│   │   ├── architecture/
│   │   │   └── index.ts
│   │   ├── results/
│   │   │   └── index.ts
│   │   └── issues/
│   │       └── index.ts
│   ├── review/
│   │   ├── routing-review.ts
│   │   ├── category-review.ts
│   │   └── review-store.ts
│   ├── storage/
│   │   ├── artifact-store.ts
│   │   ├── local-store.ts
│   │   └── paths.ts
│   ├── observability/
│   │   ├── logger.ts
│   │   ├── audit-log.ts
│   │   └── metrics.ts
│   └── shared/
│       ├── errors.ts
│       ├── ids.ts
│       ├── clock.ts
│       └── schema-validator.ts
├── tests/
│   ├── unit/
│   │   ├── router/
│   │   ├── registry/
│   │   └── handlers/
│   ├── contract/
│   │   └── handlers/
│   ├── integration/
│   │   └── ingest-flow.test.ts
│   ├── evaluation/
│   │   ├── routing-cases.jsonl
│   │   └── routing-evaluation.test.ts
│   └── fixtures/
│       ├── project-materials/
│       ├── business-knowledge/
│       ├── architecture/
│       ├── results/
│       ├── issues/
│       └── ambiguous/
└── runtime/                    # 运行数据，不纳入源码版本控制
    ├── inbox/
    ├── registry/
    ├── routing/
    │   ├── decisions/
    │   └── review/
    ├── jobs/
    ├── handler-workspaces/
    ├── accepted/
    ├── quarantine/
    └── audit/
```

### 11.1 目录职责说明

- `config/`：环境无关的分类枚举、阈值、Handler 启停和日志策略；
- `schemas/`：模块间契约的唯一机器可校验定义；
- `prompts/`：LLM 路由提示词，必须独立版本化；
- `src/router/`：只包含分类和决策逻辑；
- `src/orchestrator/`：负责编排、状态转换、重试和派发；
- `src/handlers/`：类别专属实现；
- `src/review/`：路由审核和类别审核，不混合两种审核语义；
- `tests/evaluation/`：根据人工改判持续积累分类基准集；
- `runtime/`：运行期产物，应加入 `.gitignore`；
- 现有政策文档暂时保留原位置，代码通过配置引用，不在第一阶段搬迁。

### 11.2 技术边界

目录示例以 TypeScript 为主，原因是当前 `judge_tool` 已包含 TypeScript 生态的 Pi Agent 代码，Router 和 Orchestrator 可以共享类型及运行工具。PDF、Word、Excel 等确定性解析可以通过适配器调用独立程序，不能让格式工具侵入 Router。

## 12. 配置规划

`categories.yaml` 定义稳定类别 ID、展示名称和 Handler ID：

```yaml
categories:
  - id: project-materials
    label: 项目资料
    handler: project-materials.v1
  - id: business-knowledge
    label: 业务知识
    handler: business-knowledge.v1
  - id: architecture
    label: 架构
    handler: architecture.v1
  - id: results
    label: 结果
    handler: results.v1
  - id: issues
    label: 问题
    handler: issues.v1
```

`routing-policy.yaml` 定义阈值和政策版本，不将阈值散落在代码中：

```yaml
version: routing-policy.v1
auto_route_threshold: 0.85
minimum_margin: 0.20
explicit_conflict_requires_review: true
unsupported_requires_review: true
raw_project_evidence_bias: project-materials
```

这些数值是初始建议，正式值应通过评测集校准。

## 13. 存储与审计

第一阶段可以使用本地文件存储，但接口需要为未来数据库实现保留替换空间。

必须持久化：

- FileRecord；
- InspectionResult；
- RoutingDecision 的全部修订；
- ReviewRecord；
- Job 状态和 HandlerResult；
- 写入正式区的操作记录；
- 错误、重试和人工改判记录。

审计日志采用追加写入，不通过更新删除历史事件。

任何正式产物都必须能够追溯到：

```text
accepted artifact
  -> handler result
  -> routing decision
  -> file record
  -> original source
```

## 14. 安全与权限

- 原始输入以只读方式提供给 Inspector 和 Handler；
- 路径必须规范化并限制在获准的输入根目录内；
- 压缩包解压需要防止路径穿越和解压炸弹；
- MIME 和扩展名不一致时记录风险；
- 不可信文档中的提示性文本不能覆盖系统分类政策；
- 敏感文件的采样内容不得直接写入普通日志；
- 只有确定性存储模块可以把审核通过的产物写入正式区；
- 所有移动、覆盖和删除操作必须由受控命令执行并写入审计日志。

## 15. 可观测性与评估指标

### 15.1 运行指标

- 每批文件数和总大小；
- 登记、检查、路由、Handler 各阶段耗时；
- 自动路由率；
- 人工复核率；
- Handler 成功、失败和重试次数；
- 重复文件和不可读文件数量。

### 15.2 质量指标

- 自动路由准确率；
- 高置信度错误路由率；
- 人工改判率；
- 应复核却被自动派发的比例；
- 同一输入在同一政策版本下的稳定性；
- 正式产物的来源可追溯率；
- Handler 契约校验通过率。

高置信度错误路由率应作为第一优先级风险指标。

## 16. 测试策略

### 16.1 单元测试

- 文件 ID 和哈希稳定性；
- 重复文件检测；
- 强规则命中和冲突；
- DecisionPolicy 阈值边界；
- 状态机合法和非法转换；
- Schema 校验；
- Handler 注册和派发。

### 16.2 契约测试

所有 Handler 使用同一组契约测试，验证：

- 不修改原文件；
- 输出符合 HandlerResult Schema；
- 相同 Job 重试保持幂等；
- 跨类别内容只生成候选；
- 失败时返回标准错误类型。

### 16.3 集成测试

至少覆盖：

- 高置信度项目资料自动进入 `project-materials`；
- 架构文档路由到 Architecture Handler；
- 混合会议纪要以项目资料为主并生成问题候选；
- 结果与问题语义冲突进入人工复核；
- 不支持格式进入复核或隔离；
- 人工改判后重新派发；
- 重复提交不会重复产生正式产物。

### 16.4 路由评测集

`tests/evaluation/routing-cases.jsonl` 保存经人工确认的样例，至少包含：

- 输入摘要；
- 正确主类别；
- 可接受的次级信号；
- 是否必须人工复核；
- 判定说明。

每次修改规则、提示词或模型后运行回归评测。

## 17. 分阶段实现计划

### 阶段 1：可运行入口

- 建立 Schema、Registry 和稳定 FileRecord；
- 实现单文件和目录摄取命令；
- 实现 Inspector 最小能力；
- 建立状态机和本地 JobStore。

验收标准：任何支持文件都能从唯一入口完成登记，并获得可追溯状态。

### 阶段 2：初始路由

- 实现五类枚举；
- 实现显式声明、强规则和语义分类；
- 实现 DecisionPolicy 和路由审核队列；
- 建立初始评测集。

验收标准：高置信度文件可自动派发，模糊文件稳定进入复核，无强制猜测。

### 阶段 3：接通项目资料 Handler

- 将现有项目资料规则实现为 `project-materials.v1`；
- 生成文件登记、项目背景、数据集匹配、画像和问题产物；
- 实现类别内部审核。

验收标准：项目资料能从统一入口走完整链路，不需要调用方手动选择处理脚本。

### 阶段 4：建立其他 Handler 骨架

- 注册业务知识、架构、结果和问题 Handler；
- 初期只生成标准摘要和审核候选；
- 逐类补充专属规则和工具。

验收标准：顶层 Router 无需修改即可启用或升级 Handler。

### 阶段 5：治理和优化

- 基于人工改判校准阈值；
- 增加审计查询和指标报表；
- 完善权限、敏感信息和批量重处理；
- 支持政策版本迁移和历史重放。

## 18. 架构决策摘要

| 决策 | 选择 | 原因 |
| --- | --- | --- |
| 系统入口 | Router 前置的统一 Intake | 调用方不需要预判类别，所有文件执行一致治理 |
| 文件分类 | 一个主类别加多个次级信号 | 避免重复存放，同时保留混合内容信息 |
| 分类实现 | 规则与 LLM 混合 | 兼顾确定性、可解释性和语义判断能力 |
| 模糊输入 | 正式拒判并人工复核 | 降低高置信度错误分类风险 |
| 原始文件 | 不可变、只读引用 | 保证证据完整和可追溯 |
| Handler 关系 | 插件式统一契约 | 各类别可独立演进，控制面保持稳定 |
| 跨类别发现 | 返回候选给 Orchestrator | 避免 Handler 相互调用和递归失控 |
| 历史记录 | 追加修订，不覆盖 | 支持审计、评估和决策重放 |

## 19. 第一版完成定义

满足以下条件时，可以认为初始路由系统第一版完成：

1. 存在一个可调用的统一 `ingest` 入口；
2. 所有文件在分类前完成登记和只读引用；
3. Router 能输出符合 Schema 的五类候选和判断依据；
4. 低置信度、冲突和不可读文件不会被强制派发；
5. `project-materials.v1` 已通过统一 Handler 契约接入；
6. 路由决定、人工改判和 Handler 结果均可追溯；
7. 原始文件不会被 Agent 或 Handler 修改；
8. 至少有一组覆盖五类及模糊样例的回归评测；
9. 新增类别 Handler 时无需修改 Intake 主流程；
10. 从正式产物能够回溯到原始文件和具体路由决定。
