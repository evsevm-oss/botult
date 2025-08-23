import React, { useMemo, useState, useEffect, useRef, useCallback } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  ReferenceLine,
  Legend,
} from "recharts";
import { Loader2, Trash2, Pencil, ChevronLeft, ChevronRight, Calendar } from "lucide-react";
import { apiFetch, getTelegramId } from './auth';

const RootStyles: React.FC = () => (
  <style>{`
    *,*::before,*::after{box-sizing:border-box}
    html,body{margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',Roboto,Arial,'Noto Sans','Apple Color Emoji','Segoe UI Emoji',sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
    img,svg,video,canvas{display:block;max-width:100%}
    button,input,select,textarea{font:inherit;color:inherit;background:transparent;border:0;-webkit-appearance:none;appearance:none;padding:0;border-radius:0}
    /* Robust custom radios (work across Telegram WebView versions) */
    .field label{ display:flex; align-items:flex-start; gap:8px; }
    .field label input[type="radio"]{ position:absolute; opacity:0; width:1px; height:1px; }
    .field label span{ display:inline-flex; align-items:flex-start; line-height:1.35; }
    .field label span::before{ content:""; display:inline-block; width:18px; height:18px; flex:0 0 18px; border-radius:9999px; border:2px solid rgba(255,255,255,0.35); margin-right:8px; margin-top:2px; box-sizing:border-box; }
    .field label input[type="radio"]:checked + span{ color: var(--link); font-weight:600; }
    .field label input[type="radio"]:checked + span::before{ border-color: var(--link); background: radial-gradient(circle, var(--link) 6px, transparent 7px); }
    .field label input[type="radio"]:focus-visible + span::before{ outline:2px solid rgba(109,40,217,0.65); outline-offset:2px; }
    a{color:inherit;text-decoration:none}
    #root{isolation:isolate}
    :root {
      --bg: var(--tg-theme-bg-color, #0b1020);
      --text: var(--tg-theme-text-color, #eef2ff);
      --card: var(--tg-theme-secondary-bg-color, #12172a);
      --muted: var(--tg-theme-hint-color, #94a3b8);
      --link: var(--tg-theme-link-color, #7aa2ff);
      --primary: var(--tg-theme-button-color, #6d28d9);
      --primary-text: var(--tg-theme-button-text-color, #ffffff);
      --chart-grid: rgba(255,255,255,0.08);
      --ok: #10b981;
      --warn: #f59e0b;
      --err: #ef4444;
      --radius: 16px;
    }
    html, body, #root { height: 100%; background: var(--bg); color: var(--text); }
    .container { position:relative; padding-top: calc(env(safe-area-inset-top, 0px) + 12px); padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 108px); min-height: 100vh; box-sizing: border-box; }
    .glass { background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)); backdrop-filter: saturate(160%) blur(8px); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius); }
    .card { background: var(--card); border-radius: var(--radius); border: 1px solid rgba(255,255,255,0.08); }
    .h1 { font-size: 20px; font-weight: 700; }
    .h2 { font-size: 16px; font-weight: 700; }
    .subtle { color: var(--muted); }
    .btn { height: 44px; min-width: 44px; padding: 0 16px; border-radius: 12px; font-weight: 600; }
    .btn-primary { background: var(--primary); color: var(--primary-text); transition: transform 0.12s ease, box-shadow 0.2s ease, filter 0.2s ease; }
    .btn-primary:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 14px 40px rgba(109,40,217,0.35); }
    .btn-primary:active:not(:disabled) { transform: translateY(0); filter: brightness(0.98); box-shadow: 0 8px 24px rgba(109,40,217,0.28); }
    .btn-primary:focus-visible { outline: 2px solid rgba(109,40,217,0.65); outline-offset: 2px; }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-ghost { background: transparent; color: var(--text); border: 1px solid rgba(255,255,255,0.14); }
    .tab { display:inline-flex; align-items:center; justify-content:center; min-height: 36px; height: auto; padding: 8px 14px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.14); white-space: nowrap; line-height: 1; background: rgba(255,255,255,0.06); color: var(--text); }
    .tab-active { background: rgba(109,40,217,0.22); border-color: rgba(109,40,217,0.42); }
    .tab:active{filter:brightness(0.95)}
    .tabs { display:flex; gap:8px; overflow-x:auto; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
    .tabs::-webkit-scrollbar{ display:none; }
    .row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
    .row .subtle { white-space: nowrap; }
    .metric { background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; }
    .metric-btn { width:100%; text-align:left; cursor:pointer; }
    .metric-btn:focus { outline: 2px solid rgba(109,40,217,0.65); outline-offset: 2px; }
    .value-xl { font-size: 20px; font-weight: 700; }
    .pill { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.16); color: var(--muted); font-size: 12px; line-height: 18px; white-space: nowrap; background: rgba(255,255,255,0.04); max-width:100%; overflow:hidden; text-overflow:ellipsis; }
    .pill-wrap{white-space:normal;display:inline-flex;flex-direction:column;align-items:flex-end;line-height:1.2}
    .mono { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
    .shadow-xl { box-shadow: 0 10px 30px rgba(16,24,40,0.35); }
    .main-gradient { background: radial-gradient(1200px 400px at 50% -10%, rgba(99,102,241,0.25), transparent), radial-gradient(800px 300px at 0% 10%, rgba(147,51,234,0.15), transparent), radial-gradient(800px 300px at 100% 10%, rgba(56,189,248,0.12), transparent); }
    .chart-wrap{position:relative}
    .chart-labels{position:absolute; top:8px; left:8px; right:8px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap; pointer-events:none}
    @media (max-width: 420px){
      .chart-labels{ right:auto; justify-content:flex-start; align-items:flex-start; flex-direction:column; gap:6px }
      .chart-labels .pill{ font-size:11px; padding:2px 8px }
      .pill-extra{ display:none }
    }
    .skeleton { position: relative; overflow: hidden; background: rgba(255,255,255,0.06); }
    .skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent); transform: translateX(-100%); animation: sk 1.4s infinite; }
    @keyframes sk { 100% { transform: translateX(100%); } }
    @media (min-width: 960px) { .grid-desktop { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } }

    /* Utilities (to mimic small subset of tailwind, ensure consistent layout on all devices) */
    .flex{display:flex}
    .flex-wrap{flex-wrap:wrap}
    .flex-col{display:flex;flex-direction:column}
    .items-center{align-items:center}
    .justify-between{justify-content:space-between}
    .gap-1{gap:4px}
    .gap-2{gap:8px}
    .gap-3{gap:12px}
    .mt-1{margin-top:4px}
    .mt-3{margin-top:12px}
    .mt-4{margin-top:16px}
    .mb-3{margin-bottom:12px}
    .mr-1{margin-right:4px}
    .pr-3{padding-right:12px}
    .p-4{padding:16px}
    .p-3{padding:12px}
    .px-3{padding-left:12px;padding-right:12px}
    .pt-3{padding-top:12px}
    .w-full{width:100%}
    .w-48{width:192px}
    .w-64{width:256px}
    .w-72{width:288px}
    .text-left{text-align:left}
    .truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .text-xs{font-size:12px}
    .text-sm{font-size:14px}
    .text-lg{font-size:18px}
    .h-5{height:20px}
    .h-6{height:24px}
    .h-10{height:40px}
    .h-16{height:64px}
    .h-220{height:220px}
    .h-240{height:240px}
    .minh-360{min-height:360px}
    .min-h-360{min-height:360px}
    .min-h-\[360px\]{min-height:360px}
    .h-\[220px\]{height:220px}
    .h-\[240px\]{height:240px}
    .grid{display:grid}
    .grid-cols-6{grid-template-columns:repeat(6,minmax(0,1fr))}
    .grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .row-grid{display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:center}
    .row-grid>button{background:none!important;border:0!important;padding:0!important;border-radius:0!important}
    .mb-1{margin-bottom:4px}
    .mb-2{margin-bottom:8px}
    .mt-auto{margin-top:auto}
    .self-end{align-self:flex-end}
    .cursor-pointer{cursor:pointer}
    .border-l-4{border-left-width:4px}
    .list-disc{list-style-type:disc}
    .pl-6{padding-left:24px}
    @media (min-width:960px){.md\:grid-cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}}

    /* Tiles grid used in MainInfo */
    .grid-tiles{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
    .tile-half{grid-column:span 3 / span 3}
    .tile-row-2{grid-row:span 2 / span 2}
    @media (min-width:960px){
      .grid-tiles{grid-template-columns:repeat(3,minmax(0,1fr))}
      .tile-md-col-1{grid-column:span 1 / span 1}
      .tile-md-row-1{grid-row:span 1 / span 1}
    }

    /* Simple spin animation (for Loader2) */
    @keyframes spin{to{transform:rotate(360deg)}}
    .animate-spin{animation:spin 1s linear infinite}

    /* Modal */
    .modal-root { position: fixed; inset: 0; z-index: 50; }
    .backdrop { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.55); z-index: 50; }
    .modal { position: fixed; z-index: 51; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(86vw, 420px); background: var(--card); border:1px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 16px; }
    .field { display:flex; flex-direction:column; gap:6px; margin-top:10px; }
    .input { width:100%; height:40px; border-radius: 10px; background: rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding: 0 10px; color: var(--text); }
    .modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:12px; }

    /* Extra utility aliases used in markup */
    .space-y-3 > * + * { margin-top: 12px; }
    .rounded { border-radius: 8px; }
    .rounded-md { border-radius: 12px; }
    .rounded-lg { border-radius: 16px; }
    .mt-2 { margin-top: 8px; }
    .grid-cols-1 { grid-template-columns: repeat(1, minmax(0,1fr)); }
    .grid-cols-3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
    @media (min-width: 640px) { .sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0,1fr)); } }
    .text-\[12px\] { font-size: 12px; }
  `}</style>
);

