import React, { useState, useEffect } from "react";
import { api } from "../api";

interface SchoolConfig {
  id: number;
  start_time: string;
  end_time: string;
  lunch_start: string;
  lunch_end: string;
  period_duration: number;
  periods_per_day: number;
  has_lunch_break: boolean;
  working_days: number;
  target_contact_periods_per_week: number;
  class_teacher_hours_per_week: number;
  pre_primary_mode: "single" | "specialist";
  pre_primary_support_subjects: string[];
  default_room_capacity: number;
  ground_max_concurrent_batches: number;
  available_streams: string[];
  min_group_size: number;
  max_group_size: number;
  elective_merge_threshold: number;
  language_start_grade: string;
  allow_group_override: boolean;
}

const toMinutes = (t: string): number => {
  const [h, m] = (t || "0:0").split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
};

export default function ConfigurationForm() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [config, setConfig] = useState<SchoolConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [workload, setWorkload] = useState<any>(null);

  const [formData, setFormData] = useState({
    start_time: "08:00",
    end_time: "14:00",
    lunch_start: "11:00",
    lunch_end: "11:45",
    period_duration: 45,
    periods_per_day: 8,
    has_lunch_break: true,
    working_days: 5,
    target_contact_periods_per_week: 40,
    class_teacher_hours_per_week: 5,
    pre_primary_mode: "single" as "single" | "specialist",
    pre_primary_support_subjects: ["Art", "Music", "Dance", "PE"] as string[],
    default_room_capacity: 50,
    ground_max_concurrent_batches: 4,
    available_streams: ["Science", "Commerce", "Humanities"] as string[],
    min_group_size: 10,
    max_group_size: 45,
    elective_merge_threshold: 10,
    language_start_grade: "6",
    allow_group_override: true,
  });

  // Number of periods is derived from the school hours, not typed in — this is
  // what guarantees the timetable actually runs the full day.
  const computedPeriods = Math.max(
    0,
    Math.floor((toMinutes(formData.end_time) - toMinutes(formData.start_time)) / (formData.period_duration || 45))
  );

  useEffect(() => {
    loadConfig();
    api.admin.workload.summary().then(setWorkload).catch(() => {});
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const res = await api.admin.config.get();
      if (res) {
        setConfig(res);
        setFormData(res);
      }
    } catch (err) {
      setError("Failed to load configuration");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError("");
      setSuccess("");
      await api.admin.config.update(formData);
      setSuccess("Configuration saved successfully!");
      await loadConfig();
    } catch (err) {
      setError("Failed to save configuration");
      console.error(err);
    }
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-900">School Configuration</h2>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}
      {success && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">{success}</div>}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-6">
        {/* School Hours */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">School Hours</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Start Time</label>
              <input
                type="time"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">End Time</label>
              <input
                type="time"
                value={formData.end_time}
                onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                required
              />
            </div>
          </div>
        </div>

        {/* Lunch Break */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Lunch Break</h3>
          <label className="flex items-center gap-2 mb-4">
            <input
              type="checkbox"
              checked={formData.has_lunch_break}
              onChange={(e) => setFormData({ ...formData, has_lunch_break: e.target.checked })}
            />
            <span className="text-sm text-slate-700">
              Reserve a lunch period (uncheck for a compact, back-to-back day)
            </span>
          </label>
          {formData.has_lunch_break && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Lunch Start</label>
                <input
                  type="time"
                  value={formData.lunch_start}
                  onChange={(e) => setFormData({ ...formData, lunch_start: e.target.value })}
                  className="border rounded px-3 py-2 w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Lunch End</label>
                <input
                  type="time"
                  value={formData.lunch_end}
                  onChange={(e) => setFormData({ ...formData, lunch_end: e.target.value })}
                  className="border rounded px-3 py-2 w-full"
                  required
                />
              </div>
            </div>
          )}
        </div>

        {/* Period Configuration */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Period Configuration</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Period Duration (minutes)</label>
              <input
                type="number"
                value={formData.period_duration}
                onChange={(e) => setFormData({ ...formData, period_duration: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                min="30"
                max="60"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Periods Per Day (auto)</label>
              <div className="border rounded px-3 py-2 w-full bg-slate-100 text-slate-700">
                {computedPeriods} {computedPeriods === 1 ? "period" : "periods"}
              </div>
              <p className="text-xs text-slate-500 mt-1">Computed from school hours ÷ period length.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Working Days</label>
              <input
                type="number"
                value={formData.working_days}
                onChange={(e) => setFormData({ ...formData, working_days: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                min="3"
                max="6"
                required
              />
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Junior grades can finish earlier — set a shorter day per class under <strong>Batches</strong>.
          </p>
        </div>

        {/* Teacher Workload */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Teacher Workload</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Target contact periods / week</label>
              <input
                type="number"
                min={1}
                max={48}
                value={formData.target_contact_periods_per_week}
                onChange={(e) => setFormData({ ...formData, target_contact_periods_per_week: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                required
              />
              <p className="text-xs text-slate-500 mt-1">
                Every teacher is balanced to this total. Teaching capacity = target − charge hours, so teachers
                with extra duties teach proportionally fewer classes. Changing this rebalances all teachers.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Class-teacher hours / week</label>
              <input
                type="number"
                min={0}
                max={20}
                value={formData.class_teacher_hours_per_week}
                onChange={(e) => setFormData({ ...formData, class_teacher_hours_per_week: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                required
              />
              <p className="text-xs text-slate-500 mt-1">
                Extra weekly contact hours reserved for class teachers (default 5 for this organization —
                edit to increase/decrease). These reduce a class teacher's teaching capacity by this amount.
                Each organization keeps its own value.
              </p>
            </div>
          </div>

          {workload && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-slate-900 mb-2">Suggested workload (from this school's size)</h4>
              <ul className="text-sm text-slate-700 grid grid-cols-2 gap-x-6 gap-y-1">
                <li>👨‍🎓 Students: <strong>{workload.total_students ?? "—"}</strong></li>
                <li>🏫 Classes: <strong>{workload.total_classes}</strong></li>
                <li>📖 Subjects: <strong>{workload.total_subjects}</strong></li>
                <li>📅 Weekly periods demanded: <strong>{workload.total_weekly_periods_demanded}</strong></li>
                <li>👩‍🏫 Class-taking teachers: <strong>{workload.teaching_teachers}</strong></li>
                <li>🔁 Substitute pool: <strong>{workload.substitute_teachers}</strong></li>
              </ul>
              <div className="mt-3 flex items-center gap-3">
                <span className="text-sm text-slate-700">
                  Suggested target: <strong>{workload.suggested_target_periods_per_week}</strong> periods/week/teacher
                </span>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, target_contact_periods_per_week: workload.suggested_target_periods_per_week })}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded"
                >
                  Use suggested
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                = total weekly periods ÷ class-taking teachers. Save to apply &amp; rebalance everyone.
              </p>
            </div>
          )}
        </div>

        {/* Pre-primary scheduling */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-1">Pre-primary Scheduling</h3>
          <p className="text-xs text-slate-500 mb-4">
            How Nursery / LKG / UKG / Prep classes are staffed. Single-teacher mode keeps young
            children with one familiar homeroom teacher for most of the (short) day.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <label
              className={`flex flex-col gap-1 border rounded-lg p-3 cursor-pointer ${
                formData.pre_primary_mode === "single"
                  ? "border-green-500 bg-green-50 ring-1 ring-green-500"
                  : "border-slate-300"
              }`}
            >
              <span className="flex items-center gap-2 font-medium text-slate-900">
                <input
                  type="radio"
                  name="pre_primary_mode"
                  checked={formData.pre_primary_mode === "single"}
                  onChange={() => setFormData({ ...formData, pre_primary_mode: "single" })}
                />
                Single Teacher Mode
              </span>
              <span className="text-xs text-slate-600">
                One homeroom teacher takes most subjects; specialists only for the support subjects below.
              </span>
            </label>
            <label
              className={`flex flex-col gap-1 border rounded-lg p-3 cursor-pointer ${
                formData.pre_primary_mode === "specialist"
                  ? "border-green-500 bg-green-50 ring-1 ring-green-500"
                  : "border-slate-300"
              }`}
            >
              <span className="flex items-center gap-2 font-medium text-slate-900">
                <input
                  type="radio"
                  name="pre_primary_mode"
                  checked={formData.pre_primary_mode === "specialist"}
                  onChange={() => setFormData({ ...formData, pre_primary_mode: "specialist" })}
                />
                Subject Specialist Mode
              </span>
              <span className="text-xs text-slate-600">
                Every subject is scheduled with its own subject teacher, like senior grades.
              </span>
            </label>
          </div>

          {formData.pre_primary_mode === "single" && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Support / specialist subjects
              </label>
              <input
                type="text"
                value={(formData.pre_primary_support_subjects || []).join(", ")}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    pre_primary_support_subjects: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
                className="border rounded px-3 py-2 w-full"
                placeholder="Art, Music, Dance, PE"
              />
              <p className="text-xs text-slate-500 mt-1">
                Comma-separated. These subjects go to specialist teachers even in single-teacher mode.
                Set the homeroom teacher for each pre-primary class under <strong>Batches</strong>.
              </p>
            </div>
          )}
        </div>

        {/* Rooms & class size */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
          <h3 className="font-semibold text-slate-900 mb-1">🏫 Rooms &amp; class size</h3>
          <p className="text-sm text-slate-600 mb-3">
            These drive how students are distributed across sections and how the ground is shared.
            Manage the actual room inventory (classrooms, labs, art/music/dance rooms, library, ground)
            under the <strong>Rooms</strong> tab.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Max students per class (default room capacity)
              </label>
              <input
                type="number"
                min="1"
                max="200"
                value={formData.default_room_capacity}
                onChange={(e) => setFormData({ ...formData, default_room_capacity: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
              />
              <p className="text-xs text-slate-500 mt-1">
                Used when a room/section has no explicit capacity. No section is filled beyond its limit.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Batches allowed on the ground at once (games period)
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={formData.ground_max_concurrent_batches}
                onChange={(e) => setFormData({ ...formData, ground_max_concurrent_batches: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
              />
              <p className="text-xs text-slate-500 mt-1">
                The scheduler won't put more than this many classes on the ground in the same period.
              </p>
            </div>
          </div>
        </div>

        {/* Streams, electives & teaching groups */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <h3 className="font-semibold text-slate-900 mb-1">🧩 Streams, electives &amp; groups</h3>
          <p className="text-sm text-slate-600 mb-3">
            Controls how senior streams are offered and how elective / language teaching groups are
            formed. After changing these, rebuild groups under the <strong>Teaching Groups</strong> tab.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Streams offered (Class 11 &amp; 12)
              </label>
              <input
                type="text"
                value={(formData.available_streams || []).join(", ")}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    available_streams: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
                className="border rounded px-3 py-2 w-full"
                placeholder="Science, Commerce, Humanities"
              />
              <p className="text-xs text-slate-500 mt-1">Comma-separated. Shown in the student admission form.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Minimum group size</label>
              <input
                type="number" min="1"
                value={formData.min_group_size}
                onChange={(e) => setFormData({ ...formData, min_group_size: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Maximum group size (split above)</label>
              <input
                type="number" min="1"
                value={formData.max_group_size}
                onChange={(e) => setFormData({ ...formData, max_group_size: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Elective merge threshold</label>
              <input
                type="number" min="1"
                value={formData.elective_merge_threshold}
                onChange={(e) => setFormData({ ...formData, elective_merge_threshold: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
              />
              <p className="text-xs text-slate-500 mt-1">Groups smaller than this are flagged to merge.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Language choice starts at grade</label>
              <input
                type="text"
                value={formData.language_start_grade}
                onChange={(e) => setFormData({ ...formData, language_start_grade: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                placeholder="6"
              />
            </div>
            <div className="md:col-span-2 flex items-center gap-2">
              <input
                id="allow_group_override"
                type="checkbox"
                checked={formData.allow_group_override}
                onChange={(e) => setFormData({ ...formData, allow_group_override: e.target.checked })}
              />
              <label htmlFor="allow_group_override" className="text-sm text-slate-700">
                Allow admins to manually override auto-formed groups (move students, lock, reassign)
              </label>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-slate-900 mb-2">Summary</h4>
          <ul className="text-sm text-slate-700 space-y-1">
            <li>
              📅 <strong>Daily Schedule:</strong> {formData.start_time} - {formData.end_time} ({computedPeriods} periods × {formData.period_duration} min)
            </li>
            <li>
              🍽️ <strong>Lunch Break:</strong>{" "}
              {formData.has_lunch_break ? `${formData.lunch_start} - ${formData.lunch_end}` : "None (compact day)"}
            </li>
            <li>
              📆 <strong>Working Days:</strong> {formData.working_days} days/week
            </li>
          </ul>
        </div>

        <button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-3 rounded-lg">
          Save Configuration
        </button>
      </form>
    </div>
  );
}
