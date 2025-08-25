import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import TelegramWebAppMainMockup from './TelegramWebAppMainMockup'
import { ensureAuth } from './auth'

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: any }>{
  constructor(props: { children: React.ReactNode }){ super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error: any){ return { error }; }
  componentDidCatch(error: any){ try { console.error('App crash:', error); } catch {}
    try { (window as any).Telegram?.WebApp?.showPopup?.({ title: 'Ошибка', message: String(error?.message||error), buttons: [{ type: 'ok' }] }); } catch {}
  }
  render(){ if (this.state.error){ return (
    <div style={{ padding: 12 }}>
      <div style={{ padding: 12, borderRadius: 12, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)' }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Произошла ошибка интерфейса</div>
        <div style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', fontSize: 12 }}>{String(this.state.error?.message || this.state.error)}</div>
      </div>
    </div>
  ); }
    return this.props.children as any;
  }
}

function MealsPage() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp
    const initDataUnsafe = tg?.initDataUnsafe
    const user = initDataUnsafe?.user
    const telegram_id = user?.id
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    fetch(`/api/meals?telegram_id=${telegram_id}&date=${date}&tz=${encodeURIComponent(tz)}`)
      .then(r => r.json())
      .then(j => setItems(j?.data?.items || []))
      .finally(() => setLoading(false))
  }, [date])
  if (loading) return <div>Loading…</div>
  return (
    <div>
      <h2>Дневник</h2>
      <label>Дата: <input type="date" value={date} onChange={(e)=>setDate(e.target.value)} /></label>
      <button onClick={async ()=>{
        const tg = (window as any).Telegram?.WebApp
        const user = tg?.initDataUnsafe?.user
        const telegram_id = user?.id
        const now = new Date().toISOString()
        const body = { at: now, type: null, status: 'confirmed', items: [], notes: 'Быстрый приём' }
        await fetch(`/api/meals?telegram_id=${telegram_id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        location.reload()
      }}>Быстрый приём (пустой)</button>
      {items.map((m, idx) => (
        <div key={idx} style={{padding:8,border:'1px solid #333',marginBottom:8}}>
          <div>{new Date(m.at).toLocaleTimeString()} — {m.type} ({m.status})</div>
          <div>
            <label>Тип приёма: 
              <select defaultValue={m.type} onChange={async (e)=>{
                const tg = (window as any).Telegram?.WebApp
                const user = tg?.initDataUnsafe?.user
                const telegram_id = user?.id
                await fetch(`/api/meals/${m.id}?telegram_id=${telegram_id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: e.target.value }) })
              }}>
                <option value="breakfast">breakfast</option>
                <option value="lunch">lunch</option>
                <option value="dinner">dinner</option>
                <option value="snack">snack</option>
              </select>
            </label>
          </div>
          <ul>
            {m.items.map((it:any) => (
              <li key={it.id}>{it.name}: {Math.round(it.amount)}{it.unit}, {Math.round(it.kcal)} ккал</li>
            ))}
          </ul>
          <button onClick={async () => {
            const tg = (window as any).Telegram?.WebApp
            const user = tg?.initDataUnsafe?.user
            const telegram_id = user?.id
            await fetch(`/api/meals/${m.id}?telegram_id=${telegram_id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ notes: (m.notes||'') + ' (edited)' }) })
            location.reload()
          }}>Редактировать (заметка)</button>
          <button onClick={async () => {
            const tg = (window as any).Telegram?.WebApp
            const user = tg?.initDataUnsafe?.user
            const telegram_id = user?.id
            await fetch(`/api/meals/${m.id}?telegram_id=${telegram_id}`, { method: 'DELETE' })
            location.reload()
          }}>Удалить</button>
        </div>
      ))}
    </div>
  )
}

// Render immediately to avoid blank screen if auth is slow/unavailable
const root = createRoot(document.getElementById('root')!);
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <TelegramWebAppMainMockup />
    </ErrorBoundary>
  </React.StrictMode>
);

// Run auth refresh in background (non-blocking)
ensureAuth().catch(() => { /* ignore auth errors at boot; UI can still work */ });


