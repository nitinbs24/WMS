import { api } from './client';

export const authApi = {
  login:   (email, password) => api.post('/api/v1/auth/login', { email, password }),
  refresh: (refreshToken)    => api.post('/api/v1/auth/refresh', { refresh_token: refreshToken }),
  me:      ()                => api.get('/api/v1/auth/me'),
};
