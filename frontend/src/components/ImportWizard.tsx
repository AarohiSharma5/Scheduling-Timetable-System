import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";

type Entity = "students" | "teachers";

interface Issue {
  level: "invalid" | "duplicate";
  msg: string;
}
interface Row {
  row: number;
  data: Record<string, string>;
  issues: Issue[];
  missing: string[];
  status: "ok" | "duplicate" | "invalid";
}
interface Preview {
  entity: Entity;
  fields: string[];
  mapping: Record<string, string>;
  unmapped_headers: string[];
  scope: { class_grade: string; section: string } | null;
  counts: { total: number; valid: number; duplicates: number; invalid: number };
  rows: Row[];
}
interface Result {
  success_count: number;
  failure_count: number;
  errors: { row: number; name: string; error: string }[];
}

interface Props {
  entity: Entity;
  onClose: () => void;
  onImported: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  name: "Name",
  parent_name: "Father",
  mother_name: "Mother",
  email: "Parent Email",
  phone: "Phone",
  class: "Class",
  section: "Section",
  roll_no: "Roll #",
  admission_number: "Admission #",
  date_of_birth: "DOB",
  gender: "Gender",
  address: "Address",
  blood_group: "Blood",
  admission_date: "Adm. Date",
  qualification: "Qualification",
  designation: "Designation",
};

const STATUS_STYLE: Record<Row["status"], string> = {
  ok: "bg-green-100 text-green-800",
  duplicate: "bg-amber-100 text-amber-800",
  invalid: "bg-red-100 text-red-700",
};