// Демоданные
// Демо-данные удалены: показываем только реальные данные, если они есть
const last7: { d: string; kcal: number; protein: number }[] = [];

const foods = [
  { name: "Starbucks Cappuccino (Grande)", kcal: 540 },
  { name: "Tequenos", kcal: 120 },
  { name: "Danone YoPRO PROTEIN PUDDING", kcal: 254 },
  { name: "Tomatoes", kcal: 179 },
  { name: "Тверской кондитер \"Пастила с ароматом клюквы\"", kcal: 546 },
  { name: "Starbucks Cappuccino (Grande)", kcal: 540 },
  { name: "Tequenos", kcal: 120 },
  { name: "Danone YoPRO PROTEIN PUDDING", kcal: 254 },
  { name: "Tomatoes", kcal: 179 },
  { name: "Тверской кондитер \"Пастила с ароматом клюквы\"", kcal: 546 },
];

const nf = (v: number, d = 0) => v.toLocaleString("ru-RU", { maximumFractionDigits: d, minimumFractionDigits: d });

const Chip: React.FC<{ active?: boolean; onClick?: () => void; label: string }> = ({ active, onClick, label }) => (
  <button className={`tab ${active ? "tab-active" : ""}`} onClick={onClick} aria-pressed={!!active} aria-label={label}>
    {label}
  </button>
);

const Card: React.FC<{ title?: string; extra?: React.ReactNode; className?: string; children?: React.ReactNode }>
  = ({ title, extra, className, children }) => (
  <section className={`card p-4 shadow-xl ${className || ""}`}> 
    {(title || extra) && (
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        {title && <div className="h2">{title}</div>}
        {extra}
      </div>
    )}
    {children}
  </section>
);

// --- Modal ---
function Modal(
  { title, children, onClose, onSave, saveLabel = "Сохранить", saveDisabled = false }:
  { title: string; children: React.ReactNode; onClose: () => void; onSave: () => void; saveLabel?: string; saveDisabled?: boolean }
) {
  return (
    <div className="modal-root" role="presentation">
      <div className="backdrop" onClick={onClose} aria-hidden={true} />
      <div className="modal" role="dialog" aria-modal={true} aria-label={title}>
        <div className="h2 mb-2">{title}</div>
        {children}
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Отмена</button>
          <button className="btn btn-primary" onClick={onSave} disabled={saveDisabled} aria-disabled={saveDisabled}>
            {saveLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Goal presets & helpers ---
const GOAL_PRESETS: Record<'loss'|'maint'|'gain'|'nocw', { title: string; note: string }> = {
  loss:  { title: 'Снижение веса',       note: 'дефицит калорий' },
  maint: { title: 'Поддержание веса',    note: 'после снижения веса' },
  gain:  { title: 'Рост мышечной массы', note: '' },
  nocw:  { title: 'Без цели по весу',    note: 'контроль потребления' },
};
const inferGoalMode = (title: string, note: string): 'loss'|'maint'|'gain'|'nocw' => {
  if (title === 'Снижение веса' && note === 'дефицит калорий') return 'loss';
  if (title === 'Поддержание веса' && note === 'после снижения веса') return 'maint';
  if (title === 'Рост мышечной массы') return 'gain';
  if (title === 'Без цели по весу' && note === 'контроль потребления') return 'nocw';
  return 'loss';
};

interface MainInfoProps {
  values: {
    goalTitle: string;
    goalNote: string;
    dateRange: string;
    calPlan: number;
    protPlan: number;
    weight: number;
    weightDelta: string;
    fatPct: number;
    fatDelta: string;
  };
  onEditGoal: () => void;
  onEditCalories: () => void;
  onEditProtein: () => void;
  onAddWeightToday: () => void;
  onAddFatToday: () => void;
}

const MainInfo: React.FC<MainInfoProps> = ({ values, onEditGoal, onEditCalories, onEditProtein, onAddWeightToday, onAddFatToday }) => (
  <Card>
    <div className="space-y-3">
      {/* Группа 1 */}
      <div className="grid-tiles">
        {/* Цель */}
        <button className="metric metric-btn tile-half tile-row-2 flex-col" onClick={onEditGoal} aria-label="Изменить цель">
          <div className="subtle text-[12px] mb-1">Цель</div>
          <div className="value-xl">{values.goalTitle}</div>
          {values.goalNote ? <div className="subtle text-xs">{values.goalNote}</div> : null}
          {values.dateRange && (
            <div className="pill pill-wrap mt-auto self-end" title={values.dateRange}>
              {values.dateRange.includes('–') ? (
                <>
                  <span>{values.dateRange.split('–')[0].trim()}</span>
                  <span>– {values.dateRange.split('–')[1].trim()}</span>
                </>
              ) : (
                <span>{values.dateRange}</span>
              )}
            </div>
          )}
        </button>
        {/* Калории */}
        <button className="metric metric-btn tile-half" onClick={onEditCalories} aria-label="Изменить план калорий">
          <div className="subtle text-[12px] mb-1">Калории</div>
          <div className="value-xl mono">{Number.isFinite(values.calPlan) ? `< ${nf(values.calPlan)} ккал` : '—'}</div>
          <div className="pill mt-1">план на день</div>
        </button>
        {/* Протеин */}
        <button className="metric metric-btn tile-half" onClick={onEditProtein} aria-label="Изменить план протеина">
          <div className="subtle text-[12px] mb-1">Протеин</div>
          <div className="value-xl mono">{Number.isFinite(values.protPlan) ? `> ${nf(values.protPlan)} г` : '—'}</div>
          <div className="pill mt-1">план на день</div>
        </button>
      </div>

      {/* Группа 2: вес и жир */}
      <div className="grid grid-cols-2 gap-3">
        <button className="metric metric-btn flex items-center justify-between" onClick={onAddWeightToday} aria-label="Добавить вес за сегодня">
          <div>
            <div className="subtle text-[12px] mb-1">Вес</div>
            <div className="value-xl mono">{Number.isFinite(values.weight) ? `${nf(values.weight)} кг` : '—'}</div>
          </div>
          <div className="pill">{values.weightDelta || '—'}</div>
        </button>
        <button className="metric metric-btn flex items-center justify-between" onClick={onAddFatToday} aria-label="Добавить долю жира за сегодня">
          <div>
            <div className="subtle text-[12px] mb-1">Доля жира</div>
            <div className="value-xl mono">{Number.isFinite(values.fatPct) ? `~${nf(values.fatPct)}%` : '—'}</div>
          </div>
          <div className="pill">{values.fatDelta || '—'}</div>
        </button>
      </div>
    </div>
  </Card>
);

// --- Данные для графика веса/жира ---
interface WFPoint { x: string; d: string; weight: number; fat: number; }
const genWeightFat = (_days: number): WFPoint[] => [];

const WeightFatWidget: React.FC<{ initial?: WFPoint[] }> = ({ initial }) => {
  const [period, setPeriod] = useState<'week'|'month'|'q'|'year'>('month');
  const data = useMemo(() => (initial && initial.length) ? initial : [], [initial, period]);

  const hasData = data.length > 0;
  let leftDomain: [number, number] | undefined;
  let rightDomain: [number, number] | undefined;
  if (hasData) {
    const wMin = Math.min(...data.map(p => p.weight));
    const wMax = Math.max(...data.map(p => p.weight));
    const fMin = Math.min(...data.map(p => p.fat));
    const fMax = Math.max(...data.map(p => p.fat));
    leftDomain = [Math.floor(wMin), Math.ceil(wMax)];
    rightDomain = [Math.floor(fMin), Math.ceil(fMax)];
  }

  return (
    <Card
      title="Динамика веса и доли жира"
      extra={
        <div className="tabs">
          <Chip label="За неделю" active={period==='week'} onClick={() => setPeriod('week')} />
          <Chip label="За месяц" active={period==='month'} onClick={() => setPeriod('month')} />
          <Chip label="За 3 месяца" active={period==='q'} onClick={() => setPeriod('q')} />
          <Chip label="За год" active={period==='year'} onClick={() => setPeriod('year')} />
        </div>
      }
    >
      <div style={{ width: '100%', height: 220 }}>
        {hasData ? (
          <ResponsiveContainer>
            <LineChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--chart-grid)" />
              <XAxis dataKey="d" tick={{ fill: 'var(--muted)' }} interval="preserveStartEnd" />
              <YAxis yAxisId="left" orientation="left" tick={{ fill: 'var(--muted)' }} domain={leftDomain as [number, number]} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--muted)' }} domain={rightDomain as [number, number]} />
              <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: 'var(--text)' }} />
              <Legend wrapperStyle={{ color: 'var(--muted)' }} />
              <Line yAxisId="left" type="monotone" dataKey="weight" name="Вес (кг)" stroke="#a78bfa" strokeWidth={2.5} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="fat" name="Жир (%)" stroke="#38bdf8" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : null}
      </div>
    </Card>
  );
};

