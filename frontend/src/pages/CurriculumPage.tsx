import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { api } from "../api";
import { usePlanStore } from "../store";
import { Alert, LoadingSpinner } from "../components/Common";
import { CurriculumEditorComponent } from "../components/CurriculumEditor";

const CurriculumPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentPlan, loading, error, setCurrentPlan, setLoading, setError } =
    usePlanStore();

  useEffect(() => {
    loadPlan();
  }, [id]);

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
        teachers: currentPlan.teachers,
        subjects: currentPlan.subjects,
      });
      navigate(`/plans/${currentPlan.id}/review`);
    } catch (err) {
      setError("Failed to save curriculum");
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!currentPlan) return <Alert type="error" message="Plan not found" />;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold">{currentPlan.title}</h2>
        <p className="text-gray-600">Step 2: Add Teachers & Subjects</p>
      </div>

      {error && <Alert type="error" message={error} />}

      <CurriculumEditorComponent
        teachers={currentPlan.teachers}
        subjects={currentPlan.subjects}
        onTeachersChange={(teachers) =>
          setCurrentPlan({ ...currentPlan, teachers })
        }
        onSubjectsChange={(subjects) =>
          setCurrentPlan({ ...currentPlan, subjects })
        }
      />

      <div className="mt-8 flex gap-4">
        <button onClick={() => navigate(`/plans/${id}/setup`)} className="secondary">
          Back
        </button>
        <button onClick={handleSave} disabled={currentPlan.teachers.length === 0}>
          Next: Review & Generate <ChevronRight size={16} className="ml-2 inline" />
        </button>
      </div>
    </div>
  );
};

export default CurriculumPage;
