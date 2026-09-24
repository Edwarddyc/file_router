import type { HandlerStatus, RoutingFile } from "../types";

export const initialFiles: RoutingFile[] = [
  {
    id: "file_01J8R4AK",
    name: "HLX1102 项目启动会议纪要.docx",
    project: "HLX1102 PDU POC",
    size: "2.4 MB",
    extension: "DOCX",
    submittedAt: "09:42",
    category: "project-materials",
    secondarySignals: ["issue-candidate", "architecture-candidate"],
    confidence: 0.94,
    disposition: "auto-route",
    state: "processing",
    reasons: [
      { source: "semantic", code: "raw-project-evidence", evidence: "正文主要记录项目背景、参与方、需求和待办事项。" },
      { source: "policy", code: "original-evidence-priority", evidence: "未经提炼的会议纪要优先归入项目资料。" }
    ],
    sha256: "8f07b54d…e61a",
    source: "用户上传 / 项目启动资料"
  },
  {
    id: "file_01J8R39F",
    name: "报告生成程序架构设计.md",
    project: "HLX1102 PDU POC",
    size: "46 KB",
    extension: "MD",
    submittedAt: "09:31",
    category: "architecture",
    secondarySignals: ["decision-candidate"],
    confidence: 0.91,
    disposition: "auto-route",
    state: "accepted",
    reasons: [
      { source: "rule", code: "architecture-heading", evidence: "存在“组件职责”“数据流”“关键决策”等强架构章节。" },
      { source: "semantic", code: "system-design-purpose", evidence: "文件主要说明系统如何设计以及选择理由。" }
    ],
    sha256: "23b9a140…b5d2",
    source: "Git 导入 / docs"
  },
  {
    id: "file_01J8R1S7",
    name: "ELN 批次映射验证结果.xlsx",
    project: "HLX1102 PDU POC",
    size: "814 KB",
    extension: "XLSX",
    submittedAt: "09:18",
    category: "results",
    secondarySignals: ["issue-candidate"],
    confidence: 0.72,
    disposition: "needs-review",
    state: "review",
    reasons: [
      { source: "semantic", code: "observed-validation", evidence: "工作表包含实验组合、实际匹配结果和验证结论。" },
      { source: "policy", code: "result-issue-ambiguity", evidence: "文件同时包含未匹配批次，需要确认主要用途是结果记录还是问题登记。" }
    ],
    sha256: "caf71109…293e",
    source: "用户上传 / 验证资料"
  },
  {
    id: "file_01J8QZP2",
    name: "Non-GMP 数据缺口清单.md",
    project: "HLX1102 PDU POC",
    size: "18 KB",
    extension: "MD",
    submittedAt: "昨天",
    category: "issues",
    secondarySignals: ["dataset-missing"],
    confidence: 0.88,
    disposition: "needs-review",
    state: "review",
    reasons: [
      { source: "rule", code: "issue-register-structure", evidence: "条目包含缺失内容、影响、状态和所需证据。" }
    ],
    sha256: "3e5f7012…722a",
    source: "Git 导入 / project"
  },
  {
    id: "file_01J8QYA4",
    name: "细胞培养工艺参数说明.pdf",
    project: "PDU 团队知识库",
    size: "6.7 MB",
    extension: "PDF",
    submittedAt: "昨天",
    category: "business-knowledge",
    secondarySignals: ["domain-method-candidate"],
    confidence: 0.86,
    disposition: "auto-route",
    state: "processing",
    reasons: [
      { source: "semantic", code: "domain-explanation", evidence: "文件主要解释培养过程、参数含义和业务规则。" }
    ],
    sha256: "9a210c41…ab08",
    source: "共享目录导入"
  },
  {
    id: "file_01J8QW13",
    name: "附件_扫描件_03.pdf",
    project: "待识别项目",
    size: "12.1 MB",
    extension: "PDF",
    submittedAt: "昨天",
    secondarySignals: [],
    confidence: 0.31,
    disposition: "needs-review",
    state: "review",
    reasons: [
      { source: "policy", code: "insufficient-readable-content", evidence: "仅识别到扫描图片，缺少足够文本和来源上下文。" }
    ],
    sha256: "790a3f1b…911f",
    source: "批量导入 / 未分类"
  }
];

export const handlerStatuses: HandlerStatus[] = [
  {
    id: "project-materials.v1",
    category: "project-materials",
    label: "项目资料",
    version: "v1.0.0",
    status: "healthy",
    processed: 128,
    pending: 4,
    successRate: 98.4,
    description: "项目背景抽取、数据集匹配与基础画像"
  },
  {
    id: "business-knowledge.v1",
    category: "business-knowledge",
    label: "业务知识",
    version: "v0.3.0",
    status: "draft",
    processed: 36,
    pending: 2,
    successRate: 92.1,
    description: "业务概念、对象、流程、方法与规则提炼"
  },
  {
    id: "architecture.v1",
    category: "architecture",
    label: "架构",
    version: "v0.4.1",
    status: "healthy",
    processed: 49,
    pending: 1,
    successRate: 96.0,
    description: "系统设计、组件、接口、数据流与决策抽取"
  },
  {
    id: "results.v1",
    category: "results",
    label: "结果",
    version: "v0.2.0",
    status: "draft",
    processed: 21,
    pending: 3,
    successRate: 90.5,
    description: "测试、验证、交付和运行事实归档"
  },
  {
    id: "issues.v1",
    category: "issues",
    label: "问题",
    version: "v0.2.0",
    status: "attention",
    processed: 42,
    pending: 6,
    successRate: 88.7,
    description: "缺失、冲突、风险、缺陷和待确认事项管理"
  }
];
