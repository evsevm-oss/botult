const TOKEN_KEY = 'webapp_jwt_token';
const EXP_KEY = 'webapp_jwt_exp';
let refreshTimer: number | null = null;

const getInitData = (): string | null => {
  try {
    // 1) Try Telegram object
    const tg: any = (window as any).Telegram?.WebApp;
    const initData: string | undefined = tg?.initData;
    if (initData && initData.length > 0) return initData;
  } catch {}
  try {
    // 2) Fallback: query string param provided by Telegram clients
    const qs = new URLSearchParams(window.location.search);
    const keys = ["tgWebAppData", "initData", "tgwebappdata"]; // try common variants
    for (const k of keys) {
      const v = qs.get(k);
      if (v && v.length > 0) return v;
    }
  } catch {}
  try {
    // 3) Fallback: some clients pass initData in the URL hash fragment
    const h = (window.location.hash || '').replace(/^#/, '');
    if (h) {
      const hp = new URLSearchParams(h);
      const keys = ["tgWebAppData", "initData", "tgwebappdata"]; // same variants
      for (const k of keys) {
        const v = hp.get(k);
        if (v && v.length > 0) return v;
      }
    }
  } catch {}
  return null;
};

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const getTokenExp = (): number | null => {
  const v = localStorage.getItem(EXP_KEY);
  return v ? parseInt(v, 10) : null;
};

const scheduleRefresh = () => {
  if (refreshTimer) {
    window.clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  const exp = getTokenExp();
  const now = Math.floor(Date.now() / 1000);
  if (!exp || exp <= now) return;
  const secondsUntilRefresh = Math.max(5, exp - now - 60); // refresh 60s before expiry
  refreshTimer = window.setTimeout(() => {
    refreshToken().catch(() => {/* ignore */});
  }, secondsUntilRefresh * 1000);
};

export const ensureAuth = async (): Promise<void> => {
  const token = getToken();
  const exp = getTokenExp();
  const now = Math.floor(Date.now() / 1000);
  if (token && exp && exp - now > 90) {
    scheduleRefresh();
    return;
  }
  const initData = getInitData();
  if (!initData) return; // outside Telegram, skip
  const res = await fetch('/api/webapp/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initData }),
  });
  const body = await res.json().catch(() => ({}));
  if (body?.ok && body?.data?.token && body?.data?.exp) {
    localStorage.setItem(TOKEN_KEY, body.data.token);
    localStorage.setItem(EXP_KEY, String(body.data.exp));
    scheduleRefresh();
  }
};

export const refreshToken = async (): Promise<void> => {
  const token = getToken();
  if (!token) return;
  const res = await fetch('/api/webapp/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  const body = await res.json().catch(() => ({}));
  if (body?.ok && body?.data?.token && body?.data?.exp) {
    localStorage.setItem(TOKEN_KEY, body.data.token);
    localStorage.setItem(EXP_KEY, String(body.data.exp));
    scheduleRefresh();
  } else if (body?.ok === false) {
    logout();
  }
};

export const logout = (): void => {
  if (refreshTimer) {
    window.clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXP_KEY);
};

export const apiFetch = async (input: string, init: RequestInit = {}): Promise<Response> => {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(input, { ...init, headers });
};

export const getTelegramId = (): number | null => {
  try {
    // Debug override via URL param (force_tid)
    try {
      const params = new URLSearchParams(window.location.search);
      const forced = params.get('force_tid');
      if (forced && /^\d+$/.test(forced)) return parseInt(forced, 10);
    } catch {}
    const tg: any = (window as any).Telegram?.WebApp;
    const raw = tg?.initDataUnsafe?.user?.id;
    const id = typeof raw === 'string' ? parseInt(raw, 10) : raw;
    if (Number.isFinite(id)) return Number(id);
    // Fallback 1: parse from initData query-string if present (Desktop Telegram иногда не заполняет initDataUnsafe)
    const init = getInitData();
    if (init) {
      try {
        const params = new URLSearchParams(init);
        const userStr = params.get('user');
        if (userStr) {
          const u = JSON.parse(userStr);
          const uid = typeof u?.id === 'string' ? parseInt(u.id, 10) : u?.id;
          if (Number.isFinite(uid)) return Number(uid);
        }
      } catch {}
    }
    // Fallback: decode from JWT token payload (claim tid)
    const token = getToken();
    if (token) {
      const parts = token.split('.')
      if (parts.length === 3) {
        try {
          const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
          const json = JSON.parse(atob(b64));
          const tid = json?.tid;
          if (typeof tid === 'number' && Number.isFinite(tid)) return tid;
          if (typeof tid === 'string' && /^\d+$/.test(tid)) return parseInt(tid, 10);
        } catch {}
      }
    }
    return null;
  } catch {
    return null;
  }
};


