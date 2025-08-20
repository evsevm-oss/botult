const TOKEN_KEY = 'webapp_jwt_token';
const EXP_KEY = 'webapp_jwt_exp';
let refreshTimer: number | null = null;

const getInitData = (): string | null => {
  try {
    // Telegram WebApp init data is available inside Telegram client
    const tg: any = (window as any).Telegram?.WebApp;
    const initData: string | undefined = tg?.initData;
    if (initData && initData.length > 0) return initData;
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
    const tg: any = (window as any).Telegram?.WebApp;
    const id = tg?.initDataUnsafe?.user?.id;
    return typeof id === 'number' ? id : null;
  } catch {
    return null;
  }
};


