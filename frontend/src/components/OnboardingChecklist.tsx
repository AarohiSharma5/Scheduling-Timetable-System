import React from "react";

interface Step {
  key: string;
  label: string;
  tab: string;
  done: boolean;
  count: number | null;
}

interface OnboardingData {
  completed: boolean;
  done_count: number;
  total: number;
  steps: Step[];
}

interface Props {
  data: OnboardingData | null;
  onNavigate: (tab: string) => void;
  onDismiss: () => void;
}

export default function OnboardingChecklist({ data, onNavigate, onDismiss }: Props) {
  if (!data) {
    return <div className="text-slate-500">Loading setup checklist…</div>;
  }

  const pct = data.total ? Math.round((data.done_count / data.total) * 100) : 0;
  const allDone = data.done_count >= data.total;

  return (
    <div className="max-w-2xl">
      <div className="flex items-start justify-between gap-4 mb-1">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Getting started</h2>
          <p className="text-slate-600 mt-1">
            {allDone
              ? "Your school is set up. You can dismiss this checklist."
              : "Finish these steps to get your school up and running."}
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="text-sm text-slate-500 hover:text-slate-800 underline whitespace-nowrap"
        >
          {allDone ? "Finish setup" : "Skip for now"}
        </button>
      </div>

      {/* Progress */}
      <div className="mt-4 mb-6">
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>
            {data.done_count} of {data.total} done
          </span>
          <span>{pct}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <ol className="space-y-3">
        {data.steps.map((step, i) => (
          <li key={step.key}>
            <button
              onClick={() => onNavigate(step.tab)}
              className={`w-full flex items-center gap-3 text-left rounded-lg border px-4 py-3 transition ${
                step.done
                  ? "border-emerald-200 bg-emerald-50"
                  : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50"
              }`}
            >
              <span
                className={`flex h-7 w-7 flex-none items-center justify-center rounded-full text-sm font-semibold ${
                  step.done ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-600"
                }`}
              >
                {step.done ? "✓" : i + 1}
              </span>
              <span className="flex-1">
                <span
                  className={`font-medium ${
                    step.done ? "text-emerald-800" : "text-slate-800"
                  }`}
                >
                  {step.label}
                </span>
                {typeof step.count === "number" && step.count > 0 && (
                  <span className="ml-2 text-xs text-slate-500">({step.count})</span>
                )}
              </span>
              {!step.done && (
                <span className="text-sm font-medium text-indigo-600">Set up →</span>
              )}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
