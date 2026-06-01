import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Room {
  id: number;
  room_id: string;
  room_name: string;
  capacity: number;
  room_type: string;
  floor: number | null;
  assigned_class: string | null;
}

interface BatchLite {
  id: number;
  grade: string;
  section: string;
  room_id: number | null;
  capacity: number | null;
}

const ROOM_TYPES: { value: string; label: string }[] = [
  { value: "regular", label: "Regular classroom" },
  { value: "lab", label: "Laboratory" },
  { value: "library", label: "Library" },
  { value: "art", label: "Art room" },
  { value: "music", label: "Music room" },
  { value: "dance", label: "Dance room" },
  { value: "indoor_games", label: "Indoor games" },
  { value: "ground", label: "Ground / playfield" },
  { value: "hall", label: "Hall / auditorium" },
  { value: "activity", label: "Activity room (ATL etc.)" },
];
const TYPE_LABEL: Record<string, string> = Object.fromEntries(ROOM_TYPES.map((t) => [t.value, t.label]));

const floorName = (f: number | null): string => {
  if (f === null || f === undefined) return "Outdoor / unassigned";
  return ["Ground floor", "First floor", "Second floor", "Third floor"][f] ?? `Floor ${f}`;
};

const TYPE_BADGE: Record<string, string> = {
  regular: "bg-slate-100 text-slate-700",
  ground: "bg-green-100 text-green-800",
};

const emptyForm = {
  room_id: "",
  room_name: "",
  room_type: "regular",
  capacity: "" as number | "",
  floor: "" as number | "",
};

