import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

interface Event {
  id: number;
  title: string;
  event_type: string;
  start_date: string;
  end_date: string | null;
  description: string | null;
}

const TYPES = ["holiday", "event", "exam", "break", "activity"];

const typeBadge = (t: string) => {
  const map: Record<string, string> = {
    holiday: "bg-rose-100 text-rose-700",
    event: "bg-blue-100 text-blue-800",
    exam: "bg-amber-100 text-amber-800",
    break: "bg-violet-100 text-violet-700",
    activity: "bg-emerald-100 text-emerald-800",
  };
  return map[t] || "bg-slate-100 text-slate-700";
};

export default function CalendarPanel() {
  const role = useAuthStore((s) => s.user?.role);
  const canManage = role === "admin" || role === "principal";

  const [items, setItems] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState("event");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setItems(await api.calendar.list());
    } catch {
      setErr("Could not load the calendar.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !startDate) return;
    try {
      setSaving(true);
      await api.calendar.create({
        title: title.trim(), event_type: eventType, start_date: startDate,
        end_date: endDate || undefined, description: description.trim() || undefined,
      });
      setTitle(""); setStartDate(""); setEndDate(""); setDescription(""); setEventType("event");
      setShowForm(false);
      load();
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Could not create event.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this calendar entry?")) return;
    await api.calendar.remove(id);
    load();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Academic Calendar</h2>
        {canManage && (
          <button onClick={() => setShowForm((v) => !v)} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">
            {showForm ? "Close" : "+ New entry"}
          </button>
        )}
      </div>

      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}

      {canManage && showForm && (
        <form onSubmit={create} className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Title (e.g. Summer Break)" value={title} onChange={(e) => setTitle(e.target.value)} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm capitalize" value={eventType} onChange={(e) => setEventType(e.target.value)}>
              {TYPES.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
            </select>
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} placeholder="End (optional)" />
          </div>
          <textarea className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" rows={2} placeholder="Notes (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : "Add"}</button>
        </form>
      )}

      {loading && <div className="text-sm text-slate-500">Loading…</div>}

      <div className="space-y-2">
        {items.map((ev) => (
          <div key={ev.id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
            <div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${typeBadge(ev.event_type)}`}>{ev.event_type}</span>
                <span className="font-semibold text-slate-800">{ev.title}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {ev.start_date}{ev.end_date && ev.end_date !== ev.start_date ? ` → ${ev.end_date}` : ""}
              </div>
              {ev.description && <p className="mt-1 text-sm text-slate-600">{ev.description}</p>}
            </div>
            {canManage && (
              <button onClick={() => remove(ev.id)} className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Delete</button>
            )}
          </div>
        ))}
        {!loading && !items.length && <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">No calendar entries yet.</div>}
      </div>
    </div>
  );
}
