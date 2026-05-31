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
  is_class_teacher?: boolean;
  class_teacher_batch_id?: number | null;
  class_teacher_grade?: string;
  class_teacher_section?: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  getCurrentUser: () => Promise<void>;
  restoreSession: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  // Start in a loading state so guarded routes wait for the cookie-based
  // /auth/me rehydrate instead of briefly bouncing to /login on every refresh.
  loading: true,
  error: null,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      // The org session is an httpOnly cookie the browser sends automatically;
      // we just confirm one exists locally to show a friendlier message.
      if (!localStorage.getItem("org_info")) {
        throw new Error("Please log in to your organization first.");
      }

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
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
      // No token is stored anywhere; the httpOnly cookie carries it.
      set({
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

  logout: async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      /* best-effort; clear local state regardless */
    }
    set({
      user: null,
      isAuthenticated: false,
      error: null,
      loading: false,
    });
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
    set({ loading: true });
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        credentials: "include",
      });

      if (!response.ok) {
        // No valid session cookie -> treat as logged out (no redirect here).
        set({ user: null, isAuthenticated: false, loading: false });
        return;
      }

      const user = await response.json();
      set({ user, isAuthenticated: true, loading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },

  restoreSession: () => {
    // Cookie-based: just ask the server who we are. If the cookie is missing or
    // expired, getCurrentUser resolves to a logged-out state.
    get().getCurrentUser();
  },
}));
