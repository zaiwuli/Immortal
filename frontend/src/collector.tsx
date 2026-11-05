import { useEffect, useState, useRef } from 'react'
import { createRoot } from 'react-dom/client'
import './collector.css'
async function api(path: string, body?: unknown, method?: string) {
  const r = await fetch('/api' + path, {
    method: method ?? (body === undefined ? 'GET' : 'POST'),
    headers:
      body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  })
  if (!r.ok) {
    let detail
    try {
      detail = (await r.json()).detail
    } catch {
      detail = r.statusText
    }
    throw Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return r.json()
}
const logWords: Record<string, string> = {
  crawl: '采集',
  file: 'CSV 导入',
  legacy: '旧库导入',
  merge: '转换同步',
  cleanup: '数据清理',
  running: '运行中',
  completed: '已完成',
  stopped: '已停止',
  failed: '失败',
  interrupted: '已中断',
  inserted: '新增',
  existing: '已存在',
  skipped: '跳过',
  conflict: '冲突',
  errors: '错误详情',
  row: '行号',
  error: '错误',
  batch_id: '批次',
  id: '编号',
  batch: '批次',
  create_time: '记录时间',
  message: '说明',
  realtime: '实时同步',
  scheduled: '定时同步',
}
function chineseLog(value: unknown): string {
  if (typeof value === 'string') {
    try {
      return chineseLog(JSON.parse(value))
    } catch {
      return logWords[value] ?? value
    }
  }
  if (Array.isArray(value)) return value.map(chineseLog).join('\n')
  if (value && typeof value === 'object')
    return Object.entries(value)
      .map(([key, val]) => `${logWords[key] ?? key}：${chineseLog(val)}`)
      .join('；')
  return String(value ?? '无')
}
type Row = {
  id: number
  tid: number
  title: string
  section: string
  website: string
  source: string
  merge_status: string
  magnet: string[]
  edk: string[]
  preview_images: string[]
  error: string
  batch_id: number
}
type Overview = {
  phase?: string
  sync_queued?: number
  total: number
  pending: number
  active: number | null
  sections: Record<string, string>
  groups: { section: string; source: string; count: number }[]
  batches: { id: number; kind: string; status: string; message: string }[]
}
function App() {
  const csvInput = useRef<HTMLInputElement>(null)
  const [taskTab, setTaskTab] = useState('采集配置')
  const [settingsTab, setSettingsTab] = useState('网络')
  const [logTab, setLogTab] = useState('批次记录')
  const [statusFilter, setStatusFilter] = useState('')
  const [allFiltered, setAllFiltered] = useState(false)
  const [resolution, setResolution] = useState<{operation: string; filters: unknown; confirmation: string; items: {id: number; tid: number; title: string; size: number | null; target_tid: number; available: boolean; existing_title: string | null; existing_website: string | null}[]} | null>(null)
  const prepareResolution = async (operation: string) => {
    try {
      if (!allFiltered && !selected.length) throw Error("请先勾选文章，或选择筛选全部")
      const scope = filters()
      const result = await api('/resolve/preview', {operation, filters: scope})
      setResolution({...result, operation, filters: scope})
    } catch (e) { setError((e as Error).message) }
  }
  const [syncProgress, setSyncProgress] = useState<{running: boolean; processed: number; total: number; stats: Record<string, number>; error: string | null} | null>(null)
  const [runtimeLogs, setRuntimeLogs] = useState('')
  const [autoLogs, setAutoLogs] = useState(true)
  const loadRuntimeLogs = async () => {
    const entries: { time: string; level: string; icon: string; message: string }[] = await api('/runtime-logs')
    setRuntimeLogs([...entries].reverse().map((entry) =>
      `${new Date(entry.time).toLocaleString()} | ${entry.icon} ${entry.level}\n${entry.icon} ${entry.message}`,
    ).join('\n'))
  }
  const [editing, setEditing] = useState<number | null>(null)
  const [page, setPage] = useState('文章管理'),
    [overview, setOverview] = useState<Overview>({
      total: 0,
      pending: 0,
      active: null,
      sections: {},
      groups: [],
      batches: [],
    }),
    [rows, setRows] = useState<Row[]>([]),
    [total, setTotal] = useState(0),
    [num, setNum] = useState(1),
    [section, setSection] = useState(''),
    [keyword, setKeyword] = useState(''),
    [selected, setSelected] = useState<number[]>([]),
    [detail, setDetail] = useState<Row | null>(null),
    [output, setOutput] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [plans, setPlans] = useState<
      {
        id: number
        name: string
        params: Record<string, unknown>
        cron: string
        enabled: boolean
      }[]
    >([]),
    [name, setName] = useState('色花堂采集'),
    [boards, setBoards] = useState<string[]>(['95', '142']),
    [start, setStart] = useState(1),
    [end, setEnd] = useState(''),
    [cron, setCron] = useState(''),
    [enabled, setEnabled] = useState(false),
    [network, setNetwork] = useState({
      PROXY: '',
      FLARE_SOLVERR_URL: '',
      database: '',
      target: '',
    }),
    [cleanOpen, setCleanOpen] = useState(false),
    [cleanSections, setCleanSections] = useState<string[]>([]),
    [syncSettings, setSyncSettings] = useState({
      mode: 'realtime',
      cron: '0 * * * *',
      fallback_minutes: 15,
    }),
    [cleanup, setCleanup] = useState<{
      count: number
      confirmation: string
      sections: string[]
    } | null>(null)
  const filters = () => ({
    merge_status: statusFilter || null,
    section: section || null,
    keyword: keyword || null,
    ids: !allFiltered && selected.length ? selected : null,
  })
  const cleanFilters = () => ({ sections: cleanSections })
  const refresh = async () => {
    const [o, a, t, n] = await Promise.all([
      api('/overview'),
      api('/articles/search?page=' + num, {
        merge_status: statusFilter || null,
        section: section || null,
        keyword: keyword || null,
      }),
      api('/tasks'),
      api('/settings'),
    ])
    setOverview(o)
    setRows(a.items)
    setTotal(a.total)
    setPlans(t)
    setNetwork(n)
    setSyncSettings(await api('/sync/settings'))
  }
  useEffect(() => {
    refresh().catch((e) => setError(e.message))
  }, [num, section, statusFilter])
  useEffect(() => {
    const timer = setInterval(() => {
      api('/sync/status').then(setSyncProgress).catch(() => {})
      api('/overview')
        .then(setOverview)
        .catch(() => {})
    }, 4000)
    return () => clearInterval(timer)
  }, [])
  const action = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setError('')
    try {
      const result = await fn()
      if (result !== undefined) setOutput(JSON.stringify(result, null, 2))
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  useEffect(() => {
    if (page !== '日志' || logTab !== '运行日志') return
    let disposed = false
    const load = () => loadRuntimeLogs().catch((e) => { if (!disposed) setError(e.message) })
    load()
    const timer = autoLogs ? setInterval(load, 3000) : undefined
    return () => { disposed = true; clearInterval(timer) }
  }, [page, logTab, autoLogs])
  const plan = () => ({
    name,
    section_id_list: boards,
    start_page: start,
    max_page: end ? Number(end) : null,
    cron: cron || null,
    enabled,
  })
  return (
    <div className="shell">
      <aside>
        <div className="brand">色花堂采集器</div>
        <div className="brand-caption">拾取新帖 · 有序归档</div>
        <nav>
          {['文章管理', '采集任务', '日志', '设置'].map((p) => (
            <button
              className={page === p ? 'active' : ''}
              key={p}
              onClick={() => {
                setPage(p)
                setOutput('')
                setError('')
              }}
            >
              {p}
            </button>
          ))}
        </nav>
      </aside>
      <main>
        <header>
          <div>
            <h1>{page}</h1>
            <p className="page-caption">
              {
                (
                  {
                    文章管理: '一处整理采集所得，让每条资源各归其位。',
                    采集任务: '按计划巡访，循新帖而来。',
                    日志: '每一次采集，都有迹可循。',
                    设置: '调好连接与节奏，余下交给采集。',
                  } as Record<string, string>
                )[page]
              }
            </p>
          </div>
          <button onClick={() => action(refresh)}>刷新</button>
        </header>
        {page === '采集任务' && (
          <div className="subnav">
            {['采集配置', '定时计划'].map((t) => (
              <button
                key={t}
                className={taskTab === t ? 'selected' : ''}
                onClick={() => {
                  setTaskTab(t)
                  setOutput('')
                }}
              >
                {t}
              </button>
            ))}
          </div>
        )}
        {page === '设置' && (
          <div className="subnav">
            {['网络', '同步策略'].map((t) => (
              <button
                key={t}
                className={settingsTab === t ? 'selected' : ''}
                onClick={() => {
                  setSettingsTab(t)
                  setOutput('')
                }}
              >
                {t}
              </button>
            ))}
          </div>
        )}
        {page === '日志' && (
          <div className="subnav">
            {['运行日志', '批次记录', '详细日志'].map((t) => (
              <button
                key={t}
                className={logTab === t ? 'selected' : ''}
                onClick={() => setLogTab(t)}
              >
                {t}
              </button>
            ))}
          </div>
        )}
        {page === '文章管理' && (
          <div className="stats">
            <div>
              <small>暂存文章</small>
              <strong>{overview.total}</strong>
            </div>
            <div>
              <small>待合并</small>
              <strong>{overview.pending}</strong>
            </div>
            <div>
              <small>采集状态</small>
              <strong>
                {overview.active ? (overview.phase === 'syncing' ? '采集完成 · 同步收尾中' : '采集中 #' + overview.active) : '空闲'}
              </strong>
            </div>
            <div>
              <small>同步状态</small>
              <strong>{overview.sync_queued ? `同步排队 ${overview.sync_queued} 批` : syncProgress?.running ? '同步中' : '空闲'}</strong>
            </div>
          </div>
        )}
        {error && <div className="error">{error}</div>}
        {page === '文章管理' && (
          <>
            <section className="panel">
              <div className="toolbar article-tools">
                <button
                  disabled={busy}
                  onClick={() => csvInput.current?.click()}
                >
                  导入 CSV
                </button>
                <span className="file-input-holder">
                  <input
                    ref={csvInput}
                    style={{ display: 'none' }}
                    type="file"
                    accept=".csv"
                    disabled={busy}
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) {
                        const form = new FormData()
                        form.append('file', file)
                        action(() => api('/import/file', form))
                        e.target.value = ''
                      }
                    }}
                  />
                </span>
                <button
                  onClick={() => {
                    setCleanOpen(true)
                    setCleanup(null)
                    setCleanSections([])
                  }}
                >
                  清理板块
                </button>
                <span>采集与 CSV 共用原始表，后台按设置增量同步</span>
              </div>
              <div className="toolbar">
                <input
                  placeholder="搜索标题"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
                <select
                  value={section}
                  onChange={(e) => {
                    setSection(e.target.value)
                    setAllFiltered(false)
                    setSelected([])
                    setNum(1)
                  }}
                >
                  <option value="">全部板块</option>
                  {Array.from(
                    new Set(overview.groups.filter((g) => g.count > 0).map((g) => g.section)),
                  ).map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
                <select value={statusFilter} onChange={(e) => {setStatusFilter(e.target.value);setSelected([]);setAllFiltered(false);setNum(1)}}>
                  <option value="">全部状态</option>
                  {Object.entries({pending:'待合并',inserted:'已新增',existing:'已存在',failed:'失败',conflict:'冲突'}).map(([value,label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <button
                  onClick={() => {
                    setSelected([])
                    action(refresh)
                  }}
                >
                  搜索
                </button>
              </div>
              <div className="toolbar">
                <button
                  disabled={busy}
                  onClick={() => action(() => api('/convert', filters()))}
                >
                  转换预览
                </button>
                <button
                  className="primary"
                  disabled={busy || syncProgress?.running}
                  onClick={() => {
                    if (
                      confirm(
                        `合并${selected.length ? '选中 ' + selected.length + ' 条' : '当前筛选范围内的全部'}资源到 Avdb 主表？已有记录不会覆盖。`,
                      )
                    )
                      action(() => api('/merge', filters()))
                  }}
                >
                  {syncProgress?.running ? '正在同步…' : '处理并同步'}
                </button>
                <label><input type="checkbox" checked={allFiltered} onChange={(e) => {setAllFiltered(e.target.checked);setSelected([])}} />选择筛选全部（{total} 条）</label>
                {statusFilter === 'failed' && <button disabled={busy || syncProgress?.running} onClick={() => prepareResolution('clear_size')}>大小留空并同步</button>}
                {statusFilter === 'conflict' && <button disabled={busy || syncProgress?.running} onClick={() => prepareResolution('resolve_conflict')}>使用备用 TID 同步</button>}
                {syncProgress && (syncProgress.running || syncProgress.total > 0 || syncProgress.error) && (
                  <span role="status">
                    {syncProgress.running ? '同步中' : '同步结束'}：{syncProgress.processed}/{syncProgress.total}
                    {' · '}{chineseLog(syncProgress.stats)}
                    {syncProgress.error && ` · ${syncProgress.error}`}
                  </span>
                )}
                <button
                  onClick={async () => {
                    try {
                      const r = await fetch('/api/export', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(filters()),
                      })
                      if (!r.ok) throw Error('导出失败')
                      const u = URL.createObjectURL(await r.blob())
                      const a = document.createElement('a')
                      a.href = u
                      a.download = 'sehuatang-collector-articles.csv'
                      a.click()
                      URL.revokeObjectURL(u)
                    } catch (e) {
                      setError((e as Error).message)
                    }
                  }}
                >
                  导出 CSV
                </button>
                <span>
                  {selected.length
                    ? `已选 ${selected.length} 条`
                    : '未选择时操作当前筛选范围'}
                </span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th></th>
                      <th>原帖 / 标题</th>
                      <th>板块</th>
                      <th>链接</th>
                      <th>同步状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selected.includes(a.id)}
                            onChange={(e) =>
                              setSelected(
                                e.target.checked
                                  ? [...selected, a.id]
                                  : selected.filter((x) => x !== a.id),
                              )
                            }
                          />
                        </td>
                        <td>
                          <small>#{a.tid}</small>
                          <button
                            className="text-button"
                            onClick={() => setDetail(a)}
                          >
                            {a.title}
                          </button>
                        </td>
                        <td>{a.section}</td>
                        <td>
                          磁力 {a.magnet?.length ?? 0}
                          <br />
                          ED2K {a.edk?.length ?? 0}
                        </td>
                        <td>
                          <span className={'badge ' + a.merge_status}>
                            {(
                              {
                                pending: '待合并',
                                inserted: '已新增',
                                existing: '已存在',
                                failed: '失败',
                                conflict: '冲突',
                              } as Record<string, string>
                            )[a.merge_status] ?? a.merge_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!rows.length && (
                  <div className="empty">
                    暂无文章，可先导入旧库或 CSV 文件。
                  </div>
                )}
              </div>
              <div className="toolbar footer">
                <span>
                  共 {total} 条 · 第 {num} 页
                </span>
                <button
                  disabled={num <= 1}
                  onClick={() => {
                    setNum(num - 1)
                    setSelected([])
                  }}
                >
                  上一页
                </button>
                <button
                  disabled={num * 30 >= total}
                  onClick={() => {
                    setNum(num + 1)
                    setSelected([])
                  }}
                >
                  下一页
                </button>
              </div>
            </section>
          </>
        )}
        {page === '采集任务' && (
          <>
            {taskTab === '采集配置' && (
              <section className="panel">
                <h2>色花堂采集</h2>
                <p>
                  不填写结束页：智能增量模式，到达同板块历史 TID
                  范围后停止（最多 100
                  页）；填写结束页：按指定页范围抓取。两种模式都跳过已存在帖子。
                </p>
                <label>
                  任务名称
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </label>
                <div className="boards">
                  {Object.entries(overview.sections).map(([id, label]) => (
                    <label key={id}>
                      <input
                        type="checkbox"
                        checked={boards.includes(id)}
                        onChange={(e) =>
                          setBoards(
                            e.target.checked
                              ? [...boards, id]
                              : boards.filter((x) => x !== id),
                          )
                        }
                      />
                      {label} <small>{id}</small>
                    </label>
                  ))}
                </div>
                <div className="grid">
                  <label>
                    起始页
                    <input
                      type="number"
                      min="1"
                      value={start}
                      onChange={(e) => setStart(Number(e.target.value))}
                    />
                  </label>
                  <label>
                    结束页（空为智能）
                    <input
                      type="number"
                      min={start}
                      value={end}
                      onChange={(e) => setEnd(e.target.value)}
                    />
                  </label>
                  <label>
                    定时 Cron（可选）
                    <input
                      placeholder="0 3 * * *"
                      value={cron}
                      onChange={(e) => setCron(e.target.value)}
                    />
                  </label>
                </div>
                <label>
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => setEnabled(e.target.checked)}
                  />
                  启用定时计划
                </label>
                <div className="toolbar">
                  <button
                    className="primary"
                    disabled={busy || !!overview.active || !boards.length}
                    onClick={() => action(() => api('/tasks/run', plan()))}
                  >
                    立即采集
                  </button>
                  <button
                    disabled={busy || !boards.length}
                    onClick={() =>
                      action(() =>
                        api(
                          editing ? '/tasks/' + editing : '/tasks',
                          plan(),
                          editing ? 'PUT' : 'POST',
                        ),
                      )
                    }
                  >
                    {editing ? '更新计划' : '保存计划'}
                  </button>
                  <button
                    className="danger"
                    disabled={!overview.active}
                    onClick={() => action(() => api('/tasks/stop', {}))}
                  >
                    停止当前任务
                  </button>
                </div>
                <p>停止会等待当前请求返回，已保存数据保留，不自动合并。</p>
              </section>
            )}
            {taskTab === '定时计划' && (
              <section className="panel">
                <h2>定时计划</h2>
                {plans.map((t) => (
                  <div className="list-row" key={t.id}>
                    <div>
                      <strong>{t.name}</strong>
                      <p>
                        {t.cron || '手动'} · {t.enabled ? '已启用' : '未启用'} ·{' '}
                        {JSON.stringify(t.params)}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setEditing(t.id)
                        setName(t.name)
                        setBoards((t.params.section_id_list as string[]) || [])
                        setStart(Number(t.params.start_page) || 1)
                        setEnd(
                          t.params.max_page ? String(t.params.max_page) : '',
                        )
                        setCron(t.cron || '')
                        setEnabled(t.enabled)
                        setTaskTab('采集配置')
                      }}
                    >
                      编辑
                    </button>{' '}
                    <button
                      disabled={!!overview.active}
                      onClick={() =>
                        action(() =>
                          api('/tasks/run', { name: t.name, ...t.params }),
                        )
                      }
                    >
                      执行
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('删除该采集计划？'))
                          action(() =>
                            api('/tasks/' + t.id, undefined, 'DELETE'),
                          )
                      }}
                    >
                      删除
                    </button>
                  </div>
                ))}
              </section>
            )}
          </>
        )}
        {page === '设置' && settingsTab === '网络' && (
          <section className="panel">
            <h2>运行设置</h2>
            <p className="connection-status">
              数据库由部署环境配置 · 同步目标：Avdb article
            </p>{' '}
            <label>
              代理地址
              <input
                value={network.PROXY}
                onChange={(e) =>
                  setNetwork({ ...network, PROXY: e.target.value })
                }
                placeholder="http://主机:端口"
              />
            </label>
            <label>
              FlareSolverr 地址
              <input
                value={network.FLARE_SOLVERR_URL}
                onChange={(e) =>
                  setNetwork({ ...network, FLARE_SOLVERR_URL: e.target.value })
                }
                placeholder="http://主机:8191"
              />
            </label>
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                action(() =>
                  api('/settings', {
                    PROXY: network.PROXY,
                    FLARE_SOLVERR_URL: network.FLARE_SOLVERR_URL,
                  }),
                )
              }
            >
              保存网络设置
            </button>
          </section>
        )}
        {page === '设置' && settingsTab === '同步策略' && (
          <section className="panel">
            <h2>同步策略</h2>

            <div className="mode-options">
              <button
                className={syncSettings.mode === 'realtime' ? 'primary' : ''}
                onClick={() =>
                  setSyncSettings({ ...syncSettings, mode: 'realtime' })
                }
              >
                实时同步<span>爬取新增入库后触发，没有新增不运行</span>
              </button>
              <button
                className={syncSettings.mode === 'scheduled' ? 'primary' : ''}
                onClick={() =>
                  setSyncSettings({ ...syncSettings, mode: 'scheduled' })
                }
              >
                定时同步<span>按计划批量处理待同步数据</span>
              </button>
            </div>
            {syncSettings.mode === 'scheduled' && (
              <label>
                定时计划（Cron）
                <input
                  value={syncSettings.cron}
                  placeholder="0 * * * *"
                  onChange={(e) =>
                    setSyncSettings({ ...syncSettings, cron: e.target.value })
                  }
                />
                <small>例如 0 * * * * 表示每小时整点</small>
              </label>
            )}
            <label>
              兜底补同步间隔（分钟）
              <input
                type="number"
                min="1"
                max="1440"
                value={syncSettings.fallback_minutes}
                onChange={(e) =>
                  setSyncSettings({
                    ...syncSettings,
                    fallback_minutes: Number(e.target.value),
                  })
                }
              />
              <small>
                独立检查漏处理、失败及重启遗留记录，定时模式下也会执行。
              </small>
            </label>
            <button
              className="primary"
              disabled={busy}
              onClick={() => action(() => api('/sync/settings', syncSettings))}
            >
              保存同步设置
            </button>
          </section>
        )}
        {page === '日志' && logTab === '批次记录' && (
          <section className="panel">
            <h2>批次记录</h2>
            {overview.batches.map((b) => (
              <div className="list-row" key={b.id}>
                <div>
                  <strong>
                    #{b.id} · {chineseLog(b.kind)} · {chineseLog(b.status)}
                  </strong>
                  <p>{b.message ? chineseLog(b.message) : '处理中'}</p>
                </div>
                <button
                  onClick={() =>
                    action(async () => {
                      const rows = await api('/logs/' + b.id)
                      setLogTab('详细日志')
                      setOutput(
                        rows.length
                          ? rows
                              .map(
                                (row: {
                                  create_time: string
                                  message: string
                                }) =>
                                  `${new Date(row.create_time).toLocaleString()}  ${row.message}`,
                              )
                              .join('\n')
                          : '暂无详细日志',
                      )
                      return undefined
                    })
                  }
                >
                  日志
                </button>
              </div>
            ))}
          </section>
        )}
        {page === '日志' && logTab === '运行日志' && (
          <section className="panel">
            <div className="toolbar">
              <h2>运行日志</h2>
              <label><input type="checkbox" checked={autoLogs} onChange={(e) => setAutoLogs(e.target.checked)} />自动刷新</label>
              <button onClick={() => loadRuntimeLogs().catch((e) => setError(e.message))}>刷新</button>
            </div>
            <p>最近 1000 条 · 每 3 秒刷新 · 服务重启后重新记录</p>
            <pre style={{ maxHeight: '65vh', overflow: 'auto' }}>{runtimeLogs || '暂无运行日志'}</pre>
          </section>
        )}
        {(page === '日志' ? logTab === '详细日志' : !!output) && (
          <section className="panel">
            <div className="toolbar">
              <h2>{page === '日志' ? '日志详情' : '操作结果 / 转换预览'}</h2>
              <button onClick={() => setOutput('')}>收起</button>
            </div>
            <pre>{output || '请在批次记录中选择一条日志。'}</pre>
          </section>
        )}
        {resolution && (
          <div className="modal" onClick={() => setResolution(null)}>
            <section className="panel" style={{maxWidth:'1000px',maxHeight:'85vh',overflow:'auto'}} onClick={(e) => e.stopPropagation()}>
              <h2>{resolution.operation === 'clear_size' ? '确认大小留空并同步' : '确认使用备用 TID 同步'}</h2>
              <p>可处理 {resolution.items.filter((item) => item.available).length} 条，共 {resolution.items.length} 条。原始数据保留，Avdb 已有文章不覆盖。</p>
              <p>{resolution.operation === 'clear_size' ? '仅处理大小超出范围的失败项，确认后目标大小为 NULL。' : '备用 TID = 原始 TID × 10000 ＋原始 TID；已占用的跳过。'}</p>
              <table><thead><tr><th>原始 TID / 标题</th><th>原始大小 / 备用 TID</th><th>检查结果</th></tr></thead><tbody>
                {resolution.items.map((item) => <tr key={item.id}><td>{item.tid} · {item.title}<p>{item.existing_website} {item.existing_title}</p></td><td>{resolution.operation === 'clear_size' ? String(item.size ?? '空') : item.target_tid}</td><td>{item.available ? '可处理' : '已占用或超出范围'}</td></tr>)}
              </tbody></table>
              <div className="toolbar"><button onClick={() => setResolution(null)}>取消</button><button disabled={busy || !resolution.items.some((item) => item.available)} onClick={() => action(async () => {const result=await api('/resolve', resolution);setResolution(null);return result})}>确认处理可用记录</button></div>
            </section>
          </div>
        )}
        {cleanOpen && (
          <div className="modal" onClick={() => setCleanOpen(false)}>
            <section
              className="panel clean-dialog"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="toolbar">
                <h2>清理指定板块</h2>
                <button onClick={() => setCleanOpen(false)}>关闭</button>
              </div>
              <p>
                多选要删除的板块。清理原始表及其转换结果，不影响目标表已展示的文章。删除历史数据可能使该板块重新采集。
              </p>
              <div className="boards">
                {Array.from(new Set(overview.groups.map((g) => g.section))).map(
                  (name) => (
                    <label key={name}>
                      <input
                        type="checkbox"
                        checked={cleanSections.includes(name)}
                        onChange={(e) => {
                          setCleanSections(
                            e.target.checked
                              ? [...cleanSections, name]
                              : cleanSections.filter((s) => s !== name),
                          )
                          setCleanup(null)
                        }}
                      />
                      {name}
                    </label>
                  ),
                )}
              </div>
              <button
                disabled={busy || !cleanSections.length}
                onClick={() =>
                  action(async () => {
                    const result = await api('/cleanup/preview', cleanFilters())
                    setCleanup(result)
                    return undefined
                  })
                }
              >
                预览删除数量
              </button>
              {cleanup && (
                <div className="warning">
                  将删除 {cleanup.count} 条文章及关联转换记录。
                  <button
                    className="danger"
                    disabled={busy || !cleanup.count}
                    onClick={() => {
                      if (
                        confirm(
                          `确认删除所选板块的 ${cleanup.count} 条原始文章及转换结果？目标表不会删除。`,
                        )
                      )
                        action(async () => {
                          const result = await api('/cleanup', {
                            filters: cleanFilters(),
                            confirmation: cleanup.confirmation,
                          })
                          setCleanup(null)
                          setCleanOpen(false)
                          return result
                        })
                    }}
                  >
                    确认删除
                  </button>
                </div>
              )}
            </section>
          </div>
        )}
        {detail && (
          <div className="modal" onClick={() => setDetail(null)}>
            <section className="panel" onClick={(e) => e.stopPropagation()}>
              <div className="toolbar">
                <h2>文章详情 #{detail.tid}</h2>
                <button onClick={() => setDetail(null)}>关闭</button>
              </div>
              <h3>{detail.title}</h3>
              <p>
                {detail.section} · {detail.website} · {detail.error}
              </p>
              <button
                onClick={() => {
                  navigator.clipboard
                    .writeText(
                      [...(detail.magnet || []), ...(detail.edk || [])].join(
                        '\n',
                      ),
                    )
                    .catch(() => setError('复制失败，请在下方手动选择'))
                }}
              >
                复制原始下载链接
              </button>
              <pre>
                {[...(detail.magnet || []), ...(detail.edk || [])].join('\n')}
              </pre>
              <div className="images">
                {detail.preview_images?.map((url, i) => (
                  <img
                    loading="lazy"
                    key={i}
                    src={url}
                    referrerPolicy="no-referrer"
                  />
                ))}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
createRoot(document.getElementById('root')!).render(<App />)
