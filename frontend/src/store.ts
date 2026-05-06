import { create } from "zustand";
import type { Plan, SchoolProfile, Teacher, Subject } from "./types";

interface PlanState {
  plans: Plan[];
  currentPlan: Plan | null;
  loading: boolean;
  error: string | null;

  setPlans: (plans: Plan[]) => void;
  setCurrentPlan: (plan: Plan | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  addPlan: (plan: Plan) => void;
  updatePlanInList: (id: number, updates: Partial<Plan>) => void;
  removePlanFromList: (id: number) => void;
}

export const usePlanStore = create<PlanState>((set) => ({
  plans: [],
  currentPlan: null,
  loading: false,
  error: null,

  setPlans: (plans) => set({ plans }),
  setCurrentPlan: (plan) => set({ currentPlan: plan }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  addPlan: (plan) =>
    set((state) => ({
      plans: [plan, ...state.plans],
    })),

  updatePlanInList: (id, updates) =>
    set((state) => ({
      plans: state.plans.map((p) => (p.id === id ? { ...p, ...updates } : p)),
      currentPlan:
        state.currentPlan?.id === id
          ? { ...state.currentPlan, ...updates }
          : state.currentPlan,
    })),

  removePlanFromList: (id) =>
    set((state) => ({
      plans: state.plans.filter((p) => p.id !== id),
      currentPlan: state.currentPlan?.id === id ? null : state.currentPlan,
    })),
}));
