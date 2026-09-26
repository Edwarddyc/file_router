import { useEffect, useMemo, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Icon } from "./components/Icon";
import { CategoryBadge, StateBadge } from "./components/StatusBadge";
import { handlerStatuses } from "./data/systemCatalog";
import { listRegisteredFiles, uploadFiles, type FileRecordDto } from "./api/client";
import {
  categoryMeta,
  type FileCategory,
  type RoutingFile,
  type ViewId
} from "./types";

const navItems: Array<{ id: ViewId; label: string; icon: "grid" | "upload" | "review" | "layers" }> = [
  { id: "overview", label: "总览", icon: "grid" },
  { id: "intake", label: "文件摄取", icon: "upload" },
  { id: "review", label: "路由审核", icon: "review" },
  { id: "handlers", label: "处理器", icon: "layers" }
];

const viewTitles: Record<ViewId, { title: string; subtitle: string }> = {
  overview: { title: "路由总览", subtitle: "追踪文件从接入、分类到处理的完整状态" },
  intake: { title: "文件摄取", subtitle: "所有文件从这里进入统一登记与路由流程" },
  review: { title: "路由审核", subtitle: "处理证据不足、分类冲突或需要人工确认的文件" },
  handlers: { title: "类别处理器", subtitle: "五类 Handler 独立运行，共享统一契约与审核入口" }
};

type FontScale = "compact" | "standard" | "large";
type ThemeMode = "light" | "dark";

const fontScaleOptions: Array<{ value: FontScale; label: string }> = [
  { value: "compact", label: "紧凑" },
  { value: "standard", label: "标准" },
  { value: "large", label: "大号" }
];

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function toViewFile(file: FileRecordDto): RoutingFile {
  return {
    id: file.file_id,
    batchId: file.batch_id,
    name: file.display_name,
    project: file.project_id,
    size: file.size_bytes == null ? "—" : formatFileSize(file.size_bytes),
    extension: file.extension?.toUpperCase() || "FILE",
    submittedAt: new Date(file.registered_at ?? file.created_at).toLocaleString(),
    secondarySignals: [],
    confidence: 0,
    state: file.status,
    reasons: [],
    sha256: file.sha256 ?? "—",
    source: file.is_content_duplicate ? "重复上传" : "用户上传",
    duplicateOfFileId: file.duplicate_of_file_id ?? undefined,
    isContentDuplicate: file.is_content_duplicate,
    failureMessage: file.failure_message ?? undefined
  };
}

