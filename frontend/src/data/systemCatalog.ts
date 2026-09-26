import type { HandlerStatus } from "../types";

export const handlerStatuses: HandlerStatus[] = [
  {
    id: "project-materials.v1",
    category: "project-materials",
    label: "项目资料",
    version: "未发布",
    implementationStatus: "specified",
    description: "项目背景抽取、数据集匹配与基础画像",
    dependency: "Inspector、Dispatcher、Agent Runtime",
    nextStep: "依据现有甄别规则实现首个 Handler 契约"
  },
  {
    id: "business-knowledge.v1",
    category: "business-knowledge",
    label: "业务知识",
    version: "未发布",
    implementationStatus: "planned",
    description: "业务概念、对象、流程、方法与规则提炼",
    dependency: "Router、Dispatcher",
    nextStep: "定义业务知识处理与审核规则"
  },
  {
    id: "architecture.v1",
    category: "architecture",
    label: "架构",
    version: "未发布",
    implementationStatus: "planned",
    description: "系统设计、组件、接口、数据流与决策抽取",
    dependency: "Router、Dispatcher",
    nextStep: "定义架构对象和决策抽取契约"
  },
  {
    id: "results.v1",
    category: "results",
    label: "结果",
    version: "未发布",
    implementationStatus: "planned",
    description: "测试、验证、交付和运行事实归档",
    dependency: "Router、Dispatcher",
    nextStep: "定义结果条件、观察、结论和限制模型"
  },
  {
    id: "issues.v1",
    category: "issues",
    label: "问题",
    version: "未发布",
    implementationStatus: "planned",
    description: "缺失、冲突、风险、缺陷和待确认事项管理",
    dependency: "Router、Dispatcher",
    nextStep: "定义问题状态、影响和补证路径模型"
  }
];
