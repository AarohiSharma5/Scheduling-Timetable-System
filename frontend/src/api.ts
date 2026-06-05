import axios from "axios";
import type { Plan, SchoolProfile, Teacher, Subject } from "./types";

// Default to a SAME-ORIGIN relative base ("/api") so the app talks to whatever
// host/port served it (the backend serves the built frontend on the same
// origin). Override with REACT_APP_API_URL only when the API lives elsewhere.
const API_BASE = process.env.REACT_APP_API_URL || "/api";

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

    // Rooms / facilities
    rooms: {
      list: async () => {
        const { data } = await axiosInstance.get("/admin/rooms");
        return data;
      },
      create: async (room: any) => {
        const { data } = await axiosInstance.post("/admin/rooms", room);
        return data;
      },
      update: async (id: number, updates: any) => {
        const { data } = await axiosInstance.put(`/admin/rooms/${id}`, updates);
        return data;
      },
      delete: async (id: number) => {
        await axiosInstance.delete(`/admin/rooms/${id}`);
      },
      autoGenerate: async (options: any = {}) => {
        const { data } = await axiosInstance.post("/admin/rooms/auto-generate", options);
        return data;
      },
      // One-shot: add sections to fit capacity, generate rooms across floors,
      // assign home rooms, and redistribute students within the limit.
      setup: async (options: any = {}) => {
        const { data } = await axiosInstance.post("/admin/rooms/setup", options);
        return data;
      },
      assignHome: async () => {
        const { data } = await axiosInstance.post("/admin/rooms/assign-home", {});
        return data;
      },
      // Swap the home classrooms of two sections.
      exchange: async (batch_a: number, batch_b: number) => {
        const { data } = await axiosInstance.post("/admin/rooms/exchange", { batch_a, batch_b });
        return data;
      },
    },

    // Senior-school streams (Science/Commerce/Humanities per grade)
    streams: {
      list: async () => (await axiosInstance.get("/admin/streams")).data,
      create: async (s: any) => (await axiosInstance.post("/admin/streams", s)).data,
      update: async (id: number, u: any) => (await axiosInstance.put(`/admin/streams/${id}`, u)).data,
      delete: async (id: number) => { await axiosInstance.delete(`/admin/streams/${id}`); },
    },

    // Subject combinations within a stream (PCM/PCB/...)
    combinations: {
      list: async () => (await axiosInstance.get("/admin/subject-combinations")).data,
      create: async (c: any) => (await axiosInstance.post("/admin/subject-combinations", c)).data,
      update: async (id: number, u: any) => (await axiosInstance.put(`/admin/subject-combinations/${id}`, u)).data,
      delete: async (id: number) => { await axiosInstance.delete(`/admin/subject-combinations/${id}`); },
    },

    // Dynamic teaching groups (homeroom / elective / language)
    teachingGroups: {
      list: async (params: { grade?: string; group_type?: string } = {}) =>
        (await axiosInstance.get("/admin/teaching-groups", { params })).data,
      get: async (id: number) => (await axiosInstance.get(`/admin/teaching-groups/${id}`)).data,
      generate: async (options: any = {}) =>
        (await axiosInstance.post("/admin/teaching-groups/generate", options)).data,
      create: async (g: any) => (await axiosInstance.post("/admin/teaching-groups", g)).data,
      update: async (id: number, u: any) => (await axiosInstance.put(`/admin/teaching-groups/${id}`, u)).data,
      delete: async (id: number) => { await axiosInstance.delete(`/admin/teaching-groups/${id}`); },
      members: async (id: number, body: { student_id: number; action?: "add" | "remove"; from_group_id?: number }) =>
        (await axiosInstance.post(`/admin/teaching-groups/${id}/members`, body)).data,
      validate: async (timetable_id?: number) =>
        (await axiosInstance.get("/admin/teaching-groups/validate", { params: timetable_id ? { timetable_id } : {} })).data,
    },

    // Per-class subject frequency / priority configuration
    classSubjectConfig: {
      list: async (grade?: string) =>
        (await axiosInstance.get("/admin/class-subject-config", { params: grade ? { grade } : {} })).data,
      save: async (grade: string, items: any[]) =>
        (await axiosInstance.post("/admin/class-subject-config", { grade, items })).data,
      delete: async (id: number) => { await axiosInstance.delete(`/admin/class-subject-config/${id}`); },
      validatePlanning: async (timetable_id?: number) =>
        (await axiosInstance.get("/admin/timetable-planning/validate", { params: timetable_id ? { timetable_id } : {} })).data,
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

    // Bulk import (CSV / XLSX) for students & teachers
    imports: {
      preview: async (entity: "students" | "teachers", file: File) => {
        const form = new FormData();
        form.append("file", file);
        const { data } = await axiosInstance.post(`/admin/import/${entity}/preview`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        return data;
      },
      commit: async (
        entity: "students" | "teachers",
        rows: any[],
        skip_invalid: boolean
      ) => {
        const { data } = await axiosInstance.post(`/admin/import/${entity}/commit`, {
          rows,
          skip_invalid,
        });
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
    getTeacherSchedule: async (teacherId: number) => {
      const { data } = await axiosInstance.get(`/timetable/teacher/${teacherId}`);
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
    // Assign a substitute when a (homeroom) teacher is absent. Omit
    // substitute_teacher_id (or pass preview) to list available candidates.
    substituteHomeroom: async (
      id: number,
      payload: {
        batch_id?: number;
        teacher_id?: number;
        day: string;
        periods?: number[];
        substitute_teacher_id?: number;
        preview?: boolean;
      }
    ) => {
      const { data } = await axiosInstance.post(`/timetable/${id}/substitute-homeroom`, payload);
      return data;
    },
  },

  analytics: {
    get: async (planId: number) => {
      const { data } = await axiosInstance.get(`/analytics/${planId}`);
      return data;
    },
    overview: async () => (await axiosInstance.get("/analytics/overview")).data,
  },

  // First-login / password management + in-app token links
  auth: {
    changePassword: async (payload: {
      current_password: string;
      new_password: string;
      complete_profile?: { name?: string; phone?: string };
    }) => (await axiosInstance.post("/auth/change-password", payload)).data,
    forgotPassword: async (email: string) =>
      (await axiosInstance.post("/auth/forgot-password", { email })).data,
    resetInfo: async (token: string) =>
      (await axiosInstance.get(`/auth/reset-password/${token}`)).data,
    resetPassword: async (token: string, new_password: string) =>
      (await axiosInstance.post(`/auth/reset-password/${token}`, { new_password })).data,
  },

  // Admin-issued invitations (in-app token links)
  invitations: {
    list: async () => (await axiosInstance.get("/invitations")).data,
    create: async (payload: { email: string; name?: string; role: string }) =>
      (await axiosInstance.post("/invitations", payload)).data,
    revoke: async (id: number) =>
      (await axiosInstance.post(`/invitations/${id}/revoke`)).data,
    info: async (token: string) =>
      (await axiosInstance.get(`/invitations/accept/${token}`)).data,
    accept: async (
      token: string,
      payload: { name?: string; password: string; phone?: string }
    ) => (await axiosInstance.post(`/invitations/accept/${token}`, payload)).data,
  },

  attendance: {
    classes: async () => (await axiosInstance.get("/attendance/classes")).data,
    roster: async (params: { batch_id: number; date?: string; period_number?: number }) =>
      (await axiosInstance.get("/attendance/roster", { params })).data,
    mark: async (payload: {
      batch_id: number;
      date: string;
      period_number?: number;
      subject_id?: number | null;
      records: { student_id: number; status: string; remarks?: string }[];
    }) => (await axiosInstance.post("/attendance/mark", payload)).data,
    summary: async (params: { batch_id: number; from?: string; to?: string; period_number?: number }) =>
      (await axiosInstance.get("/attendance/summary", { params })).data,
    student: async (studentId: number, params: { from?: string; to?: string; period_number?: number } = {}) =>
      (await axiosInstance.get(`/attendance/student/${studentId}`, { params })).data,
    today: async (date?: string) =>
      (await axiosInstance.get("/attendance/today", { params: date ? { date } : {} })).data,
  },

  exams: {
    meta: async () => (await axiosInstance.get("/exams/meta")).data,
    list: async () => (await axiosInstance.get("/exams")).data,
    create: async (payload: {
      name: string;
      term?: string;
      exam_type?: string;
      max_marks?: number;
      start_date?: string;
      end_date?: string;
    }) => (await axiosInstance.post("/exams", payload)).data,
    update: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/exams/${id}`, payload)).data,
    remove: async (id: number) => (await axiosInstance.delete(`/exams/${id}`)).data,
    publish: async (id: number, published = true) =>
      (await axiosInstance.post(`/exams/${id}/publish`, { published })).data,
    marksheet: async (id: number, params: { batch_id: number; subject_id: number }) =>
      (await axiosInstance.get(`/exams/${id}/marksheet`, { params })).data,
    saveMarks: async (
      id: number,
      payload: {
        batch_id: number;
        subject_id: number;
        max_marks?: number;
        records: { student_id: number; marks_obtained?: number | null; is_absent?: boolean; remarks?: string }[];
      }
    ) => (await axiosInstance.post(`/exams/${id}/marks`, payload)).data,
    results: async (id: number, params: { batch_id: number }) =>
      (await axiosInstance.get(`/exams/${id}/results`, { params })).data,
    student: async (studentId: number) =>
      (await axiosInstance.get(`/exams/student/${studentId}`)).data,
  },

  announcements: {
    list: async () => (await axiosInstance.get("/announcements")).data,
    audiences: async () => (await axiosInstance.get("/announcements/audiences")).data,
    create: async (payload: {
      title: string;
      body: string;
      audience: string;
      batch_id?: number | null;
    }) => (await axiosInstance.post("/announcements", payload)).data,
    update: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/announcements/${id}`, payload)).data,
    remove: async (id: number) => (await axiosInstance.delete(`/announcements/${id}`)).data,
  },

  parents: {
    list: async () => (await axiosInstance.get("/admin/parents")).data,
    create: async (payload: {
      name: string;
      email: string;
      phone?: string;
      relation?: string;
      student_ids: number[];
    }) => (await axiosInstance.post("/admin/parents", payload)).data,
    remove: async (id: number) => (await axiosInstance.delete(`/admin/parents/${id}`)).data,
    children: async () => (await axiosInstance.get("/parent/children")).data,
  },

  fees: {
    structures: async () => (await axiosInstance.get("/fees/structures")).data,
    createStructure: async (payload: {
      name: string; amount: number; grade?: string | null; term?: string; due_date?: string;
    }) => (await axiosInstance.post("/fees/structures", payload)).data,
    removeStructure: async (id: number) => (await axiosInstance.delete(`/fees/structures/${id}`)).data,
    generate: async (id: number) => (await axiosInstance.post(`/fees/structures/${id}/generate`)).data,
    invoices: async (params: { status?: string; grade?: string; student_id?: number } = {}) =>
      (await axiosInstance.get("/fees/invoices", { params })).data,
    createInvoice: async (payload: { student_id: number; title: string; amount: number; due_date?: string }) =>
      (await axiosInstance.post("/fees/invoices", payload)).data,
    invoice: async (id: number) => (await axiosInstance.get(`/fees/invoices/${id}`)).data,
    pay: async (id: number, payload: { amount: number; method?: string; reference?: string; paid_on?: string }) =>
      (await axiosInstance.post(`/fees/invoices/${id}/payments`, payload)).data,
    summary: async () => (await axiosInstance.get("/fees/summary")).data,
    student: async (studentId: number) => (await axiosInstance.get(`/fees/student/${studentId}`)).data,
    my: async () => (await axiosInstance.get("/fees/my")).data,
  },

  assignments: {
    meta: async () => (await axiosInstance.get("/assignments/meta")).data,
    list: async () => (await axiosInstance.get("/assignments")).data,
    create: async (payload: {
      title: string; batch_id: number; subject_id?: number | null; description?: string; due_date?: string;
    }) => (await axiosInstance.post("/assignments", payload)).data,
    update: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/assignments/${id}`, payload)).data,
    remove: async (id: number) => (await axiosInstance.delete(`/assignments/${id}`)).data,
    submit: async (id: number, payload: { note?: string } = {}) =>
      (await axiosInstance.post(`/assignments/${id}/submit`, payload)).data,
    submissions: async (id: number) => (await axiosInstance.get(`/assignments/${id}/submissions`)).data,
    grade: async (id: number, studentId: number, payload: { grade?: string; feedback?: string }) =>
      (await axiosInstance.put(`/assignments/${id}/submissions/${studentId}`, payload)).data,
    student: async (studentId: number) => (await axiosInstance.get(`/assignments/student/${studentId}`)).data,
  },

  calendar: {
    list: async (params: { year?: number; type?: string } = {}) =>
      (await axiosInstance.get("/calendar", { params })).data,
    create: async (payload: { title: string; event_type?: string; start_date: string; end_date?: string; description?: string }) =>
      (await axiosInstance.post("/calendar", payload)).data,
    update: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/calendar/${id}`, payload)).data,
    remove: async (id: number) => (await axiosInstance.delete(`/calendar/${id}`)).data,
  },

  library: {
    books: async (q?: string) => (await axiosInstance.get("/library/books", { params: q ? { q } : {} })).data,
    createBook: async (payload: { title: string; author?: string; isbn?: string; category?: string; total_copies?: number }) =>
      (await axiosInstance.post("/library/books", payload)).data,
    updateBook: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/library/books/${id}`, payload)).data,
    removeBook: async (id: number) => (await axiosInstance.delete(`/library/books/${id}`)).data,
    loans: async (status?: string) => (await axiosInstance.get("/library/loans", { params: status ? { status } : {} })).data,
    issue: async (payload: { book_id: number; student_id: number; due_on?: string }) =>
      (await axiosInstance.post("/library/loans", payload)).data,
    returnLoan: async (id: number) => (await axiosInstance.post(`/library/loans/${id}/return`)).data,
    student: async (studentId: number) => (await axiosInstance.get(`/library/student/${studentId}`)).data,
    my: async () => (await axiosInstance.get("/library/my")).data,
  },

  transport: {
    routes: async () => (await axiosInstance.get("/transport/routes")).data,
    createRoute: async (payload: { name: string; description?: string; driver_name?: string; driver_phone?: string; vehicle_no?: string; capacity?: number }) =>
      (await axiosInstance.post("/transport/routes", payload)).data,
    updateRoute: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/transport/routes/${id}`, payload)).data,
    removeRoute: async (id: number) => (await axiosInstance.delete(`/transport/routes/${id}`)).data,
    routeStudents: async (id: number) => (await axiosInstance.get(`/transport/routes/${id}/students`)).data,
    assign: async (id: number, payload: { student_id: number; stop_name?: string }) =>
      (await axiosInstance.post(`/transport/routes/${id}/students`, payload)).data,
    unassign: async (assignmentId: number) => (await axiosInstance.delete(`/transport/assignments/${assignmentId}`)).data,
    student: async (studentId: number) => (await axiosInstance.get(`/transport/student/${studentId}`)).data,
    my: async () => (await axiosInstance.get("/transport/my")).data,
  },

  inventory: {
    list: async (params: { category?: string; low?: string } = {}) =>
      (await axiosInstance.get("/inventory", { params })).data,
    create: async (payload: { name: string; category?: string; quantity?: number; unit?: string; min_quantity?: number; location?: string; notes?: string }) =>
      (await axiosInstance.post("/inventory", payload)).data,
    update: async (id: number, payload: Record<string, unknown>) =>
      (await axiosInstance.put(`/inventory/${id}`, payload)).data,
    adjust: async (id: number, delta: number) => (await axiosInstance.post(`/inventory/${id}/adjust`, { delta })).data,
    remove: async (id: number) => (await axiosInstance.delete(`/inventory/${id}`)).data,
    summary: async () => (await axiosInstance.get("/inventory/summary")).data,
  },

  messages: {
    directory: async () => (await axiosInstance.get("/messages/directory")).data,
    conversations: async () => (await axiosInstance.get("/messages/conversations")).data,
    thread: async (userId: number) => (await axiosInstance.get(`/messages/thread/${userId}`)).data,
    send: async (payload: { recipient_id: number; body: string }) =>
      (await axiosInstance.post("/messages", payload)).data,
    unreadCount: async () => (await axiosInstance.get("/messages/unread-count")).data,
  },

  leaves: {
    request: async (payload: { leave_date: string; reason: string; leave_type?: string }) => {
      const { data } = await axiosInstance.post("/leaves/request", payload);
      return data;
    },
    listMine: async () => {
      const { data } = await axiosInstance.get("/leaves");
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
