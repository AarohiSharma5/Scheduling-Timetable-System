import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

interface Announcement {
  id: number;
  title: string;
  body: string;
  audience: string;
  batch_id: number | null;
  batch_label: string | null;
  author_name: string | null;
  created_at: string | null;
}

interface ClassOption {
  batch_id: number;
  label: string;
}

const AUDIENCE_LABEL: Record<string, string> = {
  all: "Everyone",
  teachers: "Teachers",
  students: "Students",
  parents: "Parents",
};

const audienceBadge = (a: string) => {
  const map: Record<string, string> = {
    all: "bg-slate-100 text-slate-700",
    teachers: "bg-emerald-100 text-emerald-800",
    students: "bg-blue-100 text-blue-800",
    parents: "bg-amber-100 text-amber-800",
  };
  return map[a] || "bg-slate-100 text-slate-700";
};

export default function AnnouncementsPanel() {
  const role = useAuthStore((s) => s.user?.role);
  const canPost = role === "admin" || role === "principal" || role === "teacher";
  const isStaffAdmin = role === "admin" || role === "principal";

  const [items, setItems] = useState<Announcement[]>([]);
  const [classes, setClasses] = useState<ClassOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState("all");
  const [batchId, setBatchId] = useState<number | "">("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const list = await api.announcements.list();
      setItems(list);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't load announcements.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (canPost) {
      api.announcements
        .audiences()
        .then((d) => {
          setClasses(d.classes || []);
          // Teachers must target a class; default to the first one.
          if (!d.can_post_org_wide && d.classes?.length) {
            setBatchId(d.classes[0].batch_id);
          }
        })
        .catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async () => {
    if (!title.trim() || !body.trim()) {
      setErr("Title and message are required.");
      return;
    }
    try {
      setSaving(true);
      setErr("");
      await api.announcements.create({
        title: title.trim(),
        body: body.trim(),
        audience,
        batch_id: batchId === "" ? null : (batchId as number),
      });
      setTitle("");
      setBody("");
      setMsg("Announcement posted.");
      setShowForm(false);
      await load();
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't post the announcement.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    try {
      await api.announcements.remove(id);
      setItems((xs) => xs.filter((x) => x.id !== id));
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't delete the announcement.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center">
        <h3 className="text-lg font-bold text-slate-800">📣 Announcements</h3>
        {canPost && (
          <button
            onClick={() => { setShowForm((v) => !v); setMsg(""); setErr(""); }}
            className="ml-auto px-4 py-2 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700"
          >
            {showForm ? "Close" : "+ New Announcement"}
          </button>
        )}
      </div>

      {msg && <div className="bg-green-50 border border-green-300 text-green-800 px-4 py-2 rounded-lg text-sm">{msg}</div>}
      {err && <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm">{err}</div>}

      {showForm && canPost && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className="border rounded px-3 py-2 bg-white w-full"
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your message…"
            rows={4}
            className="border rounded px-3 py-2 bg-white w-full"
          />
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Audience</label>
              <select value={audience} onChange={(e) => setAudience(e.target.value)}
                      className="border rounded px-3 py-2 bg-white">
                {["all", "teachers", "students", "parents"].map((a) => (
                  <option key={a} value={a}>{AUDIENCE_LABEL[a]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                Class {isStaffAdmin ? "(optional)" : ""}
              </label>
              <select
                value={batchId}
                onChange={(e) => setBatchId(e.target.value ? Number(e.target.value) : "")}
                className="border rounded px-3 py-2 bg-white"
              >
                {isStaffAdmin && <option value="">Whole school</option>}
                {classes.map((c) => (
                  <option key={c.batch_id} value={c.batch_id}>{c.label}</option>
                ))}
              </select>
            </div>
            <button onClick={submit} disabled={saving}
                    className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold py-2 px-5 rounded-lg">
              {saving ? "Posting…" : "Post"}
            </button>
          </div>
          {!isStaffAdmin && (
            <p className="text-xs text-slate-500">You can post to your own classes only.</p>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-slate-500 text-sm">⏳ Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-slate-500 text-sm">No announcements yet.</p>
      ) : (
        <div className="space-y-3">
          {items.map((a) => (
            <div key={a.id} className="border border-slate-200 rounded-lg p-4 bg-white">
              <div className="flex items-start gap-2">
                <h4 className="font-semibold text-slate-900 flex-1">{a.title}</h4>
                <span className={`text-xs px-2 py-0.5 rounded-full ${audienceBadge(a.audience)}`}>
                  {AUDIENCE_LABEL[a.audience] || a.audience}
                  {a.batch_label ? ` · ${a.batch_label}` : ""}
                </span>
                {(isStaffAdmin) && (
                  <button onClick={() => remove(a.id)}
                          className="text-xs text-red-600 hover:text-red-800">Delete</button>
                )}
              </div>
              <p className="text-slate-700 mt-1.5 whitespace-pre-wrap text-sm">{a.body}</p>
              <p className="text-xs text-slate-400 mt-2">
                {a.author_name ? `${a.author_name} · ` : ""}
                {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
