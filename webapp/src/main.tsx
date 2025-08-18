import React from 'react'
import { createRoot } from 'react-dom/client'
import { ProfilePage } from './profile'
import React, { useEffect, useState } from 'react'

function MealsPage() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp
    const initDataUnsafe = tg?.initDataUnsafe
    const user = initDataUnsafe?.user
    const telegram_id = user?.id
    const today = new Date().toISOString().slice(0, 10)
    fetch(`/api/meals?telegram_id=${telegram_id}&date=${today}`)
      .then(r => r.json())
      .then(j => setItems(j?.data?.items || []))
      .finally(() => setLoading(false))
  }, [])
  if (loading) return <div>Loading…</div>
  return (
    <div>
      <h2>Дневник на сегодня</h2>
      {items.map((m, idx) => (
        <div key={idx} style={{padding:8,border:'1px solid #333',marginBottom:8}}>
          <div>{new Date(m.at).toLocaleTimeString()} — {m.type} ({m.status})</div>
          <ul>
            {m.items.map((it:any) => (
              <li key={it.id}>{it.name}: {Math.round(it.amount)}{it.unit}, {Math.round(it.kcal)} ккал</li>
            ))}
          </ul>
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


