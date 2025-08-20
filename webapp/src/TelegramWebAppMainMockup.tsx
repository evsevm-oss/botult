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
    .container { padding-top: calc(env(safe-area-inset-top, 0px) + 12px); padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 108px); min-height: 100%; }
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
    .tab { display:inline-flex; align-items:center; justify-content:center; min-height: 36px; height: auto; padding: 8px 14px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.14); white-space: nowrap; line-height: 1; }
    .tab-active { background: rgba(109,40,217,0.22); border-color: rgba(109,40,217,0.42); }
    .tabs { display:flex; gap:8px; overflow-x:auto; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
    .tabs::-webkit-scrollbar{ display:none; }
    .row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
    .row .subtle { white-space: nowrap; }
    .metric { background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; }
    .metric-btn { width:100%; text-align:left; cursor:pointer; }
    .metric-btn:focus { outline: 2px solid rgba(109,40,217,0.65); outline-offset: 2px; }
    .value-xl { font-size: 20px; font-weight: 700; }
    .pill { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.16); color: var(--muted); font-size: 12px; line-height: 18px; white-space: nowrap; }
    .mono { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
    .shadow-xl { box-shadow: 0 10px 30px rgba(16,24,40,0.35); }
    .main-gradient { background: radial-gradient(1200px 400px at 50% -10%, rgba(99,102,241,0.25), transparent), radial-gradient(800px 300px at 0% 10%, rgba(147,51,234,0.15), transparent), radial-gradient(800px 300px at 100% 10%, rgba(56,189,248,0.12), transparent); }
    .chart-wrap{position:relative}
    .chart-labels{position:absolute; top:8px; left:8px; right:8px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap; pointer-events:none}
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
    .text-left{text-align:left}
    .truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .text-xs{font-size:12px}
    .text-lg{font-size:18px}
    .h-5{height:20px}
    .h-10{height:40px}
    .h-16{height:64px}
    .h-220{height:220px}
    .h-240{height:240px}
    .minh-360{min-height:360px}
    .grid{display:grid}
    .grid-cols-6{grid-template-columns:repeat(6,minmax(0,1fr))}
    .grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .row-grid{display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:center}
    @media (min-width:960px){.md\:grid-cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}}

    /* Modal */
    .modal-root { position: fixed; inset: 0; z-index: 50; }
    .backdrop { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.55); z-index: 50; }
    .modal { position: fixed; z-index: 51; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(92vw, 420px); background: var(--card); border:1px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 16px; }
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
const last7 = [
  { d: "Пн", kcal: 1820, protein: 110 },
  { d: "Вт", kcal: 2050, protein: 118 },
  { d: "Ср", kcal: 1760, protein: 124 },
  { d: "Чт", kcal: 1900, protein: 130 },
  { d: "Пт", kcal: 1990, protein: 98 },
  { d: "Сб", kcal: 2100, protein: 140 },
  { d: "Вс", kcal: 1720, protein: 122 },
];

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
          <div className="pill mt-auto self-end">{values.dateRange}</div>
        </button>
        {/* Калории */}
        <button className="metric metric-btn tile-half" onClick={onEditCalories} aria-label="Изменить план калорий">
          <div className="subtle text-[12px] mb-1">Калории</div>
          <div className="value-xl mono">{`< ${nf(values.calPlan)} ккал`}</div>
          <div className="pill mt-1">план на день</div>
        </button>
        {/* Протеин */}
        <button className="metric metric-btn tile-half" onClick={onEditProtein} aria-label="Изменить план протеина">
          <div className="subtle text-[12px] mb-1">Протеин</div>
          <div className="value-xl mono">{`> ${nf(values.protPlan)} г`}</div>
          <div className="pill mt-1">план на день</div>
        </button>
      </div>

      {/* Группа 2: вес и жир */}
      <div className="grid grid-cols-2 gap-3">
        <button className="metric metric-btn flex items-center justify-between" onClick={onAddWeightToday} aria-label="Добавить вес за сегодня">
          <div>
            <div className="subtle text-[12px] mb-1">Вес</div>
            <div className="value-xl mono">{nf(values.weight)} кг</div>
          </div>
          <div className="pill">{values.weightDelta}</div>
        </button>
        <button className="metric metric-btn flex items-center justify-between" onClick={onAddFatToday} aria-label="Добавить долю жира за сегодня">
          <div>
            <div className="subtle text-[12px] mb-1">Доля жира</div>
            <div className="value-xl mono">~{nf(values.fatPct)}%</div>
          </div>
          <div className="pill">{values.fatDelta}</div>
        </button>
      </div>
    </div>
  </Card>
);

