import { create } from "zustand";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5001/api";

const ORG_TOKEN_KEY = "org_token";
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
  orgToken: string | null;
  organization: Organization | null;
  loading: boolean;
  error: string | null;

  loginOrg: (identifier: string, password: string) => Promise<void>;
  logoutOrg: () => void;
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
  orgToken: localStorage.getItem(ORG_TOKEN_KEY),
  organization: readStoredOrg(),
  loading: false,
  error: null,

  loginOrg: async (identifier, password) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_BASE}/organizations/login`, {
        method: "POST",
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
      localStorage.setItem(ORG_TOKEN_KEY, data.org_token);
      localStorage.setItem(ORG_INFO_KEY, JSON.stringify(data.organization));

      set({
        orgToken: data.org_token,
        organization: data.organization,
        loading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Organization login failed";
      set({ error: message, loading: false });
      throw err;
    }
  },

  logoutOrg: () => {
    localStorage.removeItem(ORG_TOKEN_KEY);
    localStorage.removeItem(ORG_INFO_KEY);
    // Also clear any user session so we don't leak across orgs.
    localStorage.removeItem("auth_token");
    set({ orgToken: null, organization: null, error: null });
  },

  restoreOrgSession: () => {
    const token = localStorage.getItem(ORG_TOKEN_KEY);
    const info = readStoredOrg();
    if (token && info) {
      set({ orgToken: token, organization: info });
      // Best-effort revalidate; on failure, clear.
      get().refreshOrg().catch(() => {
        get().logoutOrg();
      });
    }
  },

  refreshOrg: async () => {
    const { orgToken } = get();
    if (!orgToken) return;
    const response = await fetch(`${API_BASE}/organizations/me`, {
      headers: { "X-Org-Token": orgToken },
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
