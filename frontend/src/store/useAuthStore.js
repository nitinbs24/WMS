import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Auth store — persists JWT token and user info to localStorage.
 * Only UI-safe data (role, name) stored; password never touched.
 */
export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null, // { id, name, email, role }

      setAuth: ({ token, refreshToken, user }) =>
        set({ token, refreshToken, user }),

      clearAuth: () =>
        set({ token: null, refreshToken: null, user: null }),
    }),
    { name: 'warehaven-auth' },
  ),
);
