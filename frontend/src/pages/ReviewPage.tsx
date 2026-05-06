import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import { usePlanStore } from "../store";
import { Alert, LoadingSpinner } from "../components/Common";
import { TimetableReviewComponent } from "../components/TimetableReview";

const ReviewPage: React.FC = () => {
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

  const handleGenerate = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const result = await api.plans.generate(+id);
      setCurrentPlan({
        ...currentPlan!,
        timetable: result.timetable,
        warnings: result.warnings,
        status: "completed",
      });
    } catch (err) {
      setError("Failed to generate timetable");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!id) return;
    try {
      const csv = await api.plans.exportCSV(+id);
      const blob = new Blob([csv], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `timetable_${id}.csv`;
      a.click();
    } catch (err) {
      setError("Failed to export CSV");
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!currentPlan) return <Alert type="error" message="Plan not found" />;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold">{currentPlan.title}</h2>
        <p className="text-gray-600">Step 3: Review & Export</p>
      </div>

      {error && <Alert type="error" message={error} />}

      {!currentPlan.timetable ? (
        <div className="rounded-lg bg-blue-50 p-6">
          <p className="mb-4">Ready to generate the timetable?</p>
          <button onClick={handleGenerate}>Generate Timetable</button>
        </div>
      ) : (
        <TimetableReviewComponent
          timetable={currentPlan.timetable}
          warnings={currentPlan.warnings || []}
          onExport={handleExport}
        />
      )}

      <div className="mt-8 flex gap-4">
        <button onClick={() => navigate(`/plans/${id}/curriculum`)} className="secondary">
          Back
        </button>
        <button onClick={() => navigate("/")} className="secondary">
          Dashboard
        </button>
      </div>
    </div>
  );
};

export default ReviewPage;