// --- Данные для графика веса/жира ---
interface WFPoint { x: string; d: string; weight: number; fat: number; }
const genWeightFat = (days: number): WFPoint[] => {
  const now = new Date();
  const res: WFPoint[] = [];
  const weightToday = 68.0;
  const fatToday = 24.8;
  const wSlope = 5 / 365;
  const fSlope = 1.2 / 365;
  for (let j = 0; j < days; j++) {
    const k = days - 1 - j; // дней назад
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - k);
    const iso = date.toISOString().slice(0, 10);
    const dd = String(date.getDate()).padStart(2, '0');
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const label = days <= 30
      ? dd
      : days <= 120
        ? `${dd}.${mm}`
        : date.toLocaleDateString('ru-RU', { month: 'short' });
    const weight = +(weightToday + wSlope * (days - 1 - j) + Math.sin(j / 6) * 0.05).toFixed(1);
    const fat = +(fatToday + fSlope * (days - 1 - j) + Math.cos(j / 7) * 0.03).toFixed(2);
    res.push({ x: iso, d: label, weight, fat });
  }
  return res;
};

const WeightFatWidget: React.FC<{ initial?: WFPoint[] }> = ({ initial }) => {
  const [period, setPeriod] = useState<'week'|'month'|'q'|'year'>('month');
  const daysMap = { week: 7, month: 30, q: 90, year: 365 } as const;
  const data = useMemo(() => initial && initial.length ? initial : genWeightFat(daysMap[period]), [period, initial]);

  const wMin = Math.min(...data.map(p => p.weight));
  const wMax = Math.max(...data.map(p => p.weight));
  const fMin = Math.min(...data.map(p => p.fat));
  const fMax = Math.max(...data.map(p => p.fat));
  const leftDomain: [number, number] = [Math.floor(wMin), Math.ceil(wMax)];
  const rightDomain: [number, number] = [Math.floor(fMin), Math.ceil(fMax)];

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
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid stroke="var(--chart-grid)" />
            <XAxis dataKey="d" tick={{ fill: 'var(--muted)' }} interval="preserveStartEnd" />
            <YAxis yAxisId="left" orientation="left" tick={{ fill: 'var(--muted)' }} domain={leftDomain} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--muted)' }} domain={rightDomain} />
            <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: 'var(--text)' }} />
            <Legend wrapperStyle={{ color: 'var(--muted)' }} />
            <Line yAxisId="left" type="monotone" dataKey="weight" name="Вес (кг)" stroke="#a78bfa" strokeWidth={2.5} dot={false} />
            <Line yAxisId="right" type="monotone" dataKey="fat" name="Жир (%)" stroke="#38bdf8" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};