const CaloriesProteinWidget: React.FC<{ weekly?: { d: string; kcal: number; protein: number; }[]; calPlan?: number; protPlan?: number; }>
  = ({ weekly, calPlan, protPlan }) => {
  const CAL_PLAN = Number.isFinite(calPlan as number) && (calPlan as number) > 0 ? Number(calPlan) : 0;
  const PROT_PLAN = Number.isFinite(protPlan as number) && (protPlan as number) > 0 ? Number(protPlan) : 0; // граммы

  const series = weekly && weekly.length ? weekly : [];
  const maxK = useMemo(() => (series.length ? Math.max(...series.map(x => x.kcal), CAL_PLAN || 0) : (CAL_PLAN || 0)), [series, CAL_PLAN]);
  const maxP = useMemo(() => (series.length ? Math.max(...series.map(x => x.protein), PROT_PLAN || 0) : (PROT_PLAN || 0)), [series, PROT_PLAN]);
  const yLeftMax = useMemo(() => Math.max(0, Math.ceil(((maxK || 0) * 1.6) / 50) * 50), [maxK]);
  const yRightMax = useMemo(() => Math.max(0, Math.ceil(((maxP || 0) * 1.6) / 5) * 5), [maxP]);

  const avg = useMemo(() => {
    const ak = series.reduce((s, x) => s + x.kcal, 0) / series.length;
    const ap = series.reduce((s, x) => s + x.protein, 0) / series.length;
    return { ak, ap };
  }, [series]);

  return (
    <Card title="Потребление калорий и протеина" className="mb-3">
      <div className="chart-wrap" style={{ width: '100%', height: 240 }}>
        {series.length ? (
          <>
            <div className="chart-labels">
              {CAL_PLAN > 0 && <span className="pill">План калорий {CAL_PLAN}</span>}
              {PROT_PLAN > 0 && <span className="pill">План протеина {PROT_PLAN}</span>}
            </div>
            <ResponsiveContainer>
              <BarChart data={series} margin={{ left: 8, right: 8, top: 24, bottom: 0 }} barCategoryGap="28%">
                <CartesianGrid stroke="var(--chart-grid)" />
                <XAxis dataKey="d" tick={{ fill: 'var(--muted)' }} interval="preserveStartEnd" />
                <YAxis yAxisId="left" tick={{ fill: 'var(--muted)' }} domain={[0, yLeftMax]} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--muted)' }} domain={[0, yRightMax]} />
                <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: 'var(--text)' }} />
                <Legend wrapperStyle={{ color: 'var(--muted)' }} />
                {CAL_PLAN > 0 && <ReferenceLine yAxisId="left" y={CAL_PLAN} stroke="#a78bfa" strokeDasharray="4 4" />}
                {PROT_PLAN > 0 && <ReferenceLine yAxisId="right" y={PROT_PLAN} stroke="#38bdf8" strokeDasharray="4 4" />}
                <Bar yAxisId="left" dataKey="kcal" name="Калории" fill="#8b5cf6" radius={[6,6,0,0]} barSize={18} />
                <Bar yAxisId="right" dataKey="protein" name="Протеин (г)" fill="#22d3ee" radius={[6,6,0,0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </>
        ) : (
          <ResponsiveContainer>
            <BarChart data={[]} margin={{ left: 8, right: 8, top: 24, bottom: 0 }}>
              <CartesianGrid stroke="var(--chart-grid)" />
              <XAxis dataKey="d" tick={{ fill: 'var(--muted)' }} />
              <YAxis yAxisId="left" tick={{ fill: 'var(--muted)' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--muted)' }} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      {series.length ? (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="glass p-3 rounded-lg">
            <div className="subtle text-sm">Среднедневное за 7 дней (ккал)</div>
            <div className="mono text-lg">{nf(avg.ak)}</div>
          </div>
          <div className="glass p-3 rounded-lg">
            <div className="subtle text-sm">Среднедневное за 7 дней (протеин, г)</div>
            <div className="mono text-lg">{nf(avg.ap)}</div>
          </div>
        </div>
      ) : null}
    </Card>
  );
};

interface Food { name: string; kcal: number; protein?: number; weight?: number; mealId?: number; itemId?: number; unit?: string; fat_g?: number; carb_g?: number; }

const FoodListWidget: React.FC<{
  dateISO: string;
  foods: Food[];
  onPrev: () => void;
  onNext: () => void;
  onPickDate: () => void;
  onEdit: (i: number) => void;
  onDelete: (i: number) => void;
  onItemClick: (i: number) => void;
}> = ({ dateISO, foods, onPrev, onNext, onPickDate, onEdit, onDelete, onItemClick }) => (
  <Card
    title="Дневник"
    extra={
      <div className="flex items-center gap-2">
        <button className="tab" aria-label="Предыдущий день" onClick={onPrev}><ChevronLeft size={16} /></button>
        <button className="pill" onClick={onPickDate} aria-label="Выбрать дату">
          <Calendar size={14} /> {fmtDateRU(dateISO)}
        </button>
        <button className="tab" aria-label="Следующий день" onClick={onNext}><ChevronRight size={16} /></button>
      </div>
    }
    className="minh-360"
  >
    <div className="space-y-2">
      {foods.map((f, i) => (
        <div key={i} className="row-grid gap-2 items-center py-2 px-2 rounded-md">
          <button className="text-left truncate pr-3" title={f.name} onClick={() => onItemClick(i)} aria-label={`Изменить ${f.name}`}>
            {f.name}
          </button>
          <div className="mono mr-1">{nf(f.kcal)}{'\u00A0'}ккал</div>
          <div className="flex items-center gap-1">
            <button className="tab" aria-label={`Изменить ${f.name}`} onClick={() => onEdit(i)}><Pencil size={16} /></button>
            <button className="tab" aria-label={`Удалить ${f.name}`} onClick={() => onDelete(i)}><Trash2 size={16} /></button>
          </div>
        </div>
      ))}
    </div>
  </Card>
);

