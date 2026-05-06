import axios from "axios";
import type { Plan, SchoolProfile, Teacher, Subject } from "./types";

const API_BASE = process.env.REACT_APP_API_URL || "/api";

export const api = {
  health: async () => {
    const { data } = await axios.get(`${API_BASE}/health`);
    return data;
  },

  plans: {
    list: async (): Promise<Plan[]> => {
      const { data } = await axios.get(`${API_BASE}/plans`);
      return data;
    },

    get: async (id: number): Promise<Plan> => {
      const { data } = await axios.get(`${API_BASE}/plans/${id}`);
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
      const { data } = await axios.post(`${API_BASE}/plans`, {
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
      const { data } = await axios.put(`${API_BASE}/plans/${id}`, updates);
      return data;
    },

    delete: async (id: number): Promise<void> => {
      await axios.delete(`${API_BASE}/plans/${id}`);
    },

    generate: async (
      id: number
    ): Promise<{ plan_id: number; timetable: any[][]; warnings: string[] }> => {
      const { data } = await axios.post(`${API_BASE}/plans/${id}/generate`);
      return data;
    },

    exportCSV: async (id: number): Promise<string> => {
      const { data } = await axios.get(`${API_BASE}/plans/${id}/export/csv`);
      return data;
    },
  },

  sample: async () => {
    const { data } = await axios.get(`${API_BASE}/sample-data`);
    return data;
  },
};
