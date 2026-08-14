/**
 * Typed REST API client — all calls go through here.
 * Base URL comes from Vite env var (proxied to FastAPI in dev).
 */
const BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Core fetch wrapper with JSON handling and auth header injection.
 */
export async function apiRequest(path, options = {}) {
  const token = (() => {
    try {
      const state = JSON.parse(localStorage.getItem('warehaven-auth') || '{}');
      return state?.state?.token ?? null;
    } catch { return null; }
  })();

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw Object.assign(new Error(err.message || err.detail || 'API error'), {
      status: res.status,
      body: err,
    });
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get:    (path)        => apiRequest(path),
  post:   (path, body)  => apiRequest(path, { method: 'POST', body: JSON.stringify(body) }),
  patch:  (path, body)  => apiRequest(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put:    (path, body)  => apiRequest(path, { method: 'PUT',   body: JSON.stringify(body) }),
  delete: (path)        => apiRequest(path, { method: 'DELETE' }),
};
