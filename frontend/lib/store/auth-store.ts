import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authClient, AuthUser } from '../api/auth-client';
import { useConversationStore } from './conversation-store';

interface AuthState {
  token: string | null;
  refresh_token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  verifyToken: () => Promise<void>;
  clearError: () => void;
}

const _rawUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const _cleanBase = _rawUrl.replace(/\/+$/, '');
const API_BASE = _cleanBase.endsWith('/api/v1') ? _cleanBase : `${_cleanBase}/api/v1`;

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refresh_token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string, rememberMe = false) => {
        set({ isLoading: true, error: null });
        try {
          const data = await authClient.login(email, password, rememberMe);
          set({
            token: data.access_token,
            refresh_token: data.refresh_token,
            user: data.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          // Hydrate history from backend, then open a fresh blank chat
          await useConversationStore.getState().init(data.user.id.toString());
          await useConversationStore.getState().createNewSession();
        } catch (e: any) {
          set({ isLoading: false, error: e.message || 'Login failed.' });
          throw e;
        }
      },

      register: async (fullName: string, email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const data = await authClient.register(fullName, email, password);
          set({
            token: data.access_token,
            refresh_token: data.refresh_token,
            user: data.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          // Init history (empty for new user), then open a fresh blank chat
          await useConversationStore.getState().init(data.user.id.toString());
          await useConversationStore.getState().createNewSession();
        } catch (e: any) {
          set({ isLoading: false, error: e.message || 'Registration failed.' });
          throw e;
        }
      },

      logout: () => {
        set({
          token: null,
          refresh_token: null,
          user: null,
          isAuthenticated: false,
          error: null,
        });
        // Clear local session state on logout
        useConversationStore.getState().init(null);
      },

      verifyToken: async () => {
        const { token, refresh_token } = get();
        if (!token) {
          set({ isAuthenticated: false, user: null });
          useConversationStore.getState().init(null);
          return;
        }

        try {
          const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (!res.ok) {
            // Try refresh
            if (refresh_token) {
              try {
                const refreshed = await authClient.refreshToken(refresh_token);
                set({ 
                  token: refreshed.access_token, 
                  refresh_token: refreshed.refresh_token,
                  user: refreshed.user, 
                  isAuthenticated: true 
                });
                // Hydrate sessions with the refreshed user
                await useConversationStore.getState().init(refreshed.user.id.toString());
                return;
              } catch {
                set({ token: null, refresh_token: null, user: null, isAuthenticated: false });
                useConversationStore.getState().init(null);
                return;
              }
            }
            set({ token: null, refresh_token: null, user: null, isAuthenticated: false });
            useConversationStore.getState().init(null);
            return;
          }

          const user = await res.json();
          set({ user, isAuthenticated: true });
          // Hydrate sessions for returning user on page refresh
          await useConversationStore.getState().init(user.id.toString());
        } catch {
          set({ token: null, refresh_token: null, user: null, isAuthenticated: false });
          useConversationStore.getState().init(null);
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'fineanalyst-auth',
      partialize: (state) => ({ token: state.token, refresh_token: state.refresh_token, user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
