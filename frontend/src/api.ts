import axios from "axios";
import type { Plan, SchoolProfile, Teacher, Subject } from "./types";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

// Create axios instance with request interceptor
const axiosInstance = axios.create({
  baseURL: API_BASE,
});

// Add JWT token to all requests
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 responses by clearing auth
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth_token");
      window.location.href = "/login";
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
  },

  timetable: {
    list: async () => {
      const { data } = await axiosInstance.get("/timetable");
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
  },

  stats: async () => {
    const { data } = await axiosInstance.get("/stats");
    return data;
  },
};
