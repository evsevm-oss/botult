import React, { useEffect, useState } from 'react'

type ProfileDTO = {
  sex: 'male' | 'female'
  birth_date?: string | null
  height_cm: number
  weight_kg: number
  activity_level: 'low' | 'medium' | 'high'
  goal: 'lose' | 'maintain' | 'gain'
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export function ProfilePage() {
  const [telegramId, setTelegramId] = useState<number | null>(null)
  const [profile, setProfile] = useState<ProfileDTO | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // In Telegram WebApp this comes from initData; for local dev, mock a tg id
    setTelegramId(123456789)
  }, [])

  useEffect(() => {
    if (!telegramId) return
    setLoading(true)
    fetch(`${API_BASE}/api/profile?telegram_id=${telegramId}`)
      .then((r) => r.json())
      .then((j) => setProfile(j.data || null))
      .finally(() => setLoading(false))
  }, [telegramId])

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!telegramId || !profile) return
    setLoading(true)
    await fetch(`${API_BASE}/api/profile?telegram_id=${telegramId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    })
    setLoading(false)
    alert('Профиль сохранен')
  }

  return (
    <div style={{ maxWidth: 480, margin: '16px auto', fontFamily: 'system-ui' }}>
      <h2>Профиль</h2>
      {loading && <div>Загрузка...</div>}
      <form onSubmit={onSubmit}>
        <label>
          Пол
          <select
            value={profile?.sex || 'male'}
            onChange={(e) => setProfile({ ...(profile || ({} as ProfileDTO)), sex: e.target.value as any })}
          >
            <option value="male">male</option>
            <option value="female">female</option>
          </select>
        </label>
        <br />
        <label>
          Рост (см)
          <input
            type="number"
            value={profile?.height_cm ?? 170}
            onChange={(e) => setProfile({ ...(profile || ({} as ProfileDTO)), height_cm: Number(e.target.value) })}
          />
        </label>
        <br />
        <label>
          Вес (кг)
          <input
            type="number"
            value={profile?.weight_kg ?? 70}
            onChange={(e) => setProfile({ ...(profile || ({} as ProfileDTO)), weight_kg: Number(e.target.value) })}
          />
        </label>
        <br />
        <label>
          Активность
          <select
            value={profile?.activity_level || 'medium'}
            onChange={(e) => setProfile({ ...(profile || ({} as ProfileDTO)), activity_level: e.target.value as any })}
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
        <br />
        <label>
          Цель
          <select
            value={profile?.goal || 'maintain'}
            onChange={(e) => setProfile({ ...(profile || ({} as ProfileDTO)), goal: e.target.value as any })}
          >
            <option value="lose">lose</option>
            <option value="maintain">maintain</option>
            <option value="gain">gain</option>
          </select>
        </label>
        <br />
        <button type="submit" disabled={loading}>
          Сохранить
        </button>
      </form>
    </div>
  )
}


