import { categoryMeta, type FileCategory, type JobState } from "../types";

export function CategoryBadge({ category }: { category?: FileCategory }) {
  if (!category) return <span className="badge neutral">待判断</span>;
  return <span className={`badge category ${category}`}>{categoryMeta[category].label}</span>;
}

const stateLabels: Record<JobState, string> = {
  routing: "路由中",
  review: "待审核",
  processing: "处理中",
  accepted: "已收录",
  failed: "失败"
};

export function StateBadge({ state }: { state: JobState }) {
  return <span className={`state-badge ${state}`}><i />{stateLabels[state]}</span>;
}
