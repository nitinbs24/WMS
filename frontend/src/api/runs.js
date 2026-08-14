import { api } from './client';

export const runsApi = {
  list:        ()                      => api.get('/api/v1/runs'),
  get:         (id)                    => api.get(`/api/v1/runs/${id}`),
  create:      (goal, algorithm, scope) => api.post('/api/v1/runs', { goal, algorithm, scope }),
  assignments: (id)                    => api.get(`/api/v1/runs/${id}/assignments`),
  exceptions:  (id)                    => api.get(`/api/v1/runs/${id}/exceptions`),
  rollback:    (id)                    => api.post(`/api/v1/runs/${id}/rollback`),
  report:      (id)                    => api.get(`/api/v1/runs/${id}/report`),
  exportCsv:   (id)                    => `/api/v1/runs/${id}/export.csv`,
};