const CaloriesProteinWidget: React.FC<{ weekly?: { d: string; kcal: number; protein: number; }[] }> = ({ weekly }) => {
  const CAL_PLAN = 1950;
  const PROT_PLAN = 120; // граммы

  const series = weekly && weekly.length ? weekly : last7;
  const maxK = useMemo(() => Math.max(...series.map(x => x.kcal), CAL_PLAN), [series]);
  const maxP = useMemo(() => Math.max(...series.map(x => x.protein), PROT_PLAN), [series]);
  const yLeftMax = useMemo(() => Math.ceil((maxK * 1.6) / 50) * 50, [maxK]);
  const yRightMax = useMemo(() => Math.ceil((maxP * 1.6) / 5) * 5, [maxP]);

  const avg = useMemo(() => {
    const ak = series.reduce((s, x) => s + x.kcal, 0) / series.length;
    const ap = series.reduce((s, x) => s + x.protein, 0) / series.length;
    return { ak, ap };
  }, [series]);

  return (
    <Card title="Потребление калорий и протеина" className="mb-3">
      <div className="chart-wrap" style={{ width: '100%', height: 240 }}>
        <div className="chart-labels">
          <span className="pill">План калорий 1950</span>
          <span className="pill">План протеина 120</span>
          {typeof weeklyCompliance === 'number' && <span className="pill">Комплаенс {weeklyCompliance}%</span>}
          {typeof weightPace === 'number' && <span className="pill">Темп веса {weightPace} кг/нед</span>}
        </div>
        <ResponsiveContainer>
          <BarChart data={series} margin={{ left: 8, right: 8, top: 8, bottom: 0 }} barCategoryGap="28%">
            <CartesianGrid stroke="var(--chart-grid)" />
            <XAxis dataKey="d" tick={{ fill: 'var(--muted)' }} />
            <YAxis yAxisId="left" tick={{ fill: 'var(--muted)' }} domain={[0, yLeftMax]} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--muted)' }} domain={[0, yRightMax]} />
            <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: 'var(--text)' }} />
            <Legend wrapperStyle={{ color: 'var(--muted)' }} />
            <ReferenceLine yAxisId="left" y={CAL_PLAN} stroke="#a78bfa" strokeDasharray="4 4" />
            <ReferenceLine yAxisId="right" y={PROT_PLAN} stroke="#38bdf8" strokeDasharray="4 4" />
            <Bar yAxisId="left" dataKey="kcal" name="Калории" fill="#8b5cf6" radius={[6,6,0,0]} barSize={18} />
            <Bar yAxisId="right" dataKey="protein" name="Протеин (г)" fill="#22d3ee" radius={[6,6,0,0]} barSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
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
    className="fixed left-0 right-0 bottom-0 px-3 pt-3 main-gradient"
    role="region"
    aria-label="MainButton dock"
    style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 12px)' }}
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
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
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
  

  // Верхние плитки
  const [goalTitle, setGoalTitle] = useState('Снижение веса');
  const [goalNote, setGoalNote] = useState('дефицит калорий');
  const [dateRange, setDateRange] = useState('19 мая 2025 – 18 августа 2025');
  const [calPlan, setCalPlan] = useState(1950);
  const [protPlan, setProtPlan] = useState(120);
  const [weight, setWeight] = useState(68);
  const [weightDelta, setWeightDelta] = useState('-5%');
  const [fatPct, setFatPct] = useState(25);
  const [fatDelta, setFatDelta] = useState('-5%');
  const [weightHistory, setWeightHistory] = useState<number[]>([71.6, weight]);
  const [fatHistory, setFatHistory] = useState<number[]>([26.3, fatPct]);

  useEffect(() => {
    if (weightHistory.length >= 2) {
      const prev = weightHistory[weightHistory.length - 2];
      const curr = weightHistory[weightHistory.length - 1];
      setWeightDelta(deltaLabel(prev, curr));
    }
  }, [weightHistory]);
  useEffect(() => {
    if (fatHistory.length >= 2) {
      const prev = fatHistory[fatHistory.length - 2];
      const curr = fatHistory[fatHistory.length - 1];
      setFatDelta(deltaLabel(prev, curr));
    }
  }, [fatHistory]);
  const [goalMode, setGoalMode] = useState<'loss'|'maint'|'gain'|'nocw'>(() => inferGoalMode(goalTitle, goalNote));

  // Модалки
  const [modal, setModal] = useState<{ type: null | 'goal' | 'cal' | 'prot' | 'weight' | 'fat' | 'food-edit' | 'food-del' | 'diary-date' }>({ type: null });
  const close = () => setModal({ type: null });

  // Поля модалок
  const [tmpText1, setTmpText1] = useState('');
  const [tmpStartISO, setTmpStartISO] = useState<string>(todayISO());
  const [tmpEndISO, setTmpEndISO] = useState<string>('');
  const [tmpGender, setTmpGender] = useState<'male'|'female'|'other'>('male');
  const [tmpHeightCm, setTmpHeightCm] = useState<string>('');
  const [tmpWeightKg, setTmpWeightKg] = useState<string>(String(weight));
  const [tmpWaistCm, setTmpWaistCm] = useState<string>('');
  const [tmpNeckCm, setTmpNeckCm] = useState<string>('');

  const openGoal = () => { setGoalMode(inferGoalMode(goalTitle, goalNote)); setTmpStartISO(todayISO()); setTmpEndISO(''); setModal({ type: 'goal' }); };
  const saveGoal = () => { if (isInvalidRange(tmpStartISO, tmpEndISO)) return; const p = GOAL_PRESETS[goalMode]; setGoalTitle(p.title); setGoalNote(p.note); setDateRange(makeRangeLabel(tmpStartISO, tmpEndISO)); close(); };

  const openCal = () => { setTmpText1(String(calPlan)); setModal({ type: 'cal' }); };
  const saveCal = () => { const v = parseInt(tmpText1, 10); if (!Number.isNaN(v) && v > 0) setCalPlan(v); close(); };

  const openProt = () => { setTmpText1(String(protPlan)); setModal({ type: 'prot' }); };
  const saveProt = () => { const v = parseInt(tmpText1, 10); if (!Number.isNaN(v) && v > 0) setProtPlan(v); close(); };

  const openWeight = () => { setTmpText1(String(weight)); setModal({ type: 'weight' }); };
  const saveWeight = () => { const v = Number(tmpText1); if (!Number.isNaN(v) && v > 0) { setWeight(v); setWeightHistory(h => [...h, v]); } close(); };

  const openFat = () => { setTmpGender('male'); setTmpHeightCm(''); setTmpWeightKg(String(weight)); setTmpWaistCm(''); setTmpNeckCm(''); setModal({ type: 'fat' }); };
  const saveFat = () => {
    const bf = computeBodyFat(tmpGender, parseNum(tmpHeightCm), parseNum(tmpWeightKg), parseNum(tmpWaistCm), parseNum(tmpNeckCm));
    if (bf != null && isFinite(bf) && bf >= 0) {
      const val = Math.round(bf * 10) / 10;
      setFatPct(val);
      setFatHistory(h => [...h, val]);
      // send to server
      const tgId = getTelegramId();
      if (tgId) {
        const today = todayISO();
        apiFetch(`/api/bodyfat?telegram_id=${tgId}`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ date: today, percent: val })
        }).catch(() => {});
      }
    }
    close();
  };

  // Дневник (стабильная версия: один список, дата для навигации)
  const [diaryDateISO, setDiaryDateISO] = useState<string>(todayISO());
  const [foodList, setFoodList] = useState<Food[]>(() => foods.map(f => ({ ...f, protein: 0, weight: 0 })));
  const diaryRef = useRef<HTMLDivElement | null>(null);
  const openDiaryDate = () => { setTmpStartISO(diaryDateISO); setModal({ type: 'diary-date' }); };
  const saveDiaryDate = () => { if (tmpStartISO) setDiaryDateISO(tmpStartISO); close(); };

  // CRUD блюд
  const [editIndex, setEditIndex] = useState<number>(-1);
  const [tmpFoodName, setTmpFoodName] = useState<string>('');
  const [tmpFoodWeight, setTmpFoodWeight] = useState<string>('0');
  const [tmpFoodProtein, setTmpFoodProtein] = useState<string>('0');
  const [tmpFoodKcal, setTmpFoodKcal] = useState<string>('0');
  const openFoodEdit = (i: number) => { const f = foodList[i]; if (!f) return; setEditIndex(i); setTmpFoodName(f.name); setTmpFoodWeight(String(f.weight ?? 0)); setTmpFoodProtein(String(f.protein ?? 0)); setTmpFoodKcal(String(f.kcal)); setModal({ type: 'food-edit' }); };
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
    };
    const itemsForMeal = foodList.filter(x => x.mealId === edited.mealId).map(x => ({
      name: x === edited ? updatedItem.name : x.name,
      unit: x.unit || 'g',
      amount: x === edited ? (updatedItem.weight||0) : (x.weight||0),
      kcal: x === edited ? (updatedItem.kcal||0) : (x.kcal||0),
      protein_g: x === edited ? (updatedItem.protein||0) : (x.protein||0),
      fat_g: x.fat_g || 0,
      carb_g: x.carb_g || 0,
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

  const kcalToday = useMemo(() => foodList.reduce((s, f) => s + (Number(f.kcal)||0), 0), [foodList]);
  const values = { goalTitle, goalNote, dateRange, calPlan, protPlan, weight, weightDelta, fatPct, fatDelta };
  const mainButtonLabel = makeMainButtonLabel(kcalToday);

  // Backend integrations: load weekly summary and meals
  const [weeklySeries, setWeeklySeries] = useState<{ d: string; kcal: number; protein: number }[] | null>(null);
  const [weeklyCompliance, setWeeklyCompliance] = useState<number | null>(null);
  const [weightPace, setWeightPace] = useState<number | null>(null);
  const [wfSeries, setWfSeries] = useState<WFPoint[] | null>(null);
  const [periodFilter, setPeriodFilter] = useState<'week'|'month'|'q'|'year'>('week');
  const [tz, setTz] = useState<string>(() => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');

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

  const fetchAll = useCallback(async () => {
      try {
        setMbState('loading');
        const tgId = getTelegramId();
        if (!tgId) { setLoading(false); return; }
        // Weekly summary: use /api/summary/weekly to derive bars; optionally fetch /api/weights for WF graph later
        const today = new Date();
        const daySpan = periodFilter==='week' ? 6 : (periodFilter==='month' ? 29 : (periodFilter==='q' ? 89 : 364));
        const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - daySpan).toISOString().slice(0,10);
        const r1 = await apiFetch(`/api/summary/weekly?telegram_id=${tgId}&start=${start}&tz=${encodeURIComponent(tz)}`);
        const b1 = await r1.json();
        if (b1?.ok && Array.isArray(b1?.data?.items)) {
          const items = b1.data.items as { date: string; kcal: number; protein_g: number }[];
          const ser = items.map(it => ({ d: it.date.slice(5), kcal: Number(it.kcal||0), protein: Number(it.protein_g||0) }));
          setWeeklySeries(ser);
          setWeeklyCompliance((b1.data.compliance && b1.data.compliance.score) || null);
          setWeightPace((b1.data.weight_pace_kg_per_week != null) ? Number(b1.data.weight_pace_kg_per_week) : null);
        }
        // Optionally, fetch weights to populate WF graph
        const r3 = await apiFetch(`/api/weights?telegram_id=${tgId}&start=${start}`);
        const b3 = await r3.json();
        if (b3?.ok && Array.isArray(b3?.data?.items)) {
          const items = b3.data.items as { date: string; weight_kg: number }[];
          const wf = items.map((it) => ({ x: it.date, d: it.date.slice(5), weight: Number(it.weight_kg||0), fat: NaN as unknown as number }));
          // keep fat series empty for now; UI will only plot weight when fat NaN
          setWfSeries(wf);
        }
        // Meals for selected date
        const r2 = await apiFetch(`/api/meals?telegram_id=${tgId}&date=${diaryDateISO}&tz=${encodeURIComponent(tz)}`);
        const b2 = await r2.json();
        if (b2?.ok && Array.isArray(b2?.data?.items)) {
          const meals = b2.data.items as any[];
          const list: Food[] = [];
          meals.forEach((m: any) => {
            (m.items || []).forEach((it: any) => list.push({ name: it.name, kcal: Number(it.kcal||0), protein: Number(it.protein_g||0), weight: Number(it.amount||0), mealId: m.id, itemId: it.id, unit: it.unit || 'g', fat_g: Number(it.fat_g||0), carb_g: Number(it.carb_g||0) }));
          });
          if (list.length) setFoodList(list);
        }
        setOffline(false);
      } catch {
        setOffline(true);
      } finally {
        setLoading(false);
        setMbState('default');
      }
    }, [diaryDateISO, periodFilter, tz]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="container px-3">
      <RootStyles />

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
          ) : <CaloriesProteinWidget weekly={weeklySeries || undefined} />}
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
              {isInvalidRange(tmpStartISO, tmpEndISO) && (
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
              <div className="flex gap-2 mt-1">
                <label className="tab cursor-pointer"><input type="radio" name="sex" className="mr-1" checked={tmpGender==='male'} onChange={() => setTmpGender('male')} />мужчина</label>
                <label className="tab cursor-pointer"><input type="radio" name="sex" className="mr-1" checked={tmpGender==='female'} onChange={() => setTmpGender('female')} />женщина</label>
                <label className="tab cursor-pointer"><input type="radio" name="sex" className="mr-1" checked={tmpGender==='other'} onChange={() => setTmpGender('other')} />другое</label>
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


