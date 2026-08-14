import { api } from './client';

export const layoutApi = {
  get:         () => api.get('/api/v1/layout'),
  getImport:   (id) => api.get(`/api/v1/layout/imports/${id}`),
  applyImport: (id) => api.post(`/api/v1/layout/imports/${id}/apply`),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetch('/api/v1/layout/import', {
      method: 'POST',
      headers: (() => {
        const state = JSON.parse(localStorage.getItem('warehaven-auth') || '{}');
        const token = state?.state?.token;
        return token ? { Authorization: `Bearer ${token}` } : {};
      })(),
      body: form,
    }).then((r) => r.json());
  },
};