const MainButtonDock: React.FC<{ state: 'default'|'disabled'|'loading', label: string, onClick?: () => void }>
  = ({ state, label, onClick }) => (
  <div
    className="px-3 pt-3 main-gradient"
    role="region"
    aria-label="MainButton dock"
    style={{ position: 'fixed', left: 0, right: 0, bottom: 0, paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 12px)', zIndex: 40 }}
  >
    <button
      className="btn btn-primary w-full shadow-xl flex items-center justify-center gap-2"
      disabled={state !== 'default'}
      aria-busy={state === 'loading'}
      aria-disabled={state === 'disabled'}
      onClick={onClick}
    >
      {state === 'loading' && <Loader2 className="animate-spin" size={18} />}
      <span>{label}</span>
    </button>
  </div>
);

// --- Helpers & tests ---
const normalizeSpaces = (s: string) => s.replace(/\u00A0|\u202F/g, ' ').replace(/\s+/g, ' ').trim();
const makeMainButtonLabel = (kcal: number) => `Сегодня: ${kcal} ккал`;
const toISODateLocal = (d: Date): string => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};
const parseISODateLocal = (iso: string): Date => {
  const [y, m, d] = (iso || '').split('-').map(n => parseInt(n, 10));
  return new Date((y||1970), ((m||1) - 1), (d||1), 0, 0, 0, 0);
};
const todayISO = (): string => toISODateLocal(new Date());
const fmtDateRU = (iso: string): string => {
  if (!iso) return '';
  const d = parseISODateLocal(iso);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}.${mm}.${yyyy}`;
};
const makeRangeLabel = (startISO: string, endISO: string): string => `${fmtDateRU(startISO)} – ${fmtDateRU(endISO)}`;
const isInvalidRange = (startISO: string, endISO: string): boolean => !endISO || (startISO && endISO < startISO);
const deltaLabel = (prev: number, curr: number): string => {
  if (!isFinite(prev) || prev === 0 || !isFinite(curr)) return '0%';
  const pct = ((curr - prev) / prev) * 100;
  const r = Math.round(pct);
  return `${r > 0 ? '+' : ''}${r}%`;
};
const log10 = (x: number) => (Math.log10 ? Math.log10(x) : Math.log(x) / Math.LN10);
// Body fat
export type Gender = 'male' | 'female' | 'other';
const parseNum = (s: string): number => Number(String(s ?? '').replace(',', '.'));
const computeBodyFat = (
  gender: Gender,
  heightCm: number,
  weightKg: number,
  waistCm: number,
  neckCm: number
): number | null => {
  const height_in = heightCm / 2.54;
  const waist_in = waistCm / 2.54;
  const neck_in = neckCm / 2.54;
  const weight_lb = weightKg * 2.2046226218;
  if (!isFinite(height_in) || height_in <= 0) return null;
  if (gender === 'female') {
    if (!isFinite(waist_in) || !isFinite(weight_lb) || waist_in <= 0 || weight_lb <= 0) return null;
    const bf = ((waist_in * 4.15) - (weight_lb * 0.082) - 76.76) / weight_lb * 100;
    return isFinite(bf) ? bf : null;
  }
  // male / other
  if (!isFinite(waist_in - neck_in) || (waist_in - neck_in) <= 0) return null;
  const bf = 86.010 * log10(waist_in - neck_in) - 70.041 * log10(height_in) + 36.76;
  return isFinite(bf) ? bf : null;
};
const approx = (a: number, b: number, eps = 1) => Math.abs(a - b) <= eps;
// Date helper used by diary navigation and tests (UTC-based, стабильный)
const shiftDateISO = (iso: string, days: number): string => {
  const d = parseISODateLocal(iso);
  d.setDate(d.getDate() + days);
  return toISODateLocal(d);
};

// --- Minimal self-tests ---
type TestResult = { name: string; ok: boolean; details?: string };
const runTests = (): TestResult[] => {
  const results: TestResult[] = [];
  results.push({ name: 'foods structure', ok: foods.every(f => typeof f.name === 'string' && typeof f.kcal === 'number' && f.kcal >= 0) });
  results.push({ name: 'last7 length & numbers', ok: last7.length === 7 && last7.every(x => typeof x.kcal === 'number' && typeof x.protein === 'number') });
  const expectedK = 3278; const calcK = foods.reduce((s,f) => s + f.kcal, 0); results.push({ name: 'today kcal sum', ok: calcK === expectedK, details: `calc=${calcK} expected=${expectedK}` });
  const label = makeMainButtonLabel(calcK);
  results.push({ name: 'main button label format', ok: normalizeSpaces(label) === normalizeSpaces(`Сегодня: ${expectedK} ккал`), details: label });
  results.push({ name: 'goal presets default label', ok: `${GOAL_PRESETS.loss.title} (${GOAL_PRESETS.loss.note})` === 'Снижение веса (дефицит калорий)' });
  results.push({ name: 'infer goal mode', ok: inferGoalMode('Поддержание веса', 'после снижения веса') === 'maint' && inferGoalMode('Рост мышечной массы', '') === 'gain' && inferGoalMode('Без цели по весу', 'контроль потребления') === 'nocw' });
  results.push({ name: 'date range label ru', ok: makeRangeLabel('2025-05-19','2025-08-18') === '19 мая 2025 – 18 августа 2025' });
  results.push({ name: 'invalid range detection', ok: isInvalidRange('2025-05-19','') && isInvalidRange('2025-05-19','2025-05-18') && !isInvalidRange('2025-05-19','2025-05-20') });
  results.push({ name: 'wf series lengths', ok: genWeightFat(7).length===7 && genWeightFat(30).length===30 && genWeightFat(90).length===90 && genWeightFat(365).length===365 });
  results.push({ name: 'wf last is today', ok: genWeightFat(7).slice(-1)[0].x === todayISO() });
  results.push({ name: 'deltaLabel weight -5%', ok: deltaLabel(71.6, 68) === '-5%' });
  results.push({ name: 'deltaLabel fat -5%', ok: deltaLabel(26.3, 25) === '-5%' });
  results.push({ name: 'bf male example', ok: (() => { const m = computeBodyFat('male', 175, 70, 80, 38); return m !== null && approx(m, 13, 1.6); })() });
  results.push({ name: 'bf female example', ok: (() => { const f = computeBodyFat('female', 165, 60, 70, 34); return f !== null && approx(f, 20.2, 2); })() });
  results.push({ name: 'shiftDateISO +1 day', ok: shiftDateISO('2025-04-25', 1) === '2025-04-26' });
  results.push({ name: 'shiftDateISO -1 day', ok: shiftDateISO('2025-04-25', -1) === '2025-04-24' });
  return results;
};

function DevTests() {
  const [tests, setTests] = useState<TestResult[]>([]);
  useEffect(() => { setTests(runTests()); }, []);
  const passed = tests.filter(t => t.ok).length;
  return (
    <div className="subtle text-xs mt-4">
      <details>
        <summary>Dev • Tests: {passed}/{tests.length} passed</summary>
        <ul className="mt-2 list-disc pl-6">
          {tests.map((t, i) => (
            <li key={i} className={t.ok ? 'text-green-400' : 'text-red-400'}>
              {t.name} — {t.ok ? 'OK' : 'FAIL'} {t.details ? `(${t.details})` : ''}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

export default function TelegramWebAppMainMockup() {
  const [mbState, setMbState] = useState<'default'|'disabled'|'loading'>('default');
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(true);
  

  // Верхние плитки — начально пустые значения
  const [goalTitle, setGoalTitle] = useState<string>('—');
  const [goalNote, setGoalNote] = useState<string>('');
  const [dateRange, setDateRange] = useState<string>('');
  const [calPlan, setCalPlan] = useState<number>(NaN);
  const [protPlan, setProtPlan] = useState<number>(NaN);
  const [weight, setWeight] = useState<number>(NaN);
  const [weightDelta, setWeightDelta] = useState<string>('—');
  const [fatPct, setFatPct] = useState<number>(NaN);
  const [fatDelta, setFatDelta] = useState<string>('—');
  const [weightsByDate, setWeightsByDate] = useState<Record<string, number>>({});
  const [fatByDate, setFatByDate] = useState<Record<string, number>>({});

  // Загрузка сохранённых значений из localStorage
  useEffect(() => {
    try {
      const gt = localStorage.getItem('profile.goalTitle'); if (gt) setGoalTitle(gt);
      const gn = localStorage.getItem('profile.goalNote'); if (gn !== null) setGoalNote(gn);
      const dr = localStorage.getItem('profile.dateRange'); if (dr !== null) setDateRange(dr);
      const cp = localStorage.getItem('profile.calPlan'); if (cp) setCalPlan(Number(cp));
      const pp = localStorage.getItem('profile.protPlan'); if (pp) setProtPlan(Number(pp));
      const wb = localStorage.getItem('profile.weightsByDate'); if (wb) setWeightsByDate(JSON.parse(wb));
      const fb = localStorage.getItem('profile.fatByDate'); if (fb) setFatByDate(JSON.parse(fb));
    } catch {}
  }, []);
  // Вывод актуальных веса/жира и дельт из карт по датам
  useEffect(() => {
    const derive = (map: Record<string, number>) => {
      const dates = Object.keys(map).sort();
      const last = dates.length ? map[dates[dates.length - 1]] : NaN;
      const prev = dates.length > 1 ? map[dates[dates.length - 2]] : NaN;
      return { last, prev };
    };
    const w = derive(weightsByDate);
    setWeight(Number.isFinite(w.last) ? w.last : NaN);
    setWeightDelta(Number.isFinite(w.prev) && Number.isFinite(w.last) ? deltaLabel(w.prev, w.last) : '—');
    const f = derive(fatByDate);
    setFatPct(Number.isFinite(f.last) ? f.last : NaN);
    setFatDelta(Number.isFinite(f.prev) && Number.isFinite(f.last) ? deltaLabel(f.prev, f.last) : '—');
  }, [weightsByDate, fatByDate]);
  const [goalMode, setGoalMode] = useState<'loss'|'maint'|'gain'|'nocw'>(() => inferGoalMode(goalTitle, goalNote));

  // Модалки
  const [modal, setModal] = useState<{ type: null | 'goal' | 'cal' | 'prot' | 'weight' | 'fat' | 'food-edit' | 'food-del' | 'diary-date' }>({ type: null });
  const close = () => setModal({ type: null });

  // Поля модалок
  const [tmpText1, setTmpText1] = useState('');
  const [tmpStartISO, setTmpStartISO] = useState<string>(todayISO());
  const [tmpEndISO, setTmpEndISO] = useState<string>('');
  const [tmpGender, setTmpGender] = useState<'male'|'female'|'other'>(() => {
    try {
      const v = localStorage.getItem('prefs.bf.gender');
      if (v === 'male' || v === 'female' || v === 'other') return v as 'male'|'female'|'other';
    } catch {}
    return 'male';
  });
  const [tmpHeightCm, setTmpHeightCm] = useState<string>(() => {
    try {
      const v = localStorage.getItem('prefs.bf.height_cm');
      if (v && String(v).length > 0) return String(v);
    } catch {}
    return '';
  });
  const [tmpWeightKg, setTmpWeightKg] = useState<string>(String(weight));
  const [tmpWaistCm, setTmpWaistCm] = useState<string>('');
  const [tmpNeckCm, setTmpNeckCm] = useState<string>('');

  const openGoal = () => { setGoalMode(inferGoalMode(goalTitle, goalNote)); setTmpStartISO(todayISO()); setTmpEndISO(''); setModal({ type: 'goal' }); };
  const saveGoal = () => {
    const p = GOAL_PRESETS[goalMode];
    setGoalTitle(p.title);
    setGoalNote(p.note);
    // allow empty dates (open interval) and auto-format label
    let range = '';
    const hasStart = !!tmpStartISO;
    const hasEnd = !!tmpEndISO;
    if (hasStart && hasEnd) {
      if (isInvalidRange(tmpStartISO, tmpEndISO)) return; // invalid end
      range = makeRangeLabel(tmpStartISO, tmpEndISO);
    } else if (hasStart) {
      range = `с ${fmtDateRU(tmpStartISO)}`;
    } // если указан только конец — не отображаем
    setDateRange(range);
    // persist & сброс планов калорий/протеина
    try {
      localStorage.setItem('profile.goalTitle', p.title);
      localStorage.setItem('profile.goalNote', p.note);
      localStorage.setItem('profile.dateRange', range);
      setCalPlan(NaN); setProtPlan(NaN);
      localStorage.removeItem('profile.calPlan');
      localStorage.removeItem('profile.protPlan');
    } catch {}
    // Trigger Telegram notification with strategy video (best-effort, без всплывающих предупреждений)
    try {
      const tgId = getTelegramId();
      if (tgId) {
        const mode = goalMode === 'loss' ? 'loss' : (goalMode === 'maint' ? 'maint' : (goalMode === 'gain' ? 'gain' : 'nocw'));
        apiFetch(`/api/goal-notify?telegram_id=${tgId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode }) }).catch(()=>{});
      }
    } catch {}
    close();
  };

  const openCal = () => { setTmpText1(String(calPlan)); setModal({ type: 'cal' }); };
  const saveCal = () => { const v = parseInt(tmpText1, 10); if (!Number.isNaN(v) && v > 0) { setCalPlan(v); try { localStorage.setItem('profile.calPlan', String(v)); } catch {} } close(); };

  const openProt = () => { setTmpText1(String(protPlan)); setModal({ type: 'prot' }); };
  const saveProt = () => { const v = parseInt(tmpText1, 10); if (!Number.isNaN(v) && v > 0) { setProtPlan(v); try { localStorage.setItem('profile.protPlan', String(v)); } catch {} } close(); };

  const openWeight = () => { setTmpText1(String(weight)); setModal({ type: 'weight' }); };
  const saveWeight = async () => {
    const v = Number(tmpText1);
    if (!Number.isNaN(v) && v > 0) {
      const d = todayISO();
      setWeightsByDate(m => { const nm = { ...m, [d]: v }; try { localStorage.setItem('profile.weightsByDate', JSON.stringify(nm)); } catch {} return nm; });
      // send to server
      const tgId = getTelegramId();
      if (tgId) {
        try {
          await apiFetch(`/api/weights?telegram_id=${tgId}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: d, weight_kg: v })
          });
        } catch {}
      }
    }
    close();
    // refresh charts after slight delay
    setTimeout(() => { fetchAll(); }, 50);
  };

  const openFat = () => {
    try {
      const g = localStorage.getItem('prefs.bf.gender');
      if (g === 'male' || g === 'female' || g === 'other') setTmpGender(g as 'male'|'female'|'other');
      else setTmpGender('male');
    } catch { setTmpGender('male'); }
    try {
      const h = localStorage.getItem('prefs.bf.height_cm');
      setTmpHeightCm(h && h.length ? h : '');
    } catch { setTmpHeightCm(''); }
    setTmpWeightKg(String(weight));
    setTmpWaistCm('');
    setTmpNeckCm('');
    setModal({ type: 'fat' });
  };
  const saveFat = async () => {
    const bf = computeBodyFat(tmpGender, parseNum(tmpHeightCm), parseNum(tmpWeightKg), parseNum(tmpWaistCm), parseNum(tmpNeckCm));
    if (bf != null && isFinite(bf) && bf >= 0) {
      const val = Math.round(bf * 10) / 10;
      const d = todayISO();
      setFatByDate(m => { const nm = { ...m, [d]: val }; try { localStorage.setItem('profile.fatByDate', JSON.stringify(nm)); } catch {} return nm; });
      // persist user prefs locally for next time
      try {
        localStorage.setItem('prefs.bf.gender', tmpGender);
        const h = String(tmpHeightCm || '');
        if (h && Number(parseNum(h)) > 0) localStorage.setItem('prefs.bf.height_cm', h);
      } catch {}
      // send to server
      const tgId = getTelegramId();
      if (tgId) {
        const today = todayISO();
        try {
          await apiFetch(`/api/bodyfat?telegram_id=${tgId}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: today, percent: val })
          });
        } catch {}
      }
    }
    close();
    setTimeout(() => { fetchAll(); }, 50);
  };

  // Дневник (стабильная версия: один список, дата для навигации)
  const [diaryDateISO, setDiaryDateISO] = useState<string>(todayISO());
  const [foodList, setFoodList] = useState<Food[]>([]);
  const [kcalTodayTotal, setKcalTodayTotal] = useState<number>(0);
  const diaryRef = useRef<HTMLDivElement | null>(null);
  const openDiaryDate = () => { setTmpStartISO(diaryDateISO); setModal({ type: 'diary-date' }); };
  const saveDiaryDate = () => { if (tmpStartISO) setDiaryDateISO(tmpStartISO); close(); };

  // CRUD блюд
  const [editIndex, setEditIndex] = useState<number>(-1);
  const [tmpFoodName, setTmpFoodName] = useState<string>('');
  const [tmpFoodWeight, setTmpFoodWeight] = useState<string>('0');
  const [tmpFoodProtein, setTmpFoodProtein] = useState<string>('0');
  const [tmpFoodKcal, setTmpFoodKcal] = useState<string>('0');
  const [tmpFoodFat, setTmpFoodFat] = useState<string>('0');
  const [tmpFoodCarb, setTmpFoodCarb] = useState<string>('0');
  const openFoodEdit = (i: number) => { const f = foodList[i]; if (!f) return; setEditIndex(i); setTmpFoodName(f.name); setTmpFoodWeight(String(f.weight ?? 0)); setTmpFoodProtein(String(f.protein ?? 0)); setTmpFoodKcal(String(f.kcal)); setTmpFoodFat(String(f.fat_g ?? 0)); setTmpFoodCarb(String(f.carb_g ?? 0)); setModal({ type: 'food-edit' }); };
  const saveFoodEdit = async () => {
    if (editIndex < 0) return close();
    const edited = foodList[editIndex];
    if (!edited?.mealId) { close(); return; }
    const tgId = getTelegramId();
    if (!tgId) { close(); return; }
    const updatedItem: Food = {
      ...edited,
      name: tmpFoodName.trim() || edited.name,
      weight: Number(tmpFoodWeight)||0,
      protein: Number(tmpFoodProtein)||0,
      kcal: Number(tmpFoodKcal)||Number(edited.kcal||0),
      fat_g: Number(tmpFoodFat)||0,
      carb_g: Number(tmpFoodCarb)||0,
    };
    const itemsForMeal = foodList.filter(x => x.mealId === edited.mealId).map(x => ({
      name: x === edited ? updatedItem.name : x.name,
      unit: x.unit || 'g',
      amount: x === edited ? (updatedItem.weight||0) : (x.weight||0),
      kcal: x === edited ? (updatedItem.kcal||0) : (x.kcal||0),
      protein_g: x === edited ? (updatedItem.protein||0) : (x.protein||0),
      fat_g: x === edited ? (updatedItem.fat_g||0) : (x.fat_g||0),
      carb_g: x === edited ? (updatedItem.carb_g||0) : (x.carb_g||0),
    }));
    await apiFetch(`/api/meals/${edited.mealId}?telegram_id=${tgId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items: itemsForMeal }) });
    close();
    await fetchAll();
  };
  const [deleteIndex, setDeleteIndex] = useState<number>(-1);
  const openFoodDelete = (i: number) => { setDeleteIndex(i); setModal({ type: 'food-del' }); };
  const confirmFoodDelete = async () => {
    if (deleteIndex<0) { close(); return; }
    const del = foodList[deleteIndex];
    if (!del?.mealId) { close(); return; }
    const tgId = getTelegramId();
    if (!tgId) { close(); return; }
    const remaining = foodList.filter(x => x.mealId === del.mealId && x.itemId !== del.itemId);
    if (remaining.length === 0) {
      await apiFetch(`/api/meals/${del.mealId}?telegram_id=${tgId}`, { method: 'DELETE' });
    } else {
      const items = remaining.map(x => ({ name: x.name, unit: x.unit || 'g', amount: x.weight||0, kcal: x.kcal||0, protein_g: x.protein||0, fat_g: x.fat_g||0, carb_g: x.carb_g||0 }));
      await apiFetch(`/api/meals/${del.mealId}?telegram_id=${tgId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) });
    }
    close();
    await fetchAll();
  };

  const values = { goalTitle, goalNote, dateRange, calPlan, protPlan, weight, weightDelta, fatPct, fatDelta };
  const mainButtonLabel = makeMainButtonLabel(Math.round(kcalTodayTotal));

  // Backend integrations: load weekly summary and meals
  const [weeklySeries, setWeeklySeries] = useState<{ d: string; kcal: number; protein: number }[] | null>(null);
  const [weeklyCompliance, setWeeklyCompliance] = useState<number | null>(null);
  const [weightPace, setWeightPace] = useState<number | null>(null);
  const [wfSeries, setWfSeries] = useState<WFPoint[] | null>(null);
  const [periodFilter, setPeriodFilter] = useState<'week'|'month'|'q'|'year'>('week');
  const [tz, setTz] = useState<string>(() => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  // Settings state
  const [settings, setSettings] = useState<{ specialist_id?: string; timezone?: string; locale?: string; preferred_units?: 'metric'|'imperial'; notify_enabled?: boolean; notify_times?: string[]; newsletter_opt_in?: boolean; } | null>(null);
  const [tmpSpecialist, setTmpSpecialist] = useState<string>('');
  const [tmpTimezone, setTmpTimezone] = useState<string>(() => Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Madrid');
  const [tmpLocale, setTmpLocale] = useState<string>('ru');
  const [tmpUnits, setTmpUnits] = useState<'metric'|'imperial'>('metric');
  const [tmpNotifyEnabled, setTmpNotifyEnabled] = useState<boolean>(false);
  const [tmpNotifyTimes, setTmpNotifyTimes] = useState<string[]>([]);
  const [tmpNewsOptIn, setTmpNewsOptIn] = useState<boolean>(false);

  useEffect(() => {
    // Accessibility: set document title
    document.title = 'Ultima Calories — Дневник';
    // Telegram affordances
    try {
      const tg: any = (window as any).Telegram?.WebApp;
      if (tg?.ready) tg.ready();
      if (tg?.expand) tg.expand();
    } catch {}
  }, []);

  // Debug overlay (temporary) — shows tgId and basic fetch statuses
  const [dbg, setDbg] = useState<{ tgId: number | null; weekly: string; weights: string; bodyfat: string; meals: string } | null>(null);

  const fetchAll = useCallback(async () => {
      try {
        setMbState('loading');
        const tgId = getTelegramId();
        if (!tgId) { setLoading(false); return; }
        let anyOk = false;
        // Weekly summary: use /api/summary/weekly to derive bars; optionally fetch /api/weights for WF graph later
        const today = new Date();
        const daySpan = periodFilter==='week' ? 6 : (periodFilter==='month' ? 29 : (periodFilter==='q' ? 89 : 364));
        // Use local date, not UTC toISOString, to avoid shifting window and losing today in CEST
        const start = toISODateLocal(new Date(today.getFullYear(), today.getMonth(), today.getDate() - daySpan));
        const r1 = await apiFetch(`/api/summary/weekly?telegram_id=${tgId}&start=${start}&tz=${encodeURIComponent(tz)}&no_cache=1&_=${Date.now()}`);
        const b1 = await r1.json();
        let weeklySer: { d: string; kcal: number; protein: number }[] = [];
        if (b1?.ok && Array.isArray(b1?.data?.items)) {
          const items = b1.data.items as { date: string; kcal: number; protein_g: number }[];
          weeklySer = items.map(it => ({ d: it.date.slice(5), kcal: Number(it.kcal||0), protein: Number(it.protein_g||0) }));
          setWeeklyCompliance((b1.data.compliance && b1.data.compliance.score) || null);
          setWeightPace((b1.data.weight_pace_kg_per_week != null) ? Number(b1.data.weight_pace_kg_per_week) : null);
          anyOk = true;
        }
        // Weights
        const r3 = await apiFetch(`/api/weights?telegram_id=${tgId}&start=${start}&_=${Date.now()}`);
        const b3 = await r3.json();
        let wf: WFPoint[] = [];
        if (b3?.ok && Array.isArray(b3?.data?.items)) {
          const items = b3.data.items as { date: string; weight_kg: number }[];
          wf = items.map((it) => ({ x: it.date, d: it.date.slice(5), weight: Number(it.weight_kg||0), fat: Number.NaN }));
          anyOk = true;
        }
        // Bodyfat (optional)
        try {
          const bfRes = await apiFetch(`/api/bodyfat?telegram_id=${tgId}&start=${start}&_=${Date.now()}`);
          const bf = await bfRes.json();
          if (bf?.ok && Array.isArray(bf?.data?.items) && wf.length) {
            const map: Record<string, number> = {};
            (bf.data.items as { date: string; percent: number }[]).forEach(it => { map[it.date] = Number(it.percent||0) });
            wf = wf.map(p => ({ ...p, fat: (map[p.x] != null ? Number(map[p.x]) : Number.NaN) as unknown as number }));
            anyOk = true;
          }
        } catch {}
        setWfSeries(wf);
        // Meals for selected date
        const r2 = await apiFetch(`/api/meals?telegram_id=${tgId}&date=${diaryDateISO}&tz=${encodeURIComponent(tz)}&_=${Date.now()}`);
        const b2 = await r2.json();
        if (b2?.ok && Array.isArray(b2?.data?.items)) {
          const meals = b2.data.items as any[];
          const list: Food[] = [];
          meals.forEach((m: any) => {
            (m.items || []).forEach((it: any) => list.push({ name: it.name, kcal: Number(it.kcal||0), protein: Number(it.protein_g||0), weight: Number(it.amount||0), mealId: m.id, itemId: it.id, unit: it.unit || 'g', fat_g: Number(it.fat_g||0), carb_g: Number(it.carb_g||0) }));
          });
          setFoodList(list);
          anyOk = true;
          // fallback для графика потребления, если weekly пуст
          const dayK = list.reduce((s, x) => s + (Number(x.kcal)||0), 0);
          const dayP = list.reduce((s, x) => s + (Number(x.protein)||0), 0);
          const hasWeekly = weeklySer.length > 0 && weeklySer.some(x => x.kcal > 0 || x.protein > 0);
          const todayIso = todayISO();
          const todayKey = todayIso.slice(5);
          // Если weekly уже есть, но нет колонки за сегодня — добавим её из дневника
          if (hasWeekly) {
            const hasToday = weeklySer.some(x => x.d === todayKey);
            if (!hasToday && diaryDateISO === todayIso && (dayK > 0 || dayP > 0)) {
              weeklySer = [...weeklySer, { d: todayKey, kcal: dayK, protein: dayP }]
                .sort((a,b) => a.d.localeCompare(b.d));
            }
          } else if (dayK > 0 || dayP > 0) {
            weeklySer = [{ d: diaryDateISO.slice(5), kcal: dayK, protein: dayP }];
          }
        } else {
          setFoodList([]);
        }
        setWeeklySeries(weeklySer);
        // Today kcal for bottom button (from server summary, fallback to local if current day is open)
        try {
          const todayIso = todayISO();
          const rs = await apiFetch(`/api/summary/daily?telegram_id=${tgId}&date=${todayIso}&tz=${encodeURIComponent(tz)}&no_cache=1&_=${Date.now()}`);
          const bs = await rs.json();
          if (bs?.ok && bs?.data?.consumed) {
            setKcalTodayTotal(Number(bs.data.consumed.kcal || 0));
            anyOk = true;
          } else if (diaryDateISO === todayIso) {
            setKcalTodayTotal((foodList || []).reduce((s, f) => s + (Number(f.kcal) || 0), 0));
          }
        } catch {
          const todayIso = todayISO();
          if (diaryDateISO === todayIso) {
            setKcalTodayTotal((foodList || []).reduce((s, f) => s + (Number(f.kcal) || 0), 0));
          }
        }
        setOffline(!anyOk && navigator.onLine === false ? true : false);
        setDbg({ tgId, weekly: b1?.ok ? 'ok' : 'fail', weights: b3?.ok ? 'ok' : 'fail', bodyfat: (typeof (window as any).__bfok !== 'undefined') ? String((window as any).__bfok) : (b3?.ok ? 'ok' : 'fail'), meals: b2?.ok ? 'ok' : 'fail' });
      } catch {
        setOffline(true);
      } finally {
        setLoading(false);
        setMbState('default');
      }
    }, [diaryDateISO, periodFilter, tz]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Load settings
  useEffect(() => {
    (async () => {
      try {
        const tgId = getTelegramId(); if (!tgId) return;
        const r = await apiFetch(`/api/settings?telegram_id=${tgId}&_=${Date.now()}`);
        const b = await r.json();
        if (b?.ok && b?.data) {
          setSettings(b.data);
          setTmpSpecialist(String(b.data.specialist_id || ''));
          if (b.data.timezone) setTmpTimezone(String(b.data.timezone));
          if (b.data.locale) setTmpLocale(String(b.data.locale));
          if (b.data.preferred_units) setTmpUnits(b.data.preferred_units);
          if (typeof b.data.notify_enabled === 'boolean') setTmpNotifyEnabled(!!b.data.notify_enabled);
          if (Array.isArray(b.data.notify_times)) setTmpNotifyTimes(b.data.notify_times);
          if (typeof b.data.newsletter_opt_in === 'boolean') setTmpNewsOptIn(!!b.data.newsletter_opt_in);
        }
      } catch {}
    })();
  }, []);

  return (
    <div className="container px-3">
      <RootStyles />

      {/* Debug overlay */}
      {(() => { try { const usp = new URLSearchParams(window.location.search); if (usp.get('debug') === '1' && dbg) { return (
        <div className="card p-3 mb-3" style={{borderLeft: '4px solid #38bdf8'}}>
          <div className="h2 mb-1">Debug</div>
          <div className="mono text-sm">tgId: {String(dbg.tgId)}</div>
          <div className="mono text-sm">weekly: {dbg.weekly} • weights: {dbg.weights} • bodyfat: {dbg.bodyfat} • meals: {dbg.meals}</div>
        </div>
      ); } } catch {} return null; })()}

      {offline && (
        <div className="card p-3 mb-3 border-l-4" style={{ borderLeftColor: 'var(--warn)' }} role="status">
          <div className="flex items-center gap-2"><span className="h2">Нет подключения</span></div>
          <div className="subtle">Проверьте сеть. Данные могут быть неактуальны.</div>
        </div>
      )}

      {/* Контентная сетка */}
      <div className="grid-desktop gap-3">
        {/* Левая колонка */}
        <div className="space-y-3">
          {loading ? (
            <div className="card p-4">
              <div className="skeleton h-5 w-48 mb-4 rounded"></div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Array.from({ length: 5 }).map((_,i) => (
                  <div key={i} className="skeleton h-6 rounded"></div>
                ))}
              </div>
            </div>
          ) : (
            <MainInfo
              values={values}
              onEditGoal={openGoal}
              onEditCalories={openCal}
              onEditProtein={openProt}
              onAddWeightToday={openWeight}
              onAddFatToday={openFat}
            />
          )}

          {loading ? (
            <div className="card p-4">
              <div className="skeleton h-5 w-64 mb-3 rounded"></div>
              <div className="skeleton h-[220px] rounded"></div>
            </div>
          ) : <WeightFatWidget initial={wfSeries || undefined} />}

          {loading ? (
            <div className="card p-4">
              <div className="skeleton h-5 w-72 mb-3 rounded"></div>
              <div className="skeleton h-[240px] rounded"></div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="skeleton h-16 rounded"></div>
                <div className="skeleton h-16 rounded"></div>
              </div>
            </div>
          ) : <CaloriesProteinWidget weekly={weeklySeries || undefined} calPlan={Number.isFinite(calPlan)?calPlan:undefined} protPlan={Number.isFinite(protPlan)?protPlan:undefined} />}
        </div>

        {/* Правая колонка */}
        <div className="space-y-3">
          {loading ? (
            <div className="card p-4 min-h-[360px]">
              <div className="skeleton h-5 w-80 mb-3 rounded"></div>
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="skeleton h-10 rounded mb-2"></div>
              ))}
            </div>
          ) : (
            <div ref={diaryRef}>
              <FoodListWidget
                dateISO={diaryDateISO}
                foods={foodList}
                onPrev={() => setDiaryDateISO(d => shiftDateISO(d, -1))}
                onNext={() => setDiaryDateISO(d => shiftDateISO(d, +1))}
                onPickDate={openDiaryDate}
                onEdit={openFoodEdit}
                onDelete={openFoodDelete}
                onItemClick={openFoodEdit}
              />
            </div>
          )}
        </div>
      </div>

      {/* Настройки */}
      <div className="card p-4 mt-3" id="settings">
        <div className="flex items-center justify-between">
          <div className="h2">Настройки</div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
          <div className="field">
            <label className="subtle text-sm">ID специалиста</label>
            <input className="input" type="text" value={tmpSpecialist} onChange={e=>setTmpSpecialist(e.target.value)} placeholder="например: coach_123" />
          </div>
          <div className="field">
            <label className="subtle text-sm">Часовой пояс</label>
            <input className="input" type="text" value={tmpTimezone} onChange={e=>setTmpTimezone(e.target.value)} placeholder="Europe/Madrid" />
          </div>
          <div className="field">
            <label className="subtle text-sm">Локаль</label>
            <select className="input" value={tmpLocale} onChange={e=>setTmpLocale(e.target.value)}>
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </div>
          <div className="field">
            <label className="subtle text-sm">Единицы</label>
            <select className="input" value={tmpUnits} onChange={e=>setTmpUnits(e.target.value as any)}>
              <option value="metric">Метрические (кг, см, мл)</option>
              <option value="imperial">Имперские (lb, in, fl oz)</option>
            </select>
          </div>
          <div className="field">
            <label className="subtle text-sm">Уведомления</label>
            <div className="flex items-center gap-2 mt-1">
              <input type="checkbox" checked={tmpNotifyEnabled} onChange={e=>setTmpNotifyEnabled(e.target.checked)} />
              <span>включить</span>
            </div>
          </div>
          <div className="field">
            <label className="subtle text-sm">Время уведомлений (чч:мм, через запятую)</label>
            <input className="input" type="text" value={tmpNotifyTimes.join(', ')} onChange={e=>setTmpNotifyTimes(e.target.value.split(',').map(s=>s.trim()).filter(Boolean))} placeholder="09:00, 13:00, 20:30" />
          </div>
          <div className="field">
            <label className="subtle text-sm">Рассылки / новости</label>
            <div className="flex items-center gap-2 mt-1">
              <input type="checkbox" checked={tmpNewsOptIn} onChange={e=>setTmpNewsOptIn(e.target.checked)} />
              <span>получать полезные материалы</span>
            </div>
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <button className="btn" onClick={async ()=>{
            try { const tgId = getTelegramId(); if (!tgId) return; 
              await apiFetch(`/api/settings?telegram_id=${tgId}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ specialist_id: tmpSpecialist || null, timezone: tmpTimezone, locale: tmpLocale, preferred_units: tmpUnits, notify_enabled: tmpNotifyEnabled, notify_times: tmpNotifyTimes, newsletter_opt_in: tmpNewsOptIn }) });
            } catch {}
          }}>Сохранить</button>
          <button className="btn ghost" onClick={()=>{ setTmpSpecialist(String(settings?.specialist_id || '')); }}>Отменить</button>
        </div>
      </div>

      {/* Нижний док с MainButton */}
      <MainButtonDock
        state={mbState}
        label={mainButtonLabel}
        onClick={() => diaryRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
      />

      {/* Модалки */}
      <div aria-live="polite">
        {modal.type === 'goal' && (
          <Modal
            title="Изменить цель"
            onClose={close}
            onSave={saveGoal}
            saveDisabled={isInvalidRange(tmpStartISO, tmpEndISO)}
          >
            <div className="field" role="radiogroup" aria-label="Выбор цели">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="goal" checked={goalMode==='loss'} onChange={() => setGoalMode('loss')} />
                <span>Снижение веса (дефицит калорий)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="goal" checked={goalMode==='maint'} onChange={() => setGoalMode('maint')} />
                <span>Поддержание веса (после снижения веса)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="goal" checked={goalMode==='gain'} onChange={() => setGoalMode('gain')} />
                <span>Рост мышечной массы</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="goal" checked={goalMode==='nocw'} onChange={() => setGoalMode('nocw')} />
                <span>Без цели по весу (контроль потребления)</span>
              </label>
            </div>

            <div className="field">
              <label className="subtle text-sm">Дата начала</label>
              <input className="input" type="date" value={tmpStartISO} onChange={e => setTmpStartISO(e.target.value)} />
            </div>
            <div className="field">
              <label className="subtle text-sm">Дата окончания</label>
              <input className="input" type="date" value={tmpEndISO} onChange={e => setTmpEndISO(e.target.value)} min={tmpStartISO || undefined} />
              {tmpEndISO && isInvalidRange(tmpStartISO, tmpEndISO) && (
                <div className="subtle" style={{ color: 'var(--err)' }}>
                  Выберите корректную дату окончания (после даты начала).
                </div>
              )}
            </div>
          </Modal>
        )}

        {modal.type === 'cal' && (
          <Modal title="План калорий (в день)" onClose={close} onSave={saveCal}>
            <div className="field"><label className="subtle text-sm">ккал</label><input className="input" type="number" inputMode="numeric" value={tmpText1} onChange={e=>setTmpText1(e.target.value)} placeholder="1950" /></div>
          </Modal>
        )}

        {modal.type === 'prot' && (
          <Modal title="План протеина (в день)" onClose={close} onSave={saveProt}>
            <div className="field"><label className="subtle text-sm">граммы</label><input className="input" type="number" inputMode="numeric" value={tmpText1} onChange={e=>setTmpText1(e.target.value)} placeholder="120" /></div>
          </Modal>
        )}

        {modal.type === 'weight' && (
          <Modal title="Добавить вес за сегодня" onClose={close} onSave={saveWeight} saveLabel="Сохранить вес">
            <div className="field"><label className="subtle text-sm">Вес (кг)</label><input className="input" type="number" inputMode="decimal" value={tmpText1} onChange={e=>setTmpText1(e.target.value)} placeholder="68" /></div>
            <div className="subtle text-xs mt-1">Изменение будет рассчитано автоматически по двум последним измерениям.</div>
          </Modal>
        )}

        {modal.type === 'fat' && (
          <Modal
            title="Добавить долю жира за сегодня"
            onClose={close}
            onSave={saveFat}
            saveLabel="Сохранить долю жира"
            saveDisabled={(() => { const v = computeBodyFat(tmpGender, parseNum(tmpHeightCm), parseNum(tmpWeightKg), parseNum(tmpWaistCm), parseNum(tmpNeckCm)); return !(typeof v === 'number' && isFinite(v) && v >= 0); })()}
          >
            <div className="field" role="radiogroup" aria-label="Пол">
              <div className="subtle text-sm">Пол</div>
              <div className="flex flex-col gap-2 mt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sex" checked={tmpGender==='male'} onChange={() => setTmpGender('male')} />
                  <span>мужчина</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sex" checked={tmpGender==='female'} onChange={() => setTmpGender('female')} />
                  <span>женщина</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sex" checked={tmpGender==='other'} onChange={() => setTmpGender('other')} />
                  <span>другое</span>
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-2">
              <div className="field"><label className="subtle text-sm">Рост, см</label><input className="input" type="number" inputMode="numeric" value={tmpHeightCm} onChange={e=>setTmpHeightCm(e.target.value)} placeholder="175" /></div>
              <div className="field"><label className="subtle text-sm">Вес, кг</label><input className="input" type="number" inputMode="numeric" value={tmpWeightKg} onChange={e=>setTmpWeightKg(e.target.value)} placeholder="68" /></div>
              <div className="field"><label className="subtle text см">Обхват талии, см</label><input className="input" type="number" inputMode="numeric" value={tmpWaistCm} onChange={e=>setTmpWaistCm(e.target.value)} placeholder="80" /></div>
              <div className="field"><label className="subtle text см">Обхват шеи, см</label><input className="input" type="number" inputMode="numeric" value={tmpNeckCm} onChange={e=>setTmpNeckCm(e.target.value)} placeholder="38" /></div>
            </div>

            <div className="subtle text-xs mt-2">
              — Обхват талии: Мерьте на спокойном выдохе, лента горизонтально вокруг живота — обычно на уровне пупка; при фигуре «песочные часы» — по самой узкой части. Лента прилегает плотно без перетяжки, живот не втягивать.
              <br />— Обхват шеи: Мерьте чуть ниже кадыка, лента с лёгким наклоном вниз к передней части шеи. Держите голову прямо, плечи расслаблены; лента плотно, но не «врезается».
            </div>

            <div className="glass p-3 rounded-lg mt-3">
              <div className="subtle text-sm">Расчёт</div>
              <div className="value-xl mono">{(() => { const v = computeBodyFat(tmpGender, parseNum(tmpHeightCm), parseNum(tmpWeightKg), parseNum(tmpWaistCm), parseNum(tmpNeckCm)); return (typeof v === 'number' && isFinite(v)) ? `${nf(v,1)} %` : '—'; })()}</div>
            </div>
          </Modal>
        )}

        {modal.type === 'diary-date' && (
          <Modal title="Выбрать день" onClose={close} onSave={saveDiaryDate} saveLabel="Выбрать">
            <div className="field">
              <label className="subtle text-sm">Быстрый выбор</label>
              <div className="flex gap-2 mt-1">
                <button className="tab" onClick={() => setTmpStartISO(todayISO())}>Сегодня</button>
                <button className="tab" onClick={() => setTmpStartISO(shiftDateISO(todayISO(), -1))}>Вчера</button>
              </div>
            </div>
            <div className="field">
              <label className="subtle text-sm">Дата</label>
              <input className="input" type="date" value={tmpStartISO} onChange={e => setTmpStartISO(e.target.value)} />
            </div>
          </Modal>
        )}

        {modal.type === 'food-edit' && (
          <Modal title="Редактировать блюдо" onClose={close} onSave={saveFoodEdit} saveLabel="Сохранить">
            <div className="field"><label className="subtle text-sm">Название</label><input className="input" type="text" value={tmpFoodName} onChange={e=>setTmpFoodName(e.target.value)} placeholder="Название блюда" /></div>
            <div className="grid grid-cols-3 gap-3">
              <div className="field"><label className="subtle text-sm">Вес, г</label><input className="input" type="number" inputMode="numeric" value={tmpFoodWeight} onChange={e=>setTmpFoodWeight(e.target.value)} placeholder="0" /></div>
              <div className="field"><label className="subtle text-sm">Протеин, г</label><input className="input" type="number" inputMode="numeric" value={tmpFoodProtein} onChange={e=>setTmpFoodProtein(e.target.value)} placeholder="0" /></div>
              <div className="field"><label className="subtle text-sm">Калории</label><input className="input" type="number" inputMode="numeric" value={tmpFoodKcal} onChange={e=>setTmpFoodKcal(e.target.value)} placeholder="0" /></div>
              <div className="field"><label className="subtle text-sm">Жиры, г</label><input className="input" type="number" inputMode="numeric" value={tmpFoodFat} onChange={e=>setTmpFoodFat(e.target.value)} placeholder="0" /></div>
              <div className="field"><label className="subtle text-sm">Углеводы, г</label><input className="input" type="number" inputMode="numeric" value={tmpFoodCarb} onChange={e=>setTmpFoodCarb(e.target.value)} placeholder="0" /></div>
            </div>
          </Modal>
        )}

        {modal.type === 'food-del' && (
          <Modal title="Удалить блюдо" onClose={close} onSave={confirmFoodDelete} saveLabel="Удалить">
            <div className="subtle">Вы уверены, что хотите удалить <span className="mono">{foodList[deleteIndex]?.name}</span>?</div>
          </Modal>
        )}
      </div></div>
  );
}


