import axios from "axios";
import type { Plan, SchoolProfile, Teacher, Subject } from "./types";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5001/api";

// Auth now rides on httpOnly cookies (access_token / org_token) that the
// browser attaches automatically. withCredentials makes axios include them; we
// no longer read or send any token from JavaScript, which removes the
// localStorage XSS token-theft vector.
const axiosInstance = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Handle 401 responses by bouncing the user to the right login step. We can no
// longer read the (httpOnly) tokens, so we infer org-session presence from the
// non-sensitive org info we keep in localStorage for UI purposes.
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const hasOrg = !!localStorage.getItem("org_info");
      const target = hasOrg ? "/login" : "/";
      if (window.location.pathname !== target) {
        window.location.href = target;
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  health: async () => {
    const { data } = await axiosInstance.get("/health");
    return data;
  },

  plans: {
    list: async (): Promise<Plan[]> => {
      const { data } = await axiosInstance.get("/plans");
      return data;
    },

    get: async (id: number): Promise<Plan> => {
      const { data } = await axiosInstance.get(`/plans/${id}`);
      return data;
    },

    create: async ({
      title,
      description,
      school_profile,
      teachers,
      subjects,
    }: {
      title: string;
      description: string;
      school_profile: SchoolProfile;
      teachers: Teacher[];
      subjects: Subject[];
    }): Promise<Plan> => {
      const { data } = await axiosInstance.post("/plans", {
        title,
        description,
        school_profile,
        teachers,
        subjects,
      });
      return data;
    },

    update: async (
      id: number,
      updates: Partial<Plan>
    ): Promise<Plan> => {
      const { data } = await axiosInstance.put(`/plans/${id}`, updates);
      return data;
    },

    delete: async (id: number): Promise<void> => {
      await axiosInstance.delete(`/plans/${id}`);
    },

    generate: async (
      id: number
    ): Promise<{ plan_id: number; timetable: any[][]; warnings: string[] }> => {
      const { data } = await axiosInstance.post(`/plans/${id}/generate`);
      return data;
    },

    exportCSV: async (id: number): Promise<string> => {
      const { data } = await axiosInstance.get(`/plans/${id}/export/csv`);
      return data;
    },
  },

  admin: {
    // School Configuration
    config: {
      get: async () => {
        const { data } = await axiosInstance.get("/admin/school-config");
        return data;
      },
      update: async (config: any) => {
        const { data } = await axiosInstance.post("/admin/school-config", config);
        return data;
      },
    },

    // Teachers
    teachers: {
      list: async () => {
        const { data } = await axiosInstance.get("/admin/teachers");
        return data;
      },
      get: async (id: number) => {
        const { data } = await axiosInstance.get(`/admin/teachers/${id}`);
        return data;
      },
      create: async (teacher: any) => {
        const { data } = await axiosInstance.post("/admin/teachers", teacher);
        return data;
      },
      update: async (id: number, updates: any) => {
        const { data } = await axiosInstance.put(`/admin/teachers/${id}`, updates);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/teachers/${id}`);
      },
      getPreferences: async (id: number) => {
        const { data } = await axiosInstance.get(`/admin/teachers/${id}/preferences`);
        return data;
      },
      savePreferences: async (id: number, prefs: any) => {
        const { data } = await axiosInstance.put(`/admin/teachers/${id}/preferences`, prefs);
        return data;
      },
      autoAssignSections: async () => {
        const { data } = await axiosInstance.post("/admin/teachers/auto-assign-sections", {});
        return data;
      },
    },

    // Workload stats that drive the suggested per-teacher contact target
    workload: {
      summary: async () => {
        const { data } = await axiosInstance.get("/admin/workload/summary");
        return data;
      },
    },

    // Batches
    batches: {
      list: async () => {
        const { data } = await axiosInstance.get("/admin/batches");
        return data;
      },
      get: async (id: number) => {
        const { data } = await axiosInstance.get(`/admin/batches/${id}`);
        return data;
      },
      create: async (batch: any) => {
        const { data } = await axiosInstance.post("/admin/batches", batch);
        return data;
      },
      update: async (id: number, updates: any) => {
        const { data } = await axiosInstance.put(`/admin/batches/${id}`, updates);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/batches/${id}`);
      },
    },

    // Subjects
    subjects: {
      list: async () => {
        const { data } = await axiosInstance.get("/admin/subjects");
        return data;
      },
      get: async (id: number) => {
        const { data } = await axiosInstance.get(`/admin/subjects/${id}`);
        return data;
      },
      create: async (subject: any) => {
        const { data } = await axiosInstance.post("/admin/subjects", subject);
        return data;
      },
      update: async (id: number, updates: any) => {
        const { data } = await axiosInstance.put(`/admin/subjects/${id}`, updates);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/subjects/${id}`);
      },
    },

    // Charge catalog (non-teaching duties assignable to teachers)
    charges: {
      list: async () => {
        const { data } = await axiosInstance.get("/admin/charges");
        return data;
      },
      create: async (charge: any) => {
        const { data } = await axiosInstance.post("/admin/charges", charge);
        return data;
      },
      update: async (id: number, updates: any) => {
        const { data } = await axiosInstance.put(`/admin/charges/${id}`, updates);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/charges/${id}`);
      },
    },

    // Students (admin + principal full; class teacher scoped server-side)
    students: {
      list: async (params: { class_grade?: string; section?: string; status?: string; q?: string } = {}) => {
        const { data } = await axiosInstance.get("/admin/students", { params });
        return data;
      },
      sections: async (class_grade: string) => {
        const { data } = await axiosInstance.get("/admin/students/sections", { params: { class_grade } });
        return data;
      },
      create: async (student: any) => {
        const { data } = await axiosInstance.post("/admin/students", student);
        return data;
      },
      update: async (id: number, updates: any) => {
        const { data } = await axiosInstance.put(`/admin/students/${id}`, updates);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/students/${id}`);
      },
      transfer: async (id: number, payload: { section: string; class_grade?: string }) => {
        const { data } = await axiosInstance.post(`/admin/students/${id}/transfer`, payload);
        return data;
      },
      resequenceRolls: async (payload: { class_grade: string; section: string }) => {
        const { data } = await axiosInstance.post("/admin/students/resequence-rolls", payload);
        return data;
      },
    },

    // Pinned / fixed periods the scheduler must honor
    pinnedSlots: {
      list: async () => {
        const { data } = await axiosInstance.get("/admin/pinned-slots");
        return data;
      },
      create: async (pin: any) => {
        const { data } = await axiosInstance.post("/admin/pinned-slots", pin);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/pinned-slots/${id}`);
      },
    },
  },

  timetable: {
    list: async () => {
      const { data } = await axiosInstance.get("/timetable/list");
      return data;
    },
    get: async (id: number) => {
      const { data } = await axiosInstance.get(`/timetable/${id}`);
      return data;
    },
    generate: async (name: string, description?: string) => {
      const { data } = await axiosInstance.post("/timetable/generate", {
        name,
        description,
      });
      return data;
    },
    publish: async (id: number) => {
      const { data } = await axiosInstance.post(`/timetable/${id}/publish`);
      return data;
    },
    delete: async (id: number) => {
      const { data } = await axiosInstance.delete(`/timetable/${id}`);
      return data;
    },
    getBatchSchedule: async (batchId: number) => {
      const { data } = await axiosInstance.get(`/timetable/batch/${batchId}`);
      return data;
    },
    
    // Conflict Detection & Validation
    validate: async (id: number) => {
      const { data } = await axiosInstance.get(`/timetable/${id}/validate`);
      return data;
    },
    getSummary: async (id: number) => {
      const { data } = await axiosInstance.get(`/timetable/${id}/conflicts/summary`);
      return data;
    },
    getConflictsByType: async (id: number) => {
      const { data } = await axiosInstance.get(`/timetable/${id}/conflicts/by-type`);
      return data;
    },

    // Manual editing (drag-and-drop grid)
    getGrid: async (id: number) => {
      const { data } = await axiosInstance.get(`/timetable/${id}/grid`);
      return data;
    },
    updateSlot: async (
      id: number,
      payload: { batch_id: number; day: string; period_number: number; subject_id: number | null; teacher_id: number | null; room?: string | null }
    ) => {
      const { data } = await axiosInstance.patch(`/timetable/${id}/slot`, payload);
      return data;
    },
    swapSlots: async (
      id: number,
      payload: { batch_id: number; a: { day: string; period_number: number }; b: { day: string; period_number: number } }
    ) => {
      const { data } = await axiosInstance.patch(`/timetable/${id}/swap`, payload);
      return data;
    },
    pinSlot: async (id: number, payload: { batch_id: number; day: string; period_number: number }) => {
      const { data } = await axiosInstance.patch(`/timetable/${id}/pin`, payload);
      return data;
    },
    unpinSlot: async (id: number, payload: { batch_id: number; day: string; period_number: number }) => {
      const { data } = await axiosInstance.patch(`/timetable/${id}/unpin`, payload);
      return data;
    },
    validateGrid: async (id: number, slots: any[]) => {
      const { data } = await axiosInstance.post(`/timetable/${id}/validate-grid`, { slots });
      return data;
    },
    saveVersion: async (id: number, payload: { name?: string; slots?: any[] }) => {
      const { data } = await axiosInstance.post(`/timetable/${id}/save-version`, payload);
      return data;
    },
  },

  analytics: {
    get: async (planId: number) => {
      const { data } = await axiosInstance.get(`/analytics/${planId}`);
      return data;
    },
  },

  stats: async () => {
    const { data } = await axiosInstance.get("/stats");
    return data;
  },

  // Direct HTTP methods for flexible endpoints
  get: (url: string, config?: any) => axiosInstance.get(url, config),
  post: (url: string, data?: any, config?: any) => axiosInstance.post(url, data, config),
  put: (url: string, data?: any, config?: any) => axiosInstance.put(url, data, config),
  delete: (url: string, config?: any) => axiosInstance.delete(url, config),
  patch: (url: string, data?: any, config?: any) => axiosInstance.patch(url, data, config),
};
