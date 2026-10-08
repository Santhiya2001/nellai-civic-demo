let accessToken: string | null = null;
let refreshPromise: Promise<boolean> | null = null;
export function setToken(token: string | null) { accessToken = token; }
export async function refreshSession(): Promise<boolean> {
  if (!refreshPromise) refreshPromise = fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: '{}' }).then(async r => { if (!r.ok) { setToken(null); return false; } setToken((await r.json()).access_token); return true; }).catch(() => false).finally(() => { refreshPromise = null; });
  return refreshPromise;
}
export async function request<T = unknown>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'include' });
  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    if (await refreshSession()) return request<T>(path, options, false);
    window.dispatchEvent(new Event('session-expired'));
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Server unavailable' }));
    throw new Error(Array.isArray(body.detail) ? body.detail.map((d: {msg: string}) => d.msg).join('. ') : body.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? undefined as T : response.json();
}
export const post = <T = unknown>(path: string, data: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(data) });
export const put = <T = unknown>(path: string, data: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(data) });
export async function upload(file: File) { const data = new FormData(); data.append('file', file); return request<{id: string}>('/uploads', { method: 'POST', body: data }); }
export async function photoUrl(id: string) { const response = await fetch(`/api/v1/uploads/${id}`, { headers: { Authorization: `Bearer ${accessToken}` } }); if (!response.ok) throw new Error('Photograph unavailable'); return URL.createObjectURL(await response.blob()); }
