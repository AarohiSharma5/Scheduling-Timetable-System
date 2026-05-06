import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { api } from "../api";
import { usePlanStore } from "../store";
import { Alert, LoadingSpinner } from "../components/Common";
import { SetupFormComponent } from "../components/SetupForm";

const SetupPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentPlan, loading, error, setCurrentPlan, setLoading, setError } =
    usePlanStore();

  useEffect(() => {
    loadPlan();
  }, [id, setLoading, setCurrentPlan, setError]);

  const loadPlan = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const plan = await api.plans.get(+id);
      setCurrentPlan(plan);
    } catch (err) {
      setError("Failed to load plan");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!currentPlan) return;
    try {
      await api.plans.update(currentPlan.id, {
        school_profile: currentPlan.school_profile,
      });
      navigate(`/plans/${currentPlan.id}/curriculum`);
    } catch (err) {
      setError("Failed to save plan");
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!currentPlan) return <Alert type="error" message="Plan not found" />;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold">{currentPlan.title}</h2>
        <p className="text-gray-600">Step 1: Institution Setup</p>
      </div>

      {error && <Alert type="error" message={error} />}

      <SetupFormComponent
        profile={currentPlan.school_profile}
        onChange={(profile) =>
          setCurrentPlan({ ...currentPlan, school_profile: profile })
        }
      />

      <div className="mt-8 flex gap-4">
        <button onClick={() => navigate("/")} className="secondary">
          Back
        </button>
        <button onClick={handleSave}>
          Next: Add Curriculum <ChevronRight size={16} className="ml-2 inline" />
        </button>
      </div>
    </div>
  );
};

export default SetupPage;
