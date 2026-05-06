import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Edit2, Trash2 } from "lucide-react";
import { api } from "../api";
import { usePlanStore } from "../store";
import { Alert, LoadingSpinner } from "../components/Common";

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { plans, loading, error, setPlans, setLoading, setError, removePlanFromList } =
    usePlanStore();

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const data = await api.plans.list();
      setPlans(data);
    } catch (err) {
      setError("Failed to load plans");
    } finally {
      setLoading(false);
    }
  };

  const createNewPlan = async () => {
    try {
      const newPlan = await api.plans.create({
        title: "New Timetable Plan",
        description: "",
        school_profile: {
          institution_name: "My School",
          days_per_week: 5,
          periods_per_day: 6,
          student_count: 500,
          core_subjects_target: 5,
          elective_limit: 3,
        },
        teachers: [],
        subjects: [],
      });
      navigate(`/plans/${newPlan.id}/setup`);
    } catch (err) {
      setError("Failed to create plan");
    }
  };

  const deletePlan = async (id: number) => {
    try {
      await api.plans.delete(id);
      removePlanFromList(id);
    } catch (err) {
      setError("Failed to delete plan");
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-3xl font-bold">My Plans</h2>
        <button onClick={createNewPlan}>
          <Plus size={20} className="mr-2 inline" /> Create Plan
        </button>
      </div>

      {error && <Alert type="error" message={error} />}
      {loading && <LoadingSpinner />}

      {!loading && plans.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center">
          <p className="text-gray-600">No plans yet. Create one to get started!</p>
        </div>
      )}

      <div className="grid gap-4">
        {plans.map((plan) => (
          <div key={plan.id} className="flex items-center justify-between rounded-lg bg-white p-6 shadow">
            <div>
              <h3 className="text-xl font-semibold">{plan.title}</h3>
              <p className="text-gray-600">{plan.description}</p>
              <p className="mt-2 text-sm text-gray-500">
                Status: <span className="font-semibold">{plan.status}</span>
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate(`/plans/${plan.id}/setup`)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Edit2 size={16} />
              </button>
              <button
                onClick={() => deletePlan(plan.id)}
                className="bg-red-600 hover:bg-red-700"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DashboardPage;
