import React from 'react'
import { createRoot } from 'react-dom/client'
import { ProfilePage } from './profile'
import React, { useEffect, useState } from 'react'

function MealsPage() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp
    const initDataUnsafe = tg?.initDataUnsafe
    const user = initDataUnsafe?.user
    const telegram_id = user?.id
    fetch(`/api/meals?telegram_id=${telegram_id}&date=${date}`)
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

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MealsPage />
  </React.StrictMode>
)