export default function ImportWizard({ entity, onClose, onImported }: Props) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [skipInvalid, setSkipInvalid] = useState(true);
  const [committing, setCommitting] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const handleFile = useCallback(
    async (file: File) => {
      const ok = /\.(csv|xlsx|xlsm|txt)$/i.test(file.name);
      if (!ok) {
        setError("Please upload a .csv or .xlsx file");
        return;
      }
      setError("");
      setResult(null);
      setFileName(file.name);
      setLoading(true);
      try {
        const data = await api.admin.imports.preview(entity, file);
        setPreview(data);
      } catch (e: any) {
        setError(e.response?.data?.error || "Failed to read file");
        setPreview(null);
      } finally {
        setLoading(false);
      }
    },
    [entity]
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  const doImport = async () => {
    if (!preview) return;
    setCommitting(true);
    setError("");
    try {
      const res = await api.admin.imports.commit(entity, preview.rows, skipInvalid);
      setResult(res);
      if (res.success_count > 0) onImported();
    } catch (e: any) {
      setError(e.response?.data?.error || "Import failed");
    } finally {
      setCommitting(false);
    }
  };

  const reset = () => {
    setPreview(null);
    setResult(null);
    setFileName("");
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  };

  // Only "ok" rows are written. Invalid + duplicate rows are skipped when the
  // skip toggle is on; otherwise the import is blocked until they're fixed.
  const skippable = preview ? preview.counts.invalid + preview.counts.duplicates : 0;
  const importableCount = preview ? preview.counts.valid : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-4xl my-8">
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-slate-900">
            Import {entity === "students" ? "students" : "teachers"} from CSV / Excel
            {preview?.scope && (
              <span className="ml-2 text-sm font-normal text-slate-500">
                · scoped to {preview.scope.class_grade}-{preview.scope.section}
              </span>
            )}
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-5">
          {error && (
            <div className="bg-red-100 text-red-700 text-sm font-medium px-4 py-3 rounded">{error}</div>
          )}

          {/* Result view */}
          {result ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-3xl font-bold text-green-600">{result.success_count}</p>
                  <p className="text-sm text-slate-600">Imported successfully</p>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-3xl font-bold text-red-600">{result.failure_count}</p>
                  <p className="text-sm text-slate-600">Skipped / failed</p>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <div className="bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-700">Error report</div>
                  <div className="max-h-60 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-100">
                        <tr>
                          <th className="px-3 py-1.5 text-left">Row</th>
                          <th className="px-3 py-1.5 text-left">Name</th>
                          <th className="px-3 py-1.5 text-left">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.errors.map((er, i) => (
                          <tr key={i} className="border-b">
                            <td className="px-3 py-1.5">{er.row}</td>
                            <td className="px-3 py-1.5">{er.name || "—"}</td>
                            <td className="px-3 py-1.5 text-red-600">{er.error}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <div className="flex gap-2">
                <button onClick={reset} className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium px-4 py-2 rounded">
                  Import another file
                </button>
                <button onClick={onClose} className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded">
                  Done
                </button>
              </div>
            </div>
          ) : !preview ? (
            /* Upload view */
            <>
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                className={`cursor-pointer border-2 border-dashed rounded-lg p-10 text-center transition ${
                  dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 hover:border-blue-400 hover:bg-slate-50"
                }`}
              >
                <div className="text-4xl mb-2">📄⬆️</div>
                <p className="font-medium text-slate-700">
                  {loading ? "Reading file…" : "Drag & drop a .csv or .xlsx file here"}
                </p>
                <p className="text-sm text-slate-500 mt-1">or click to browse</p>
                {fileName && <p className="text-xs text-slate-400 mt-2">{fileName}</p>}
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,.xlsx,.xlsm,.txt"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />
              </div>
              <div className="text-xs text-slate-500">
                <p className="font-semibold mb-1">Recognised columns (headers are auto-detected & fuzzy-matched):</p>
                <p>
                  {entity === "students"
                    ? "name, father/parent name, mother name, parent email, phone/mob, class, section, roll no, admission no, date of birth, gender, address, blood group, admission date"
                    : "name, email, phone/mob, qualification, designation"}
                </p>
              </div>
            </>
          ) : (
            /* Preview view */
            <div className="space-y-4">
              {/* Counts */}
              <div className="grid grid-cols-4 gap-3">
                <Stat n={preview.counts.total} label="Rows" color="text-slate-700" />
                <Stat n={preview.counts.valid} label="Ready" color="text-green-600" />
                <Stat n={preview.counts.duplicates} label="Duplicates" color="text-amber-600" />
                <Stat n={preview.counts.invalid} label="Invalid" color="text-red-600" />
              </div>

              {/* Mapping summary */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm">
                <span className="font-semibold text-slate-700">Detected columns: </span>
                {preview.fields.map((f) => (
                  <span key={f} className="inline-block mr-3">
                    {FIELD_LABELS[f] || f}
                    {preview.mapping[f] ? (
                      <span className="text-green-700"> ← “{preview.mapping[f]}”</span>
                    ) : (
                      <span className="text-slate-400"> (not found)</span>
                    )}
                  </span>
                ))}
                {preview.unmapped_headers.length > 0 && (
                  <div className="text-xs text-slate-400 mt-1">
                    Ignored columns: {preview.unmapped_headers.join(", ")}
                  </div>
                )}
              </div>

              {/* Preview table */}
              <div className="border rounded-lg overflow-hidden">
                <div className="max-h-72 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-100 sticky top-0">
                      <tr>
                        <th className="px-2 py-1.5 text-left">#</th>
                        <th className="px-2 py-1.5 text-left">Status</th>
                        {preview.fields.map((f) => (
                          <th key={f} className="px-2 py-1.5 text-left whitespace-nowrap">
                            {FIELD_LABELS[f] || f}
                          </th>
                        ))}
                        <th className="px-2 py-1.5 text-left">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((r) => (
                        <tr key={r.row} className="border-b align-top">
                          <td className="px-2 py-1.5 text-slate-400">{r.row}</td>
                          <td className="px-2 py-1.5">
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLE[r.status]}`}>
                              {r.status}
                            </span>
                          </td>
                          {preview.fields.map((f) => (
                            <td key={f} className="px-2 py-1.5 whitespace-nowrap">
                              {r.data[f] || <span className="text-slate-300">—</span>}
                            </td>
                          ))}
                          <td className="px-2 py-1.5 text-xs text-slate-500">
                            {r.issues.map((i, idx) => (
                              <div key={idx} className={i.level === "invalid" ? "text-red-600" : "text-amber-600"}>
                                {i.msg}
                              </div>
                            ))}
                            {r.status === "ok" && r.missing.length > 0 && (
                              <div className="text-slate-400">missing: {r.missing.join(", ")}</div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={skipInvalid} onChange={(e) => setSkipInvalid(e.target.checked)} />
                  Skip invalid &amp; duplicate rows
                </label>
                <span className="text-sm text-slate-500">
                  Will import <strong>{importableCount}</strong> row(s)
                  {skippable > 0 && skipInvalid && <span> · skipping {skippable}</span>}
                  {!skipInvalid && skippable > 0 && (
                    <span className="text-red-600"> — fix {skippable} flagged row(s) first</span>
                  )}
                </span>
                <div className="ml-auto flex gap-2">
                  <button onClick={reset} className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium px-4 py-2 rounded">
                    Choose another file
                  </button>
                  <button
                    onClick={doImport}
                    disabled={committing || importableCount === 0 || (!skipInvalid && skippable > 0)}
                    className="bg-green-600 hover:bg-green-700 text-white disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed font-medium px-5 py-2 rounded"
                  >
                    {committing ? "Importing…" : `Confirm import (${importableCount})`}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ n, label, color }: { n: number; label: string; color: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 text-center">
      <p className={`text-2xl font-bold ${color}`}>{n}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}
