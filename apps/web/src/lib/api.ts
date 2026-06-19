/** Пустая строка в dev: запросы идут на тот же origin, Vite проксирует /api */
const API_PREFIX = import.meta.env.VITE_API_BASE ?? '';

const TOKEN_KEY = 'iter_token';
const TOKEN_PERSIST_KEY = 'iter_token_persist';
/** Срок хранения при «Запомнить устройство» — не показываем пользователю */
const REMEMBER_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

type PersistedToken = { t: string; exp: number };

export function getToken(): string | null {
  const session = sessionStorage.getItem(TOKEN_KEY);
  if (session) return session;

  const raw = localStorage.getItem(TOKEN_PERSIST_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PersistedToken;
    if (!parsed.t || typeof parsed.exp !== 'number') {
      localStorage.removeItem(TOKEN_PERSIST_KEY);
      return null;
    }
    if (Date.now() >= parsed.exp) {
      localStorage.removeItem(TOKEN_PERSIST_KEY);
      return null;
    }
    return parsed.t;
  } catch {
    localStorage.removeItem(TOKEN_PERSIST_KEY);
    return null;
  }
}

export function setToken(token: string, rememberDevice = false): void {
  if (rememberDevice) {
    sessionStorage.removeItem(TOKEN_KEY);
    const exp = Date.now() + REMEMBER_DURATION_MS;
    localStorage.setItem(TOKEN_PERSIST_KEY, JSON.stringify({ t: token, exp } satisfies PersistedToken));
  } else {
    localStorage.removeItem(TOKEN_PERSIST_KEY);
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_PERSIST_KEY);
}

export async function parseApiResponseError(res: Response): Promise<string> {
  let detail = res.statusText;
  try {
    const j = (await res.json()) as { detail?: unknown };
    if (typeof j.detail === 'string') detail = j.detail;
    else if (j.detail != null) detail = JSON.stringify(j.detail);
  } catch {
    /* ignore */
  }
  return detail;
}

/** Таймаут запросов к API (мс): при незапущенном бэкенде прокси Vite может долго ждать. */
const API_FETCH_TIMEOUT_MS = 25_000;

function defaultAbortSignal(existing?: AbortSignal): AbortSignal {
  if (existing) return existing;
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(API_FETCH_TIMEOUT_MS);
  }
  const ctrl = new AbortController();
  globalThis.setTimeout(() => ctrl.abort(), API_FETCH_TIMEOUT_MS);
  return ctrl.signal;
}

function isAbortError(e: unknown): boolean {
  if (e instanceof DOMException && e.name === 'AbortError') return true;
  if (e instanceof Error && e.name === 'AbortError') return true;
  return false;
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (
    options.body != null &&
    typeof options.body === 'string' &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const signal = defaultAbortSignal(options.signal);

  let res: Response;
  try {
    res = await fetch(`${API_PREFIX}${path}`, { ...options, headers, signal });
  } catch (e) {
    if (isAbortError(e)) {
      throw new Error(
        'Нет ответа от сервера вовремя. Убедитесь, что API запущен (uvicorn), а в dev порт совпадает с VITE_API_PROXY в Vite (по умолчанию 8010).',
      );
    }
    throw e;
  }
  if (!res.ok) throw new Error(await parseApiResponseError(res));
  return res;
}

export async function requestGuestCode(email: string): Promise<void> {
  const res = await apiFetch('/api/auth/request-code', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
  if (res.status !== 204) throw new Error('Неожиданный ответ сервера');
}

export async function verifyGuestCode(email: string, code: string): Promise<string> {
  const res = await apiFetch('/api/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  });
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export type Me = {
  email: string;
  is_admin: boolean;
  role: string;
  can_create_guest_links: boolean;
};

export async function fetchMe(): Promise<Me> {
  const res = await apiFetch('/api/auth/me');
  return res.json();
}

export type VpnGeneratedLinks = {
  happ_url: string;
  flclash_url: string;
  config_text: string;
};

export type GuestVpnLinkOut = {
  slot: number;
  happ_url: string;
  flclash_url: string;
};

export type MasterSubscriptionResponse = {
  master_subscription_url: string | null;
  server_name_mode: string;
  server_name_rules: string;
  output_format_mode: string;
  bypass_render_mode: string;
  slovo_ru_direct_override: boolean;
  slovo_ru_direct_routes: string;
  slovo_ru_direct_provider_preview: string;
};

/** Сохранённые основные ссылки VPN (если уже создавались). 404 → null. */
export async function fetchMainVpnLinks(): Promise<VpnGeneratedLinks | null> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const signal = defaultAbortSignal();
  let res: Response;
  try {
    res = await fetch(`${API_PREFIX}/api/vpn/main-links`, { headers, signal });
  } catch (e) {
    if (isAbortError(e)) {
      throw new Error(
        'Нет ответа от сервера вовремя. Убедитесь, что API запущен (uvicorn), а в dev порт совпадает с VITE_API_PROXY в Vite (по умолчанию 8010).',
      );
    }
    throw e;
  }
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await parseApiResponseError(res));
  return (await res.json()) as VpnGeneratedLinks;
}

export async function fetchVpnGenerateLinks(): Promise<VpnGeneratedLinks> {
  const res = await apiFetch('/api/vpn/generate-links', { method: 'POST' });
  return res.json();
}

export async function fetchGuestVpnLinks(): Promise<GuestVpnLinkOut[]> {
  const res = await apiFetch('/api/vpn/guest-links');
  return res.json();
}

export async function createGuestVpnLink(): Promise<GuestVpnLinkOut> {
  const res = await apiFetch('/api/vpn/guest-links', { method: 'POST' });
  return res.json();
}

export async function deleteGuestVpnLink(slot: number): Promise<void> {
  const res = await apiFetch(`/api/vpn/guest-links/${slot}`, { method: 'DELETE' });
  if (res.status !== 204) throw new Error('Неожиданный ответ сервера');
}

export type WhitelistRow = {
  id: number;
  email: string;
  role: string;
  config_fetch_count: number | null;
};

export async function fetchWhitelist(): Promise<WhitelistRow[]> {
  const res = await apiFetch('/api/admin/whitelist');
  return res.json();
}

export async function addWhitelistEmail(email: string): Promise<WhitelistRow> {
  const res = await apiFetch('/api/admin/whitelist', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
  return res.json();
}

export async function removeWhitelistEmail(email: string): Promise<void> {
  const q = new URLSearchParams({ email });
  const res = await apiFetch(`/api/admin/whitelist?${q.toString()}`, { method: 'DELETE' });
  if (res.status !== 204) throw new Error('Неожиданный ответ сервера');
}

export async function patchWhitelistRole(email: string, role: string): Promise<WhitelistRow> {
  const res = await apiFetch('/api/admin/whitelist/role', {
    method: 'PATCH',
    body: JSON.stringify({ email, role }),
  });
  return res.json();
}

export async function fetchMasterSubscription(): Promise<MasterSubscriptionResponse> {
  const res = await apiFetch('/api/admin/master-subscription');
  return res.json();
}

export async function patchMasterSubscription(
  url: string,
  settings: Pick<
    MasterSubscriptionResponse,
    | 'server_name_mode'
    | 'server_name_rules'
    | 'output_format_mode'
    | 'bypass_render_mode'
    | 'slovo_ru_direct_override'
    | 'slovo_ru_direct_routes'
  >,
): Promise<MasterSubscriptionResponse> {
  const res = await apiFetch('/api/admin/master-subscription', {
    method: 'PATCH',
    body: JSON.stringify({ master_subscription_url: url, ...settings }),
  });
  return res.json();
}
