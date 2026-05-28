import { create } from "zustand";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5001/api";

export interface User {
  id: number;
  name: string;
  email: string;
  role: "admin" | "principal" | "teacher" | "student";
  batch_id?: number;
  teacher_id?: number;
  assigned_batches?: number[];
  subjects?: number[];
}

interface AuthState {
  token: string | null;
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  
  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  getCurrentUser: () => Promise<void>;
  restoreSession: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem("auth_token") || null,
  user: null,
  loading: false,
  error: null,
  isAuthenticated: !!localStorage.getItem("auth_token"),

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const orgToken = localStorage.getItem("org_token");
      if (!orgToken) {
        throw new Error("Please log in to your organization first.");
      }

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Org-Token": orgToken,
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        let errorMessage = `Login failed: ${response.status}`;
        try {
          const data = await response.json();
          errorMessage = data.error || errorMessage;
        } catch {
          /* non-JSON */
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      localStorage.setItem("auth_token", data.token);

      set({
        token: data.token,
        user: data.user,
        isAuthenticated: true,
        loading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Login failed";
      set({ error: message, loading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem("auth_token");
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      error: null,
    });
  },

  setToken: (token: string) => {
    localStorage.setItem("auth_token", token);
    set({ token, isAuthenticated: true });
  },

  setUser: (user: User | null) => {
    set({ user });
  },

  setLoading: (loading: boolean) => {
    set({ loading });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  getCurrentUser: async () => {
    const state = get();
    if (!state.token) {
      return;
    }

    set({ loading: true });
    try {
      const orgToken = localStorage.getItem("org_token");
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${state.token}`,
          ...(orgToken ? { "X-Org-Token": orgToken } : {}),
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch user");
      }

      const user = await response.json();
      set({ user, loading: false });
    } catch (error) {
      // Token is invalid, logout
      set({ loading: false });
      get().logout();
    }
  },

  restoreSession: () => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      set({ token, isAuthenticated: true });
      get().getCurrentUser();
    }
  },
}));
