import { create } from "zustand";

const API_BASE = process.env.REACT_APP_API_URL || "/api";

// We only persist NON-SENSITIVE org info (name/slug/logo) for gating and
// display. The actual org token lives in an httpOnly cookie the browser
// attaches automatically, so it never touches JavaScript/localStorage.
const ORG_INFO_KEY = "org_info";

export interface Organization {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  logo_url?: string | null;
  created_at?: string | null;
}

interface OrgState {
  organization: Organization | null;
  loading: boolean;
  error: string | null;

  loginOrg: (identifier: string, password: string) => Promise<void>;
  registerOrg: (payload: any) => Promise<{ organization: Organization; admin: { email: string; role: string; name: string } }>;
  logoutOrg: () => Promise<void>;
  restoreOrgSession: () => void;
  refreshOrg: () => Promise<void>;
  setError: (msg: string | null) => void;
}

function readStoredOrg(): Organization | null {
  try {
    const raw = localStorage.getItem(ORG_INFO_KEY);
    return raw ? (JSON.parse(raw) as Organization) : null;
  } catch {
    return null;
  }
}

export const useOrgStore = create<OrgState>((set, get) => ({
  organization: readStoredOrg(),
  loading: false,
  error: null,

  loginOrg: async (identifier, password) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_BASE}/organizations/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, password }),
      });

      if (!response.ok) {
        let message = `Organization login failed (${response.status})`;
        try {
          const body = await response.json();
          message = body.error || message;
        } catch {
          /* non-JSON */
        }
        throw new Error(message);
      }

      const data = await response.json();
      // Persist only the display info; the token is in the httpOnly cookie.
      localStorage.setItem(ORG_INFO_KEY, JSON.stringify(data.organization));

      set({
        organization: data.organization,
        loading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Organization login failed";
      set({ error: message, loading: false });
      throw err;
    }
  },

  registerOrg: async (payload) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_BASE}/organizations/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const err: any = new Error(data.error || `Signup failed (${response.status})`);
        err.fields = data.fields;
        throw err;
      }
      // The register endpoint sets the org session cookie; persist display info.
      localStorage.setItem(ORG_INFO_KEY, JSON.stringify(data.organization));
      set({ organization: data.organization, loading: false });
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Signup failed";
      set({ error: message, loading: false });
      throw err;
    }
  },

  logoutOrg: async () => {
    try {
      // Clears both the org and user httpOnly cookies server-side.
      await fetch(`${API_BASE}/organizations/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      /* best-effort; clear local state regardless */
    }
    localStorage.removeItem(ORG_INFO_KEY);
    set({ organization: null, error: null });
  },

  restoreOrgSession: () => {
    const info = readStoredOrg();
    if (info) {
      set({ organization: info });
      // Best-effort revalidate against the cookie; on failure, clear.
      get().refreshOrg().catch(() => {
        get().logoutOrg();
      });
    }
  },

  refreshOrg: async () => {
    const response = await fetch(`${API_BASE}/organizations/me`, {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error("Organization session invalid");
    }
    const org = await response.json();
    localStorage.setItem(ORG_INFO_KEY, JSON.stringify(org));
    set({ organization: org });
  },

  setError: (msg) => set({ error: msg }),
}));
