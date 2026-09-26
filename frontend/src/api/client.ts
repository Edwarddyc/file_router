export interface FileRecordDto {
  file_id: string;
  batch_id: string;
  project_id: string;
  original_name: string;
  display_name: string;
  client_media_type: string | null;
  detected_media_type: string | null;
  extension: string | null;
  size_bytes: number | null;
  sha256: string | null;
  duplicate_of_file_id: string | null;
  is_content_duplicate: boolean;
  status: "registered" | "failed";
  failure_code: string | null;
  failure_message: string | null;
  registered_at: string | null;
  created_at: string;
}

export interface FileListDto {
  items: FileRecordDto[];
  next_cursor?: string;
}

export interface IngestBatchDto {
  batch_id: string;
  project_id: string;
  status: "completed" | "partial" | "failed";
  total_count: number;
  registered_count: number;
  failed_count: number;
  files: FileRecordDto[];
  duplicates: FileRecordDto[];
}

export interface ProblemDto {
  code: string;
  detail: string;
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) return response.json() as Promise<T>;
  const problem = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as Partial<ProblemDto>;
  throw new Error(problem.detail ?? `HTTP ${response.status}`);
}

export async function listRegisteredFiles(): Promise<FileListDto> {
  return parseResponse<FileListDto>(await fetch(`${apiBase}/files?limit=200`));
}

export async function uploadFiles(projectId: string, files: File[]): Promise<IngestBatchDto> {
  const body = new FormData();
  body.append("project_id", projectId);
  body.append("source_kind", "user-upload");
  body.append("source_description", "Context Router 前端上传");
  files.forEach((file) => body.append("files", file));
  return parseResponse<IngestBatchDto>(await fetch(`${apiBase}/intake/batches`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body
  }));
}
