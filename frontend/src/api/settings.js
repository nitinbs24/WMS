import { api } from './client';

export const settingsApi = {
  getThresholds: () => api.get('/api/v1/settings/thresholds'),
  updateThresholds: (data) => api.put('/api/v1/settings/thresholds', data),
};