export default function RoomManagement() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [batches, setBatches] = useState<BatchLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [exA, setExA] = useState<number | "">("");
  const [exB, setExB] = useState<number | "">("");

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      setLoading(true);
      const [res, bRes] = await Promise.all([
        api.admin.rooms.list(),
        api.admin.batches.list().catch(() => []),
      ]);
      setRooms(res || []);
      setBatches(bRes || []);
    } catch (err) {
      setError("Failed to load rooms");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const exchangeRooms = async () => {
    if (!exA || !exB || exA === exB) return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await api.admin.rooms.exchange(Number(exA), Number(exB));
      await load();
      const warn = (res.warnings || []).length ? ` ⚠️ ${res.warnings.join(" ")}` : "";
      setInfo(`Home rooms exchanged.${warn}`);
      setExA("");
      setExB("");
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to exchange rooms");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        room_id: form.room_id,
        room_name: form.room_name,
        room_type: form.room_type,
        capacity: form.capacity === "" ? undefined : Number(form.capacity),
        floor: form.floor === "" ? undefined : Number(form.floor),
      };
      if (editingId) await api.admin.rooms.update(editingId, payload);
      else await api.admin.rooms.create(payload);
      await load();
      resetForm();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to save room");
    }
  };

  const edit = (r: Room) => {
    setForm({
      room_id: r.room_id,
      room_name: r.room_name,
      room_type: r.room_type,
      capacity: r.capacity,
      floor: r.floor ?? "",
    });
    setEditingId(r.id);
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(false);
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this room? Any batch using it as a home room will be detached.")) return;
    try {
      await api.admin.rooms.delete(id);
      await load();
    } catch (err) {
      setError("Failed to delete room");
    }
  };

  const runSetup = async () => {
    if (
      !window.confirm(
        "Auto set-up will: add sections so every grade fits at the configured capacity, " +
          "(re)generate the room inventory across floors, assign each section a fixed home room, " +
          "and redistribute students so no section exceeds its limit.\n\nProceed?"
      )
    )
      return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await api.admin.rooms.setup({});
      await load();
      const overflow = Object.values(res.distribution || {}).reduce(
        (n: number, d: any) => n + (d.overflow || 0),
        0
      );
      setInfo(
        `Done. Created ${res.created_rooms} rooms and ${res.created_sections?.length || 0} new sections, ` +
          `assigned ${res.assigned} home rooms.` +
          (overflow > 0 ? ` ⚠️ ${overflow} students could not be seated within capacity (add rooms/sections).` : " No section exceeds its capacity.")
      );
    } catch (err: any) {
      setError(err?.response?.data?.error || "Auto set-up failed");
    } finally {
      setBusy(false);
    }
  };

  const assignHome = async () => {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await api.admin.rooms.assignHome();
      await load();
      setInfo(`Assigned ${res.assigned} home rooms${res.unassigned?.length ? `, ${res.unassigned.length} section(s) had no free room` : ""} and redistributed students.`);
    } catch (err: any) {
      setError(err?.response?.data?.error || "Assign home rooms failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="text-center py-4">Loading…</div>;

  const byFloor = rooms.reduce<Record<string, Room[]>>((acc, r) => {
    const key = r.floor === null || r.floor === undefined ? "out" : String(r.floor);
    (acc[key] = acc[key] || []).push(r);
    return acc;
  }, {});
  const floorKeys = Object.keys(byFloor).sort((a, b) => {
    if (a === "out") return 1;
    if (b === "out") return -1;
    return Number(a) - Number(b);
  });

  const counts = rooms.reduce<Record<string, number>>((acc, r) => {
    acc[r.room_type] = (acc[r.room_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-900">Rooms &amp; Facilities</h2>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            + Add Room
          </button>
        )}
      </div>

      <p className="text-sm text-slate-600">
        Tell us about your building: how many rooms you have (regular classrooms plus special rooms like
        labs, art/music/dance rooms, library, indoor games and the ground), and how many students each
        room holds. Sections sit in a fixed <strong>home classroom</strong> for regular subjects and travel
        to special rooms for co-curricular periods. Set the default class size and ground concurrency in
        the <strong>Configuration</strong> tab.
      </p>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}
      {info && <div className="bg-green-100 border border-green-400 text-green-800 px-4 py-3 rounded">{info}</div>}

      {/* Quick actions */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 space-y-3">
        <h3 className="font-semibold text-slate-900">Quick set-up</h3>
        <p className="text-sm text-slate-600">
          No rooms yet, or want a clean layout for test data? Auto set-up lays out classrooms across
          Ground/First/Second/Third floors plus the standard special rooms, gives every section a home room,
          and seats students within capacity.
        </p>
        <div className="flex flex-wrap gap-2">
          <button onClick={runSetup} disabled={busy} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg">
            {busy ? "Working…" : "🏫 Auto set-up rooms & seat students"}
          </button>
          <button onClick={assignHome} disabled={busy || rooms.length === 0} className="bg-slate-700 hover:bg-slate-800 disabled:opacity-50 text-white px-4 py-2 rounded-lg">
            Assign home rooms &amp; redistribute
          </button>
        </div>
      </div>

      {/* Exchange home rooms between two sections */}
      {(() => {
        const withRoom = batches
          .filter((b) => b.room_id)
          .sort((x, y) => `${x.grade}-${x.section}`.localeCompare(`${y.grade}-${y.section}`, undefined, { numeric: true }));
        const roomLabel = (b: BatchLite) => {
          const r = rooms.find((x) => x.id === b.room_id);
          return r ? `${r.room_id} (${r.room_name})` : `#${b.room_id}`;
        };
        const opt = (b: BatchLite) => `${b.grade}-${b.section} — ${roomLabel(b)}`;
        if (withRoom.length < 2) return null;
        return (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-3">
            <h3 className="font-semibold text-slate-900">🔁 Exchange home rooms</h3>
            <p className="text-sm text-slate-600">
              Two sections can swap their fixed classrooms (capacity travels with the room). Handy when
              classes want to trade rooms — e.g. move a senior class downstairs.
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Section A</label>
                <select value={exA} onChange={(e) => setExA(e.target.value ? Number(e.target.value) : "")} className="border rounded px-3 py-2 w-72">
                  <option value="">Select section…</option>
                  {withRoom.map((b) => <option key={b.id} value={b.id} disabled={b.id === exB}>{opt(b)}</option>)}
                </select>
              </div>
              <span className="pb-2 text-slate-500 font-semibold">⇄</span>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Section B</label>
                <select value={exB} onChange={(e) => setExB(e.target.value ? Number(e.target.value) : "")} className="border rounded px-3 py-2 w-72">
                  <option value="">Select section…</option>
                  {withRoom.map((b) => <option key={b.id} value={b.id} disabled={b.id === exA}>{opt(b)}</option>)}
                </select>
              </div>
              <button
                type="button"
                onClick={exchangeRooms}
                disabled={!exA || !exB || exA === exB || busy}
                className="bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg"
              >
                {busy ? "Swapping…" : "Swap rooms"}
              </button>
            </div>
          </div>
        );
      })()}

      {/* Summary chips */}
      {rooms.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="px-3 py-1 rounded-full bg-slate-800 text-white text-sm">{rooms.length} rooms</span>
          {Object.entries(counts).map(([t, n]) => (
            <span key={t} className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-sm">
              {TYPE_LABEL[t] || t}: {n}
            </span>
          ))}
        </div>
      )}

      {showForm && (
        <form onSubmit={submit} className="bg-white p-6 rounded-lg shadow-md space-y-4 border border-slate-200">
          <h3 className="font-semibold text-slate-900">{editingId ? "Edit room" : "Add room"}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Room code</label>
              <input type="text" placeholder="e.g., G01, 101, LAB1" value={form.room_id}
                onChange={(e) => setForm({ ...form, room_id: e.target.value })}
                className="border rounded px-3 py-2 w-full" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Room name</label>
              <input type="text" placeholder="e.g., Classroom G01, Physics Lab" value={form.room_name}
                onChange={(e) => setForm({ ...form, room_name: e.target.value })}
                className="border rounded px-3 py-2 w-full" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
              <select value={form.room_type} onChange={(e) => setForm({ ...form, room_type: e.target.value })}
                className="border rounded px-3 py-2 w-full">
                {ROOM_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Capacity</label>
              <input type="number" min="1" max="500" placeholder="default 50" value={form.capacity}
                onChange={(e) => setForm({ ...form, capacity: e.target.value ? Number(e.target.value) : "" })}
                className="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Floor</label>
              <select value={form.floor} onChange={(e) => setForm({ ...form, floor: e.target.value === "" ? "" : Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full">
                <option value="">Outdoor / unassigned</option>
                <option value="0">Ground floor</option>
                <option value="1">First floor</option>
                <option value="2">Second floor</option>
                <option value="3">Third floor</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">{editingId ? "Update" : "Create"}</button>
            <button type="button" onClick={resetForm} className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded">Cancel</button>
          </div>
        </form>
      )}

      {rooms.length === 0 ? (
        <div className="text-center text-slate-500 py-10 border-2 border-dashed border-slate-200 rounded-lg">
          No rooms yet. Use <strong>Auto set-up</strong> above, or add rooms one by one.
        </div>
      ) : (
        floorKeys.map((fk) => (
          <div key={fk} className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="bg-slate-100 px-4 py-2 font-semibold text-slate-800 border-b">
              {fk === "out" ? "Outdoor / unassigned" : floorName(Number(fk))}{" "}
              <span className="text-slate-500 font-normal">({byFloor[fk].length})</span>
            </div>
            <table className="w-full">
              <thead className="bg-slate-50 border-b text-sm">
                <tr>
                  <th className="px-4 py-2 text-left">Code</th>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Type</th>
                  <th className="px-4 py-2 text-left">Capacity</th>
                  <th className="px-4 py-2 text-left">Home of</th>
                  <th className="px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {byFloor[fk].map((r) => (
                  <tr key={r.id} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-2 font-mono">{r.room_id}</td>
                    <td className="px-4 py-2">{r.room_name}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${TYPE_BADGE[r.room_type] || "bg-blue-100 text-blue-800"}`}>
                        {TYPE_LABEL[r.room_type] || r.room_type}
                      </span>
                    </td>
                    <td className="px-4 py-2">{r.capacity}</td>
                    <td className="px-4 py-2">{r.assigned_class || <span className="text-slate-300">—</span>}</td>
                    <td className="px-4 py-2 whitespace-nowrap">
                      <div className="flex gap-2">
                        <button onClick={() => edit(r)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded">Edit</button>
                        <button onClick={() => remove(r.id)} className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-3 py-1.5 rounded">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}
