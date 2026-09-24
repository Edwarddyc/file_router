import { useMemo, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Icon } from "./components/Icon";
import { CategoryBadge, StateBadge } from "./components/StatusBadge";
import { handlerStatuses, initialFiles } from "./data/mockData";
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

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function App() {
  const [view, setView] = useState<ViewId>("overview");
  const [files, setFiles] = useState<RoutingFile[]>(initialFiles);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selected = files.find((file) => file.id === selectedId) ?? null;
  const reviewCount = files.filter((file) => file.state === "review").length;

  const addFiles = (incoming: File[]) => {
    const created: RoutingFile[] = incoming.map((file, index) => ({
      id: `file_local_${Date.now()}_${index}`,
      name: file.name,
      project: "待分配项目",
      size: formatFileSize(file.size),
      extension: file.name.split(".").pop()?.toUpperCase() || "FILE",
      submittedAt: "刚刚",
      secondarySignals: [],
      confidence: 0,
      disposition: "needs-review",
      state: "routing",
      reasons: [{ source: "policy", code: "new-ingest", evidence: "文件已登记，正在提取路由特征。" }],
      sha256: "计算中…",
      source: "本地上传"
    }));

    setFiles((current) => [...created, ...current]);
    setView("intake");

    window.setTimeout(() => {
      setFiles((current) => current.map((file) => created.some((item) => item.id === file.id)
        ? {
            ...file,
            confidence: 0.64,
            state: "review",
            reasons: [{ source: "policy", code: "prototype-review", evidence: "前端原型已完成登记；连接路由 API 后将返回实际分类证据。" }]
          }
        : file));
    }, 1100);
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  };

  const updateFile = (id: string, update: Partial<RoutingFile>) => {
    setFiles((current) => current.map((file) => file.id === id ? { ...file, ...update } : file));
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
          onMenu={() => setSidebarOpen(true)}
          onUpload={() => fileInputRef.current?.click()}
        />

        <input ref={fileInputRef} className="visually-hidden" type="file" multiple onChange={handleFileInput} />

        <div className="page-content">
          {view === "overview" && (
            <Overview files={files} onOpenFile={setSelectedId} onNavigate={navigate} />
          )}
          {view === "intake" && (
            <Intake files={files} onFiles={addFiles} onBrowse={() => fileInputRef.current?.click()} onOpenFile={setSelectedId} />
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
          onUpdate={(update) => updateFile(selected.id, update)}
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

function Header({ view, onMenu, onUpload }: { view: ViewId; onMenu: () => void; onUpload: () => void }) {
  const meta = viewTitles[view];
  return (
    <header className="topbar">
      <div className="topbar-title">
        <button className="icon-button menu-button" onClick={onMenu} aria-label="打开导航"><Icon name="menu" /></button>
        <div><h1>{meta.title}</h1><p>{meta.subtitle}</p></div>
      </div>
      <button className="primary-button" onClick={onUpload}><Icon name="plus" size={17} />添加文件</button>
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
  const accepted = files.filter((file) => file.state === "accepted").length;
  const processing = files.filter((file) => file.state === "processing" || file.state === "routing").length;
  const reviews = files.filter((file) => file.state === "review").length;
  const routed = files.filter((file) => file.category);
  const autoRate = routed.length ? Math.round(routed.filter((file) => file.disposition === "auto-route").length / routed.length * 100) : 0;

  const distribution = (Object.keys(categoryMeta) as FileCategory[]).map((category) => ({
    category,
    count: files.filter((file) => file.category === category).length
  }));
  const max = Math.max(1, ...distribution.map((item) => item.count));

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard label="本批次文件" value={files.length.toString()} note="今日新增" tone="blue" icon="file" />
        <MetricCard label="自动路由率" value={`${autoRate}%`} note="高置信度直接派发" tone="green" icon="spark" />
        <MetricCard label="处理中" value={processing.toString()} note="跨 5 个处理器" tone="violet" icon="clock" />
        <MetricCard label="待人工审核" value={reviews.toString()} note="需要你的判断" tone="amber" icon="review" action={() => onNavigate("review")} />
      </section>

      <section className="dashboard-grid">
        <article className="panel flow-panel">
          <div className="panel-heading"><div><p className="eyebrow">实时流程</p><h2>摄取管线</h2></div><span className="live-indicator"><i />运行正常</span></div>
          <div className="pipeline">
            <PipelineStep label="已登记" value={files.length} icon="upload" tone="blue" complete />
            <span className="pipeline-line" />
            <PipelineStep label="已路由" value={routed.length} icon="spark" tone="violet" complete />
            <span className="pipeline-line" />
            <PipelineStep label="处理中" value={processing} icon="layers" tone="amber" active />
            <span className="pipeline-line" />
            <PipelineStep label="已收录" value={accepted} icon="check" tone="black" />
          </div>
          <div className="flow-note"><Icon name="shield" /><span>原始文件保持只读，每个决策均保留证据与策略版本。</span></div>
        </article>

        <article className="panel distribution-panel">
          <div className="panel-heading"><div><p className="eyebrow">文件去向</p><h2>类别分布</h2></div><button className="text-button" onClick={() => onNavigate("handlers")}>查看处理器 <Icon name="arrow" size={15} /></button></div>
          <div className="bar-chart">
            {distribution.map(({ category, count }) => (
              <div className="bar-row" key={category}>
                <div className="bar-label"><span className={`category-dot ${category}`} />{categoryMeta[category].label}</div>
                <div className="bar-track"><span className={category} style={{ width: `${Math.max(count ? 12 : 0, count / max * 100)}%` }} /></div>
                <strong>{count}</strong>
              </div>
            ))}
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

function PipelineStep({ label, value, icon, tone, complete, active }: { label: string; value: number; icon: "upload" | "spark" | "layers" | "check"; tone: "blue" | "violet" | "amber" | "black"; complete?: boolean; active?: boolean }) {
  return (
    <div className={`pipeline-step ${tone} ${complete ? "complete" : ""} ${active ? "active" : ""}`}>
      <div><Icon name={icon} /></div><strong>{value}</strong><span>{label}</span>
    </div>
  );
}

function Intake({ files, onFiles, onBrowse, onOpenFile }: { files: RoutingFile[]; onFiles: (files: File[]) => void; onBrowse: () => void; onOpenFile: (id: string) => void }) {
  const [dragging, setDragging] = useState(false);
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
          <p>系统会统一完成登记、检查和路由，不会修改你的原始文件。</p>
          <button className="secondary-button" onClick={onBrowse}>选择文件</button>
          <span>支持 PDF、Word、Excel、Markdown、CSV 和文本文件</span>
        </div>
        <aside className="intake-info panel">
          <p className="eyebrow">接入原则</p>
          <h2>一次提交，自动分流</h2>
          <ol>
            <li><b>1</b><div><strong>登记与指纹</strong><span>记录来源、大小、哈希和重复关系</span></div></li>
            <li><b>2</b><div><strong>轻量检查</strong><span>提取标题、章节和表格结构</span></div></li>
            <li><b>3</b><div><strong>分类与派发</strong><span>高置信度自动进入对应 Handler</span></div></li>
          </ol>
        </aside>
      </section>
      <section className="panel recent-panel">
        <div className="panel-heading"><div><p className="eyebrow">摄取记录</p><h2>全部文件</h2></div><span className="subtle-count">{files.length} 个文件</span></div>
        <FileTable files={files} onOpen={onOpenFile} />
      </section>
    </div>
  );
}

function ReviewQueue({ files, onOpenFile }: { files: RoutingFile[]; onOpenFile: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<FileCategory | "all">("all");
  const filtered = useMemo(() => files.filter((file) => {
    if (file.state !== "review") return false;
    if (category !== "all" && file.category !== category) return false;
    return `${file.name} ${file.project}`.toLowerCase().includes(query.toLowerCase());
  }), [files, query, category]);

  return (
    <div className="page-stack">
      <section className="review-summary">
        <div><span>待审核</span><strong>{files.filter((file) => file.state === "review").length}</strong><p>需要人工确认主要类别</p></div>
        <div><span>平均置信度</span><strong>{Math.round((files.filter((file) => file.state === "review").reduce((sum, file) => sum + file.confidence, 0) / Math.max(1, files.filter((file) => file.state === "review").length)) * 100)}%</strong><p>建议优先查看低置信度文件</p></div>
        <div><span>最长等待</span><strong>1 天</strong><p>当前没有超期任务</p></div>
      </section>
      <section className="panel queue-panel">
        <div className="queue-toolbar">
          <div className="search-box"><Icon name="search" size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索文件或项目" /></div>
          <select value={category} onChange={(event) => setCategory(event.target.value as FileCategory | "all")}>
            <option value="all">全部建议类别</option>
            {(Object.keys(categoryMeta) as FileCategory[]).map((item) => <option key={item} value={item}>{categoryMeta[item].label}</option>)}
          </select>
        </div>
        {filtered.length ? <FileTable files={filtered} onOpen={onOpenFile} reviewMode /> : <EmptyState title="没有匹配的审核任务" text="调整筛选条件，或等待新的文件进入复核队列。" />}
      </section>
    </div>
  );
}

function Handlers() {
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
              <span className={`health ${handler.status}`}><i />{handler.status === "healthy" ? "运行正常" : handler.status === "draft" ? "试运行" : "需要关注"}</span>
            </div>
            <div className="handler-title"><h3>{handler.label} Handler</h3><code>{handler.version}</code></div>
            <p>{handler.description}</p>
            <div className="handler-stats">
              <div><span>已处理</span><strong>{handler.processed}</strong></div>
              <div><span>待处理</span><strong>{handler.pending}</strong></div>
              <div><span>成功率</span><strong>{handler.successRate}%</strong></div>
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
        <thead><tr><th>文件</th><th>项目</th><th>建议类别</th><th>{reviewMode ? "置信度" : "状态"}</th><th>提交时间</th><th /></tr></thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id} onClick={() => onOpen(file.id)} tabIndex={0} onKeyDown={(event) => event.key === "Enter" && onOpen(file.id)}>
              <td><div className="file-cell"><span className={`file-type ${file.extension.toLowerCase()}`}>{file.extension.slice(0, 4)}</span><div><strong>{file.name}</strong><span>{file.size} · {file.source}</span></div></div></td>
              <td><span className="project-name">{file.project}</span></td>
              <td><CategoryBadge category={file.category} /></td>
              <td>{reviewMode ? <Confidence value={file.confidence} /> : <StateBadge state={file.state} />}</td>
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

function FileDrawer({ file, onClose, onUpdate }: { file: RoutingFile; onClose: () => void; onUpdate: (update: Partial<RoutingFile>) => void }) {
  const [category, setCategory] = useState<FileCategory>(file.category ?? "project-materials");
  const approve = () => {
    onUpdate({ category, confidence: Math.max(file.confidence, 0.99), disposition: "auto-route", state: "processing", reasons: [...file.reasons, { source: "reviewer", code: "manual-approval", evidence: `审核人确认主要类别为“${categoryMeta[category].label}”。` }] });
    onClose();
  };

  return (
    <div className="drawer-layer">
      <button className="drawer-backdrop" onClick={onClose} aria-label="关闭详情" />
      <aside className="drawer">
        <div className="drawer-header"><div><p className="eyebrow">文件详情</p><h2>路由判断</h2></div><button className="icon-button" onClick={onClose} aria-label="关闭"><Icon name="close" /></button></div>
        <div className="drawer-file"><span className={`file-type large ${file.extension.toLowerCase()}`}>{file.extension.slice(0, 4)}</span><div><h3>{file.name}</h3><p>{file.project} · {file.size}</p></div></div>

        <section className="drawer-section">
          <div className="section-title"><h3>建议路由</h3><Confidence value={file.confidence} /></div>
          <label className="field-label">主要类别</label>
          <select className="wide-select" value={category} onChange={(event) => setCategory(event.target.value as FileCategory)}>
            {(Object.keys(categoryMeta) as FileCategory[]).map((item) => <option key={item} value={item}>{categoryMeta[item].label}</option>)}
          </select>
          {!!file.secondarySignals.length && <><label className="field-label">次级信号</label><div className="signal-list">{file.secondarySignals.map((signal) => <span key={signal}>{signal}</span>)}</div></>}
        </section>

        <section className="drawer-section">
          <h3>判断依据</h3>
          <div className="reason-list">
            {file.reasons.map((reason, index) => <div key={`${reason.code}-${index}`}><span>{index + 1}</span><div><strong>{reason.code}</strong><p>{reason.evidence}</p><small>{reason.source}</small></div></div>)}
          </div>
        </section>

        <section className="drawer-section meta-grid">
          <div><span>文件 ID</span><code>{file.id}</code></div><div><span>来源</span><strong>{file.source}</strong></div><div><span>SHA-256</span><code>{file.sha256}</code></div><div><span>策略版本</span><code>routing-policy.v1</code></div>
        </section>

        <div className="drawer-actions"><button className="secondary-button" onClick={onClose}>暂不处理</button><button className="primary-button" onClick={approve}><Icon name="check" size={17} />确认并派发</button></div>
      </aside>
    </div>
  );
}

export default App;
