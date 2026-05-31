import React, { useEffect, useState } from "react";
import { api } from "../api";

interface BlockedSlot {
  day: string;
  period: number;
}

interface Subject {
  id: number;
  name: string;
}

interface Batch {
  id: number;
  grade: string;
  section: string;
}

interface Props {
  teacherId: number;
  teacherName: string;
  subjects: Subject[];
  batches: Batch[];
  onClose: () => void;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const SLOT_BUCKETS: { value: string; label: string }[] = [
  { value: "morning", label: "Morning" },
  { value: "midday", label: "Mid-day" },
  { value: "last", label: "Last periods" },
];

interface PrefState {
  preferred_classes: number[];
  preferred_subjects: number[];
  preferred_slots: string[];
  blocked_slots: BlockedSlot[];
  max_periods_day: number | "";
  max_periods_week: number | "";
  allow_class_teacher_charge: boolean;
  allow_extra_charge: boolean;
}

const EMPTY: PrefState = {
  preferred_classes: [],
  preferred_subjects: [],
  preferred_slots: [],
  blocked_slots: [],
  max_periods_day: "",
  max_periods_week: "",
  allow_class_teacher_charge: true,
  allow_extra_charge: true,
};

export default function TeacherPreferenceEditor({ teacherId, teacherName, subjects, batches, onClose }: Props) {
  const [prefs, setPrefs] = useState<PrefState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [blockDay, setBlockDay] = useState("Monday");
  const [blockPeriod, setBlockPeriod] = useState(1);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await api.admin.teachers.getPreferences(teacherId);
        setPrefs({
          preferred_classes: data.preferred_classes || [],
          preferred_subjects: data.preferred_subjects || [],
          preferred_slots: data.preferred_slots || [],
          blocked_slots: data.blocked_slots || [],
          max_periods_day: data.max_periods_day ?? "",
          max_periods_week: data.max_periods_week ?? "",
          allow_class_teacher_charge: data.allow_class_teacher_charge ?? true,
          allow_extra_charge: data.allow_extra_charge ?? true,
        });
      } catch (err) {
        setError("Failed to load preferences");
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, [teacherId]);

  const toggleSlotBucket = (value: string) => {
    setPrefs((p) => ({
      ...p,
      preferred_slots: p.preferred_slots.includes(value)
        ? p.preferred_slots.filter((s) => s !== value)
        : [...p.preferred_slots, value],
    }));
  };

  const addBlocked = () => {
    if (prefs.blocked_slots.some((s) => s.day === blockDay && s.period === blockPeriod)) return;
    setPrefs((p) => ({ ...p, blocked_slots: [...p.blocked_slots, { day: blockDay, period: blockPeriod }] }));
  };

  const removeBlocked = (idx: number) => {
    setPrefs((p) => ({ ...p, blocked_slots: p.blocked_slots.filter((_, i) => i !== idx) }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      await api.admin.teachers.savePreferences(teacherId, {
        ...prefs,
        max_periods_day: prefs.max_periods_day === "" ? null : prefs.max_periods_day,
        max_periods_week: prefs.max_periods_week === "" ? null : prefs.max_periods_week,
      });
      onClose();
    } catch (err) {
      setError("Failed to save preferences");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b px-6 py-4 sticky top-0 bg-white">
          <h3 className="text-lg font-bold text-slate-900">Preferences — {teacherName}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-2xl leading-none">×</button>
        </div>

        {loading ? (
          <div className="p-6 text-center text-slate-500">Loading…</div>
        ) : (
          <div className="p-6 space-y-5">
            <p className="text-sm text-slate-500">
              These are <strong>soft</strong> preferences. The scheduler tries to honor them but may
              override when a valid timetable requires it. Blocked periods are always respected.
            </p>

            {error && <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">{error}</div>}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Preferred classes</label>
                <select
                  multiple
                  value={prefs.preferred_classes.map(String)}
                  onChange={(e) => setPrefs({ ...prefs, preferred_classes: Array.from(e.target.selectedOptions, (o) => Number(o.value)) })}
                  className="border rounded px-3 py-2 w-full h-28"
                >
                  {batches.map((b) => (
                    <option key={b.id} value={b.id}>Grade {b.grade} - {b.section}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Preferred subjects</label>
                <select
                  multiple
                  value={prefs.preferred_subjects.map(String)}
                  onChange={(e) => setPrefs({ ...prefs, preferred_subjects: Array.from(e.target.selectedOptions, (o) => Number(o.value)) })}
                  className="border rounded px-3 py-2 w-full h-28"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Preferred time of day</label>
              <div className="flex flex-wrap gap-3">
                {SLOT_BUCKETS.map((b) => (
                  <label key={b.value} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={prefs.preferred_slots.includes(b.value)}
                      onChange={() => toggleSlotBucket(b.value)}
                    />
                    {b.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Max periods / day (soft)</label>
                <input
                  type="number" min={1} max={12}
                  value={prefs.max_periods_day}
                  onChange={(e) => setPrefs({ ...prefs, max_periods_day: e.target.value === "" ? "" : Number(e.target.value) })}
                  className="border rounded px-3 py-2 w-full" placeholder="e.g. 6"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max periods / week (soft)</label>
                <input
                  type="number" min={1} max={48}
                  value={prefs.max_periods_week}
                  onChange={(e) => setPrefs({ ...prefs, max_periods_week: e.target.value === "" ? "" : Number(e.target.value) })}
                  className="border rounded px-3 py-2 w-full" placeholder="e.g. 24"
                />
              </div>
            </div>

            <div className="border-t pt-4">
              <label className="block text-sm font-medium mb-2">Blocked periods (hard — never scheduled)</label>
              <div className="flex flex-wrap items-end gap-2 mb-3">
                <select value={blockDay} onChange={(e) => setBlockDay(e.target.value)} className="border rounded px-3 py-2">
                  {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
                <input type="number" min={1} max={12} value={blockPeriod} onChange={(e) => setBlockPeriod(Number(e.target.value))} className="border rounded px-3 py-2 w-24" />
                <button type="button" onClick={addBlocked} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">+ Block</button>
              </div>
              <div className="flex flex-wrap gap-2">
                {prefs.blocked_slots.length === 0 && <span className="text-sm text-slate-400">No additional blocked periods.</span>}
                {prefs.blocked_slots.map((s, idx) => (
                  <span key={`${s.day}-${s.period}`} className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-sm px-2 py-1 rounded">
                    {s.day} P{s.period}
                    <button type="button" onClick={() => removeBlocked(idx)} className="text-amber-900 hover:text-red-600 font-bold">×</button>
                  </span>
                ))}
              </div>
            </div>

            <div className="border-t pt-4 space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={prefs.allow_class_teacher_charge} onChange={(e) => setPrefs({ ...prefs, allow_class_teacher_charge: e.target.checked })} />
                Accepts class-teacher charge
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={prefs.allow_extra_charge} onChange={(e) => setPrefs({ ...prefs, allow_extra_charge: e.target.checked })} />
                Accepts extra duties / charge
              </label>
            </div>

            <div className="flex gap-2 pt-2">
              <button onClick={handleSave} disabled={saving} className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-4 py-2 rounded">
                {saving ? "Saving…" : "Save preferences"}
              </button>
              <button onClick={onClose} className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
