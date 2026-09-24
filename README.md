# File Router（Context Router）

File Router 是统一文件摄取与知识路由系统。它接收尚未分类的项目文件，先完成登记、检查和可追溯的类别判断，再把文件派发给对应的专用 Handler；当证据不足、规则冲突或格式不受支持时，系统进入人工复核，而不是强制猜测。

项目希望解决的核心问题是：调用方不应在提交文件前就知道该使用哪套处理逻辑。所有输入都应从同一个入口进入，并在不修改原始证据的前提下，得到可解释、可审核、可重放的处理结果。

> 当前状态：规划与交互原型阶段。路由系统 Spec、项目资料甄别规则和前端原型已经存在；真实的 Intake、Router、Handler、持久化与 API 尚未实现。前端目前使用本地模拟数据，不会读取或上传所选文件的内容。

## 核心目标

- 提供唯一的 `ingest` 文件摄取入口；
- 在分类前统一完成文件登记、哈希、去重、可读性与安全检查；
- 为每个文件确定一个主要类别，同时保留跨类别的次级信号；
- 结合可信提示、确定性规则和 LLM 语义判断完成路由；
- 将低置信度、冲突和不可读输入交给人工复核；
- 记录判断依据、策略版本、模型信息与人工改判历史；
- 通过统一契约将任务派发给可独立演进的类别 Handler；
- 保持原始文件只读，并让正式产物能够回溯到原始来源和路由决定。

## 文件分类

系统将每个文件路由到一个主要类别。文件中出现其他类别的内容时，只记录次级信号，不复制原文件。

| 类别 ID                | 展示名称 | 内容边界                                           | 计划中的处理重点               |
| ---------------------- | -------- | -------------------------------------------------- | ------------------------------ |
| `project-materials`  | 项目资料 | 项目说明、需求、会议纪要、方案原文、数据与交付材料 | 项目背景抽取、数据集识别与画像 |
| `business-knowledge` | 业务知识 | 业务概念、对象、流程、方法、指标与规则             | 业务知识提炼与来源校验         |
| `architecture`       | 架构     | 系统、组件、流程、数据流、接口与设计决策           | 架构关系、选择理由与约束抽取   |
| `results`            | 结果     | 测试、验证、交付、运行指标与项目总结               | 条件、观察、结论与限制整理     |
| `issues`             | 问题     | 缺失、冲突、风险、缺陷与待确认事项                 | 影响、状态与补证路径管理       |

原始项目证据优先归为 `project-materials`。例如，包含架构讨论和问题记录的会议纪要仍以项目资料保存，同时产生 `architecture-candidate` 和 `issue-candidate` 等次级信号。

## 总体流程

```text
CLI / API / Watcher
        |
        v
Intake Orchestrator
        |
        +--> File Registry（登记、哈希、去重）
        |
        v
Inspector（元数据、文本与结构采样）
        |
        v
Router（显式提示 + 规则 + LLM + 决策策略）
        |
        +--> 低置信度 / 冲突 / 不支持 --> Routing Review
        |                                      |
        +----------------< 人工改判 <----------+
        |
        v
Dispatcher --> Handler Registry
        |
        +--> Project Materials Handler
        +--> Business Knowledge Handler
        +--> Architecture Handler
        +--> Results Handler
        +--> Issues Handler
        |
        v
Category Review --> Accepted Knowledge
```

架构分为两个相互解耦的部分：

- **控制面**：Intake、Registry、Inspector、Router、Review、Dispatcher 和状态机；
- **处理面**：五个类别 Handler，以及各自使用的确定性工具、Agent 提示词和审核产物。

Router 只决定“去哪里”和“是否需要复核”，不执行数据集画像、架构抽取或结果验证。Handler 只处理自己的类别，也不能直接修改路由记录或原始文件。

## 路由策略

路由按以下优先级组合证据：

1. 可信的调用方类别提示；
2. 文件内容与元数据上的确定性强规则；
3. LLM 对内容语义的补充判断；
4. 决策策略对置信度、候选差距、冲突与格式支持情况的统一裁决。

置信度不是模型自行声明的概率，而应由规则强度、证据覆盖、候选一致性和候选差距共同计算。首版策略计划通过配置管理以下参数：

```yaml
version: routing-policy.v1
auto_route_threshold: 0.85
minimum_margin: 0.20
explicit_conflict_requires_review: true
unsupported_requires_review: true
raw_project_evidence_bias: project-materials
```

这些值是待评测集校准的初始建议，并非已经上线的运行配置。

## Handler 契约

每个类别 Handler 计划实现统一接口：

