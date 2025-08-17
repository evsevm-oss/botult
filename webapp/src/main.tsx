import React from 'react'
import { createRoot } from 'react-dom/client'
import { ProfilePage } from './profile'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ProfilePage />
  </React.StrictMode>
)


