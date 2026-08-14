import { api } from './client';

export const layoutApi = {
  get: () => api.get('/api/v1/layout'),
};