```ts
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

共同约束包括：

- 输入文件只读；
- 输出只能写入当前 Job 的暂存空间；
- 处理结果必须通过 Schema 校验；
- 同一 `jobId` 重试应保持幂等；
- 跨类别发现只作为候选返回给 Orchestrator；
- 正式收录必须经过类别审核和受控存储模块。

首个重点 Handler 是 `project-materials.v1`。其规划流程为：文件登记 → 背景文档识别 → 项目背景抽取 → 数据集匹配 → 数据集画像 → 人工审核。数据集按项目用途和实际内容判断，不能仅凭扩展名分类。

## 当前仓库结构

```text
judge_tool/
├── README.md                         # 项目总览（本文件）
├── 知识管理存储清单.md               # 五类文件的定义与审核边界
├── specs/
│   └── 初始路由系统-spec.md          # File Router 的完整设计规格
├── project_materials/
│   └── 项目资料甄别规则.md           # 首个 Handler 的业务规则
├── frontend/                         # React + TypeScript 交互原型
│   ├── src/
│   ├── docs/视觉设计规范.md
│   └── README.md
├── pi-mono/                          # Pi Agent Harness 源码与运行时依赖
├── .pi-agent/                        # 本地 Pi Agent 工作目录
└── pi-mono.cmd                       # Windows 离线启动脚本（本机路径配置）
```

`pi-mono/` 是独立的 Agent Harness 代码库，不是 File Router 的业务实现。后续 Router 与 Handler 可以复用其中的 Agent 运行能力，但两者应保持清晰边界。

## 已完成与待实现

| 范围                          | 状态       | 说明                                         |
| ----------------------------- | ---------- | -------------------------------------------- |
| 五类知识文件定义              | 已完成     | 已定义类别边界、生命周期和通用审核要求       |
| File Router 架构规格          | 已完成草案 | Spec 版本`0.1`，状态为 Draft               |
| 项目资料甄别规则              | 已完成草案 | 覆盖项目背景抽取、数据集识别、画像和审核     |
| 管理端视觉规范                | 已完成     | Monochrome Signal 设计规范                   |
| 前端交互原型                  | 已完成     | 总览、摄取、路由审核、Handler 状态和文件详情 |
| 真实文件读取与上传            | 未实现     | 前端选择文件后仅生成模拟记录                 |
| Intake / Registry / Inspector | 未实现     | 尚无后端或 CLI 入口                          |
| Router 与决策策略             | 未实现     | 尚无规则引擎、LLM 分类和评测集               |
| Handler 运行时                | 未实现     | 五类 Handler 尚未按统一契约接入              |
| 审核、存储与审计              | 未实现     | 尚无持久化状态机和正式收录链路               |

## 运行前端原型

前置条件：Node.js、pnpm。

```bash
cd frontend
pnpm install
pnpm run dev
```

开发服务器默认由 Vite 提供，通常可通过 `http://127.0.0.1:5173/` 访问。

执行类型检查和生产构建：

```bash
pnpm run typecheck
pnpm run build
```

当前原型的文件选择操作只模拟“登记 → 路由 → 人工复核”，不会读取、分析或上传文件内容。

## 规划中的代码结构

后端实现计划以 TypeScript 为主，并按职责拆分：

```text
config/          # 类别、路由政策、Handler 和日志配置
schemas/         # 模块间唯一的机器可校验契约
prompts/router/  # 独立版本化的语义路由提示词
src/intake/      # 统一摄取入口
src/registry/    # 文件登记、哈希与去重
src/inspector/   # 元数据检查、内容采样和格式适配器
src/router/      # 分类器、决策策略和输出校验
src/orchestrator/# 状态机、派发、重试和 Job 存储
src/handlers/    # 五类可插拔 Handler
src/review/      # 路由审核与类别审核
src/storage/     # 暂存区、正式区与路径控制
src/observability/# 日志、审计与指标
tests/           # 单元、契约、集成与路由评测
runtime/         # 本地运行数据，不纳入源码版本控制
```

模块之间以 `FileRecord`、`RoutingDecision`、`HandlerRequest` 和 `HandlerResult` 等 Schema 交互，避免把文件系统细节或某个 Handler 的业务逻辑泄漏到 Router。

## 实施路线

### 阶段 1：建立可运行入口

- 定义并校验核心 Schema；
- 实现单文件和目录摄取；
- 建立 File Registry、最小 Inspector、状态机与本地 JobStore。

完成标志：支持文件能够从唯一入口完成登记，并获得可追溯状态。

### 阶段 2：实现初始路由

- 实现五类枚举、可信提示和强规则；
- 接入 LLM 语义分类与 Decision Policy；
- 建立路由复核队列和覆盖五类、冲突及模糊输入的评测集。

完成标志：高置信度文件可以自动派发，证据不足的文件稳定进入复核。

### 阶段 3：接入项目资料 Handler

- 将现有甄别规则实现为 `project-materials.v1`；
- 产出文件登记、项目背景、数据集匹配、画像和问题记录；
- 接通类别审核及正式收录候选流程。

完成标志：项目资料可以从统一入口走完整链路，无需调用方手动选择脚本。

### 阶段 4：扩展其他 Handler

- 注册业务知识、架构、结果和问题 Handler；
- 初期输出标准摘要与审核候选，再逐类增加专属能力。

完成标志：新增或升级 Handler 不需要修改 Intake 主流程。

### 阶段 5：治理与优化

- 用人工改判数据校准路由阈值；
- 完善审计查询、指标、权限和敏感信息处理；
- 支持政策版本迁移、历史重放和批量重处理。

## 质量与安全原则

- 原始文件使用只读引用，不由 Agent 或 Handler 移动、覆盖或删除；
- 路径必须规范化并限制在授权输入目录内；
- 压缩包处理需防止路径穿越和解压炸弹；
- MIME 与扩展名不一致时记录风险，不能直接信任文件名；
- 文档内容属于不可信输入，其中的指令不能覆盖系统策略；
- 敏感采样内容不得直接写入普通日志；
- 人工改判生成新修订，不覆盖历史决定；
- 审计记录采用追加写入，正式产物必须能回溯到原始文件。

首要质量指标是**高置信度错误路由率**，其次包括自动路由准确率、人工改判率、复核召回率、Handler 契约通过率和正式产物来源可追溯率。

## 关键文档

- [初始路由系统 Spec](specs/初始路由系统-spec.md)：架构、契约、状态机、存储、测试和完成定义；
- [知识管理存储清单](知识管理存储清单.md)：五类文件及其生命周期和审核要求；
- [项目资料甄别规则](project_materials/项目资料甄别规则.md)：首个 Handler 的处理边界；
- [前端说明](frontend/README.md)：原型功能、运行命令与后端接口建议；
- [视觉设计规范](frontend/docs/视觉设计规范.md)：管理端界面的视觉与组件规则。

## License

本项目采用 [MIT License](LICENSE)。
