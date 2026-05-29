import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import { usePlanStore } from "../store";
import { Alert, LoadingSpinner } from "../components/Common";
import { TimetableReviewComponent } from "../components/TimetableReview";
import TimetableValidation from "../components/TimetableValidation";

const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentPlan, loading, error, setCurrentPlan, setLoading, setError } =
    usePlanStore();
  const [timetableId, setTimetableId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"review" | "validation">("review");
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);

  useEffect(() => {
    loadPlan();
  }, [id, setLoading, setCurrentPlan, setError]);

  useEffect(() => {
    // Set timetable ID when plan is loaded and has a timetable
    if (currentPlan && currentPlan.timetable && id) {
      setTimetableId(+id);
    }
  }, [currentPlan, id]);

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
        <div>
          {/* Tabs */}
          <div className="mb-6 flex gap-4 border-b border-gray-200">
            <button
              onClick={() => setActiveTab("review")}
              className={`px-6 py-3 font-medium transition-colors ${
                activeTab === "review"
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Timetable Review
            </button>
            <button
              onClick={() => setActiveTab("validation")}
              className={`px-6 py-3 font-medium transition-colors ${
                activeTab === "validation"
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Conflict Validation
            </button>
          </div>

          {/* Content */}
          {activeTab === "review" && (() => {
            const batchTimetables = currentPlan.batch_timetables || [];
            const activeBatch =
              batchTimetables.find((b) => b.batch_id === selectedBatchId) ||
              batchTimetables[0];
            const displayedGrid = activeBatch?.timetable || currentPlan.timetable || [];

            return (
              <div className="space-y-4">
                {batchTimetables.length > 0 && (
                  <div className="flex items-center gap-3">
                    <label htmlFor="batch-select" className="font-medium text-gray-700">
                      Class:
                    </label>
                    <select
                      id="batch-select"
                      value={activeBatch?.batch_id ?? ""}
                      onChange={(e) => setSelectedBatchId(Number(e.target.value))}
                      className="rounded-lg border border-gray-300 px-3 py-2"
                    >
                      {batchTimetables.map((b) => (
                        <option key={b.batch_id} value={b.batch_id}>
                          {b.batch_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <TimetableReviewComponent
                  timetable={displayedGrid}
                  warnings={currentPlan.warnings || []}
                  onExport={handleExport}
                />
              </div>
            );
          })()}

          {activeTab === "validation" && timetableId && (
            <TimetableValidation
              timetableId={timetableId}
              onValidationComplete={(report) => {
                console.log("Validation complete:", report);
              }}
            />
          )}

          {activeTab === "validation" && !timetableId && (
            <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-6">
              <p className="text-yellow-800">
                Timetable ID not available. Please ensure the timetable has been generated and published.
              </p>
            </div>
          )}
        </div>
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
