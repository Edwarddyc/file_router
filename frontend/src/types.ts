export type FileCategory =
  | "project-materials"
  | "business-knowledge"
  | "architecture"
  | "results"
  | "issues";

export type RouteDisposition = "auto-route" | "needs-review" | "quarantine" | "reject";
export type JobState = "routing" | "review" | "processing" | "accepted" | "failed";

export interface RouteReason {
  source: "hint" | "rule" | "semantic" | "policy" | "reviewer";
  code: string;
  evidence: string;
}

export interface RoutingFile {
  id: string;
  name: string;
  project: string;
  size: string;
  extension: string;
  submittedAt: string;
  category?: FileCategory;
  secondarySignals: string[];
  confidence: number;
  disposition: RouteDisposition;
  state: JobState;
  reasons: RouteReason[];
  sha256: string;
  source: string;
}

export interface HandlerStatus {
  id: string;
  category: FileCategory;
  label: string;
  version: string;
  status: "healthy" | "draft" | "attention";
  processed: number;
  pending: number;
  successRate: number;
  description: string;
}

export type ViewId = "overview" | "intake" | "review" | "handlers";

export const categoryMeta: Record<FileCategory, { label: string; short: string }> = {
  "project-materials": { label: "项目资料", short: "项目" },
  "business-knowledge": { label: "业务知识", short: "业务" },
  architecture: { label: "架构", short: "架构" },
  results: { label: "结果", short: "结果" },
  issues: { label: "问题", short: "问题" }
};