function App() {
  const [view, setView] = useState<ViewId>("overview");
  const [files, setFiles] = useState<RoutingFile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [projectId, setProjectId] = useState("default-project");
  const [fontScale, setFontScale] = useState<FontScale>(() => {
    const saved = window.localStorage.getItem("context-router-font-scale");
    return saved === "compact" || saved === "large" ? saved : "standard";
  });
  const [theme, setTheme] = useState<ThemeMode>(() =>
    window.localStorage.getItem("context-router-theme") === "dark" ? "dark" : "light"
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selected = files.find((file) => file.id === selectedId) ?? null;
  const reviewCount = files.filter((file) => file.state === "review").length;

  const refreshFiles = async () => {
    const result = await listRegisteredFiles();
    setFiles(result.items.map(toViewFile));
  };

  useEffect(() => {
    void refreshFiles().catch(() => setFiles([]));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.fontScale = fontScale;
    window.localStorage.setItem("context-router-font-scale", fontScale);
  }, [fontScale]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("context-router-theme", theme);
  }, [theme]);

  const addFiles = async (incoming: File[]) => {
    if (!incoming.length) return;
    const created: RoutingFile[] = incoming.map((file, index) => ({
      id: `file_local_${Date.now()}_${index}`,
      name: file.name,
      project: projectId,
      size: formatFileSize(file.size),
      extension: file.name.split(".").pop()?.toUpperCase() || "FILE",
      submittedAt: "刚刚",
      secondarySignals: [],
      confidence: 0,
      state: "uploading",
      reasons: [],
      sha256: "计算中…",
      source: "本地上传"
    }));

    setFiles((current) => [...created, ...current]);
    setView("intake");

    try {
      const batch = await uploadFiles(projectId, incoming);
      const persisted = await listRegisteredFiles();
      setFiles([
        ...batch.duplicates.map(toViewFile),
        ...persisted.items.map(toViewFile)
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "上传失败";
      setFiles((current) => current.map((file) => created.some((item) => item.id === file.id)
        ? { ...file, state: "failed", failureMessage: message, sha256: "—" }
        : file));
    }
  };

  const resetDuplicates = () => {
    setFiles((current) => current.filter((file) => !file.isContentDuplicate));
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    void addFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  };

  const navigate = (id: ViewId) => {
    setView(id);
    setSidebarOpen(false);
  };

  return (
    <div className="app-shell">
      <Sidebar
        view={view}
        reviewCount={reviewCount}
        open={sidebarOpen}
        onNavigate={navigate}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main-shell">
        <Header
          view={view}
          fontScale={fontScale}
          onFontScale={setFontScale}
          theme={theme}
          onTheme={() => setTheme((current) => current === "light" ? "dark" : "light")}
          onMenu={() => setSidebarOpen(true)}
          onUpload={() => fileInputRef.current?.click()}
        />

        <input ref={fileInputRef} className="visually-hidden" type="file" multiple onChange={handleFileInput} />

        <div className="page-content">
          {view === "overview" && (
            <Overview files={files} onOpenFile={setSelectedId} onNavigate={navigate} />
          )}
          {view === "intake" && (
            <Intake
              files={files}
              projectId={projectId}
              onProjectId={setProjectId}
              onFiles={(items) => void addFiles(items)}
              onBrowse={() => fileInputRef.current?.click()}
              onOpenFile={setSelectedId}
              onResetDuplicates={() => void resetDuplicates()}
            />
          )}
          {view === "review" && (
            <ReviewQueue files={files} onOpenFile={setSelectedId} />
          )}
          {view === "handlers" && <Handlers />}
        </div>
      </main>

      {selected && (
        <FileDrawer
          file={selected}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}

function Sidebar({
  view,
  reviewCount,
  open,
  onNavigate,
  onClose
}: {
  view: ViewId;
  reviewCount: number;
  open: boolean;
  onNavigate: (id: ViewId) => void;
  onClose: () => void;
}) {
  return (
    <>
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><span /><span /><span /></div>
          <div><strong>Context Router</strong><small>Knowledge Intake</small></div>
          <button className="icon-button sidebar-close" onClick={onClose} aria-label="关闭导航"><Icon name="close" /></button>
        </div>

        <nav className="nav-list" aria-label="主导航">
          <p className="nav-label">工作台</p>
          {navItems.map((item) => (
            <button key={item.id} className={`nav-item ${view === item.id ? "active" : ""}`} onClick={() => onNavigate(item.id)}>
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.id === "review" && reviewCount > 0 && <b>{reviewCount}</b>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="policy-card">
            <div className="policy-icon"><Icon name="shield" size={17} /></div>
            <div><strong>策略版本</strong><span>routing-policy.v1</span></div>
          </div>
          <div className="user-card">
            <div className="avatar">LX</div>
            <div><strong>路由管理员</strong><span>本地工作区</span></div>
            <Icon name="chevron" size={16} />
          </div>
        </div>
      </aside>
      {open && <button className="sidebar-overlay" onClick={onClose} aria-label="关闭导航遮罩" />}
    </>
  );
}

function Header({ view, fontScale, onFontScale, theme, onTheme, onMenu, onUpload }: { view: ViewId; fontScale: FontScale; onFontScale: (value: FontScale) => void; theme: ThemeMode; onTheme: () => void; onMenu: () => void; onUpload: () => void }) {
  const meta = viewTitles[view];
  return (
    <header className="topbar">
      <div className="topbar-title">
        <button className="icon-button menu-button" onClick={onMenu} aria-label="打开导航"><Icon name="menu" /></button>
        <div><h1>{meta.title}</h1><p>{meta.subtitle}</p></div>
      </div>
      <div className="topbar-actions">
        <button className="theme-toggle" onClick={onTheme} aria-label={theme === "light" ? "切换到夜间模式" : "切换到日间模式"} title={theme === "light" ? "夜间模式" : "日间模式"}>
          <Icon name={theme === "light" ? "moon" : "sun"} size={17} />
        </button>
        <label className="font-scale-control">
          <span aria-hidden="true">Aa</span>
          <select aria-label="调整界面字号" value={fontScale} onChange={(event) => onFontScale(event.target.value as FontScale)}>
            {fontScaleOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <button className="primary-button" onClick={onUpload}><Icon name="plus" size={17} />添加文件</button>
      </div>
    </header>
  );
}

function Overview({
  files,
  onOpenFile,
  onNavigate
}: {
  files: RoutingFile[];
  onOpenFile: (id: string) => void;
  onNavigate: (id: ViewId) => void;
}) {
  const registered = files.filter((file) => file.state === "registered").length;
  const uploading = files.filter((file) => file.state === "uploading").length;
  const failed = files.filter((file) => file.state === "failed").length;
  const duplicates = files.filter((file) => file.isContentDuplicate).length;

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard label="登记记录" value={files.length.toString()} note="全部摄取记录" tone="blue" icon="file" />
        <MetricCard label="登记成功" value={registered.toString()} note="原始内容可追溯" tone="green" icon="spark" />
        <MetricCard label="上传中" value={uploading.toString()} note="正在写入与计算哈希" tone="violet" icon="clock" />
        <MetricCard label="登记失败" value={failed.toString()} note="查看文件失败原因" tone="amber" icon="review" action={() => onNavigate("intake")} />
      </section>

      <section className="dashboard-grid">
        <article className="panel flow-panel">
          <div className="panel-heading"><div><p className="eyebrow">系统架构</p><h2>模块实施状态</h2></div><span className="live-indicator"><i />第一阶段可用</span></div>
          <div className="system-stage-grid">
            <SystemStage label="Intake" status="available" detail={`${files.length} 个提交`} />
            <SystemStage label="Registry" status="available" detail={`${registered} 个已登记`} />
            <SystemStage label="Inspector" status="planned" detail="下一阶段" />
            <SystemStage label="Router" status="planned" detail="尚未接入" />
            <SystemStage label="Review" status="planned" detail="等待 Router" />
            <SystemStage label="Dispatcher" status="planned" detail="尚未接入" />
            <SystemStage label="Handlers" status="planned" detail="逐个实现" />
          </div>
          <div className="flow-note"><Icon name="shield" /><span>完整模块结构始终保留；每完成一个阶段，只将对应节点切换为真实数据。</span></div>
        </article>

        <article className="panel distribution-panel">
          <div className="panel-heading"><div><p className="eyebrow">存储状态</p><h2>File Registry</h2></div></div>
          <div className="bar-chart">
            <div className="bar-row"><div className="bar-label">登记成功</div><div className="bar-track"><span className="project-materials" style={{ width: `${files.length ? registered / files.length * 100 : 0}%` }} /></div><strong>{registered}</strong></div>
            <div className="bar-row"><div className="bar-label">内容重复</div><div className="bar-track"><span className="architecture" style={{ width: `${files.length ? duplicates / files.length * 100 : 0}%` }} /></div><strong>{duplicates}</strong></div>
            <div className="bar-row"><div className="bar-label">登记失败</div><div className="bar-track"><span className="issues" style={{ width: `${files.length ? failed / files.length * 100 : 0}%` }} /></div><strong>{failed}</strong></div>
          </div>
        </article>
      </section>

      <section className="panel recent-panel">
        <div className="panel-heading"><div><p className="eyebrow">最近活动</p><h2>最新文件</h2></div><button className="text-button" onClick={() => onNavigate("intake")}>查看全部 <Icon name="arrow" size={15} /></button></div>
        <FileTable files={files.slice(0, 5)} onOpen={onOpenFile} />
      </section>
    </div>
  );
}

function MetricCard({ label, value, note, tone, icon, action }: { label: string; value: string; note: string; tone: string; icon: "file" | "spark" | "clock" | "review"; action?: () => void }) {
  return (
    <button className={`metric-card ${action ? "clickable" : ""}`} onClick={action} disabled={!action}>
      <div className={`metric-icon ${tone}`}><Icon name={icon} /></div>
      <div><p>{label}</p><strong>{value}</strong><span>{note}</span></div>
      {action && <Icon className="metric-arrow" name="chevron" size={16} />}
    </button>
  );
}

function SystemStage({ label, status, detail }: { label: string; status: "available" | "planned"; detail: string }) {
  return (
    <div className={`system-stage ${status}`}>
      <div><i /><strong>{label}</strong></div>
      <span>{status === "available" ? "可用" : "未实现"}</span>
      <small>{detail}</small>
    </div>
  );
}

function Intake({
  files,
  projectId,
  onProjectId,
  onFiles,
  onBrowse,
  onOpenFile,
  onResetDuplicates
}: {
  files: RoutingFile[];
  projectId: string;
  onProjectId: (value: string) => void;
  onFiles: (files: File[]) => void;
  onBrowse: () => void;
  onOpenFile: (id: string) => void;
  onResetDuplicates: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  const duplicateCount = files.filter((file) => file.isContentDuplicate).length;
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    onFiles(Array.from(event.dataTransfer.files));
  };

  return (
    <div className="page-stack">
      <section className="intake-layout">
        <div
          className={`drop-zone ${dragging ? "dragging" : ""}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <div className="drop-icon"><Icon name="upload" size={26} /></div>
          <h2>将文件拖到这里</h2>
          <p>系统会保存不可变原始内容，计算 SHA-256 并建立可追溯的登记记录。</p>
          <button className="secondary-button" onClick={onBrowse}>选择文件</button>
          <span>支持 PDF、Word、Excel、Markdown、CSV 和文本文件</span>
        </div>
        <aside className="intake-info panel">
          <p className="eyebrow">接入原则</p>
          <h2>一次提交，可靠登记</h2>
          <label className="field-label" htmlFor="project-id">项目 ID</label>
          <div className="search-box"><input id="project-id" value={projectId} onChange={(event) => onProjectId(event.target.value)} placeholder="输入项目 ID" /></div>
          <ol>
            <li><b>1</b><div><strong>流式接收</strong><span>避免将完整文件载入内存</span></div></li>
            <li><b>2</b><div><strong>内容指纹</strong><span>计算 SHA-256 并复用重复 Blob</span></div></li>
            <li><b>3</b><div><strong>文件登记</strong><span>记录来源、状态和重复关系</span></div></li>
          </ol>
        </aside>
      </section>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">摄取记录</p>
            <h2>全部文件</h2>
          </div>
          <div className="panel-heading-actions">
            <span className="subtle-count">{files.length} 个文件</span>
            <button
              className="secondary-button reset-button"
              disabled={!duplicateCount}
              onClick={onResetDuplicates}
            >
              {`Reset 去重${duplicateCount ? ` (${duplicateCount})` : ""}`}
            </button>
          </div>
        </div>
        <FileTable files={files} onOpen={onOpenFile} />
      </section>
    </div>
  );
}

function ReviewQueue({ files, onOpenFile }: { files: RoutingFile[]; onOpenFile: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<FileCategory | "all">("all");
  const reviewFiles = files.filter((file) => file.state === "review");
  const filtered = useMemo(() => reviewFiles.filter((file) => {
    if (category !== "all" && file.category !== category) return false;
    return `${file.name} ${file.project}`.toLowerCase().includes(query.toLowerCase());
  }), [reviewFiles, query, category]);

  return (
    <div className="page-stack">
      <section className="review-summary">
        <div><span>模块状态</span><strong>未接入</strong><p>等待 Inspector 与 Router</p></div>
        <div><span>待审核</span><strong>{reviewFiles.length}</strong><p>接入 Router 后由真实决策产生</p></div>
        <div><span>当前阶段</span><strong>Phase 1</strong><p>Intake 与 Registry 已可用</p></div>
      </section>
      <section className="panel queue-panel">
        <div className="queue-toolbar">
          <div className="search-box"><Icon name="search" size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索文件或项目" /></div>
          <select value={category} onChange={(event) => setCategory(event.target.value as FileCategory | "all")}>
            <option value="all">全部建议类别</option>
            {(Object.keys(categoryMeta) as FileCategory[]).map((item) => <option key={item} value={item}>{categoryMeta[item].label}</option>)}
          </select>
        </div>
        {filtered.length ? <FileTable files={filtered} onOpen={onOpenFile} reviewMode /> : <EmptyState title="Router 尚未接入" text="页面结构已经保留。Inspector 和 Router 完成后，需要人工确认的真实决策会进入这里。" />}
      </section>
    </div>
  );
}

function Handlers() {
  const statusLabel = {
    planned: "规划中",
    specified: "规则已定义",
    "in-development": "开发中",
    available: "可用"
  } as const;
  return (
    <div className="page-stack">
      <section className="handler-intro panel">
        <div><p className="eyebrow">处理面</p><h2>五个类别，五套独立逻辑</h2><p>Router 只负责选择去向。每个 Handler 独立处理自己的内容模型、审核标准和生命周期。</p></div>
        <div className="contract-chip"><Icon name="shield" /><div><strong>统一 Handler 契约</strong><span>只读输入 · 幂等处理 · Schema 校验</span></div></div>
      </section>
      <section className="handler-grid">
        {handlerStatuses.map((handler) => (
          <article className="handler-card" key={handler.id}>
            <div className="handler-top">
              <div className={`handler-symbol ${handler.category}`}>{categoryMeta[handler.category].short.slice(0, 1)}</div>
              <span className={`health ${handler.implementationStatus}`}><i />{statusLabel[handler.implementationStatus]}</span>
            </div>
            <div className="handler-title"><h3>{handler.label} Handler</h3><code>{handler.version}</code></div>
            <p>{handler.description}</p>
            <div className="handler-plan">
              <div><span>依赖模块</span><strong>{handler.dependency}</strong></div>
              <div><span>下一步</span><strong>{handler.nextStep}</strong></div>
            </div>
            <div className="handler-footer"><code>{handler.id}</code><button aria-label={`查看 ${handler.label} Handler`}><Icon name="chevron" size={17} /></button></div>
          </article>
        ))}
      </section>
    </div>
  );
}

function FileTable({ files, onOpen, reviewMode = false }: { files: RoutingFile[]; onOpen: (id: string) => void; reviewMode?: boolean }) {
  return (
    <div className="table-scroll">
      <table className="file-table">
        <thead><tr><th>文件</th><th>项目</th><th>{reviewMode ? "建议类别" : "SHA-256"}</th><th>{reviewMode ? "置信度" : "状态"}</th><th>提交时间</th><th /></tr></thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id} onClick={() => onOpen(file.id)} tabIndex={0} onKeyDown={(event) => event.key === "Enter" && onOpen(file.id)}>
              <td><div className="file-cell"><span className={`file-type ${file.extension.toLowerCase()}`}>{file.extension.slice(0, 4)}</span><div><strong>{file.name}</strong><span>{file.size} · {file.source}</span></div></div></td>
              <td><span className="project-name">{file.project}</span></td>
              <td>{reviewMode ? <CategoryBadge category={file.category} /> : <code title={file.sha256}>{file.sha256 === "计算中…" ? file.sha256 : `${file.sha256.slice(0, 12)}${file.sha256.length > 12 ? "…" : ""}`}</code>}</td>
              <td>{reviewMode
                ? <Confidence value={file.confidence} />
                : <div className="file-status-stack">
                    <StateBadge state={file.state} />
                    {file.isContentDuplicate && <span className="duplicate-badge">内容重复</span>}
                  </div>}</td>
              <td><span className="time-cell">{file.submittedAt}</span></td>
              <td><Icon className="row-chevron" name="chevron" size={16} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Confidence({ value }: { value: number }) {
  const percent = Math.round(value * 100);
  return <div className={`confidence ${percent < 60 ? "low" : percent < 80 ? "medium" : "high"}`}><div><span style={{ width: `${percent}%` }} /></div><strong>{percent}%</strong></div>;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div><Icon name="search" /></div><h3>{title}</h3><p>{text}</p></div>;
}

function FileDrawer({ file, onClose }: { file: RoutingFile; onClose: () => void }) {
  return (
    <div className="drawer-layer">
      <button className="drawer-backdrop" onClick={onClose} aria-label="关闭详情" />
      <aside className="drawer">
        <div className="drawer-header"><div><p className="eyebrow">文件详情</p><h2>登记记录</h2></div><button className="icon-button" onClick={onClose} aria-label="关闭"><Icon name="close" /></button></div>
        <div className="drawer-file"><span className={`file-type large ${file.extension.toLowerCase()}`}>{file.extension.slice(0, 4)}</span><div><h3>{file.name}</h3><p>{file.project} · {file.size}</p></div></div>

        <section className="drawer-section">
          <div className="section-title"><h3>Registry 状态</h3><StateBadge state={file.state} /></div>
          {file.isContentDuplicate && <><label className="field-label">重复内容</label><p>系统检测到相同内容的再次提交；数据库仅保留这一条文件登记记录。</p></>}
          {file.failureMessage && <><label className="field-label">失败原因</label><p>{file.failureMessage}</p></>}
        </section>

        <section className="drawer-section meta-grid">
          <div><span>文件 ID</span><code>{file.id}</code></div><div><span>批次 ID</span><code>{file.batchId ?? "—"}</code></div><div><span>来源</span><strong>{file.source}</strong></div><div><span>SHA-256</span><code>{file.sha256}</code></div>
        </section>

        <section className="drawer-section lifecycle-sections">
          <div className="lifecycle-row available"><span>1</span><div><strong>Intake 与 Registry</strong><p>已完成原始文件存储、内容指纹和登记。</p></div><b>已完成</b></div>
          <div className="lifecycle-row planned"><span>2</span><div><strong>Inspector</strong><p>等待实现元数据、文本和结构采样。</p></div><b>未执行</b></div>
          <div className="lifecycle-row planned"><span>3</span><div><strong>Router 与 Review</strong><p>等待生成类别候选、证据和审核决策。</p></div><b>未执行</b></div>
          <div className="lifecycle-row planned"><span>4</span><div><strong>Dispatcher 与 Handler</strong><p>等待路由批准后派发给对应类别处理器。</p></div><b>未执行</b></div>
        </section>

        <div className="drawer-actions"><button className="secondary-button" onClick={onClose}>关闭</button></div>
      </aside>
    </div>
  );
}

export default App;
