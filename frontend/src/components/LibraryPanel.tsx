import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Book {
  id: number;
  title: string;
  author: string | null;
  isbn: string | null;
  category: string | null;
  total_copies: number;
  available_copies: number;
}

interface Loan {
  id: number;
  book_title: string | null;
  student_name: string | null;
  issued_on: string | null;
  due_on: string | null;
  returned_on: string | null;
  status: string;
  overdue: boolean;
}

interface StudentResult {
  id: number;
  full_name: string;
  class_grade: string;
  section: string;
}

export default function LibraryPanel() {
  const [tab, setTab] = useState<"catalogue" | "loans">("catalogue");
  const [books, setBooks] = useState<Book[]>([]);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loanFilter, setLoanFilter] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  // add book
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [copies, setCopies] = useState("1");

  // issue
  const [issueBook, setIssueBook] = useState<Book | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StudentResult[]>([]);

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 2500); };

  const loadBooks = async () => setBooks(await api.library.books());
  const loadLoans = async () => setLoans(await api.library.loans(loanFilter || undefined));

  useEffect(() => { loadBooks().catch(() => setErr("Could not load books.")); }, []);
  useEffect(() => { if (tab === "loans") loadLoans().catch(() => setErr("Could not load loans.")); /* eslint-disable-next-line */ }, [tab, loanFilter]);

  const addBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      await api.library.createBook({ title: title.trim(), author: author.trim() || undefined, total_copies: Number(copies) || 1 });
      setTitle(""); setAuthor(""); setCopies("1");
      flash("Book added.");
      loadBooks();
    } catch (e: any) { setErr(e?.response?.data?.error || "Could not add book."); }
  };

  const removeBook = async (id: number) => {
    if (!window.confirm("Remove this book?")) return;
    try { await api.library.removeBook(id); loadBooks(); }
    catch (e: any) { setErr(e?.response?.data?.error || "Could not remove book."); }
  };

  const search = async () => {
    if (!query.trim()) return;
    setResults(await api.admin.students.list({ q: query.trim() }));
  };

  const issue = async (studentId: number) => {
    if (!issueBook) return;
    try {
      await api.library.issue({ book_id: issueBook.id, student_id: studentId });
      setIssueBook(null); setQuery(""); setResults([]);
      flash("Book issued.");
      loadBooks();
    } catch (e: any) { setErr(e?.response?.data?.error || "Could not issue book."); }
  };

  const returnLoan = async (id: number) => {
    await api.library.returnLoan(id);
    flash("Marked returned.");
    loadLoans(); loadBooks();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Library</h2>
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
          {(["catalogue", "loans"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`rounded-md px-3 py-1 text-sm font-medium capitalize ${tab === t ? "bg-white text-slate-900 shadow" : "text-slate-500"}`}>{t}</button>
          ))}
        </div>
      </div>

      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}
      {msg && <div className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{msg}</div>}

      {tab === "catalogue" && (
        <div className="space-y-4">
          <form onSubmit={addBook} className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-5 sm:grid-cols-4">
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" placeholder="Book title" value={title} onChange={(e) => setTitle(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Author" value={author} onChange={(e) => setAuthor(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="number" min={1} placeholder="Copies" value={copies} onChange={(e) => setCopies(e.target.value)} />
            <button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-4">Add book</button>
          </form>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-2">Title</th><th className="px-4 py-2">Author</th><th className="px-4 py-2">Available</th><th className="px-4 py-2 text-right">Actions</th></tr></thead>
              <tbody>
                {books.map((b) => (
                  <tr key={b.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-medium text-slate-800">{b.title}</td>
                    <td className="px-4 py-2">{b.author || "—"}</td>
                    <td className="px-4 py-2">{b.available_copies}/{b.total_copies}</td>
                    <td className="px-4 py-2 text-right">
                      <button disabled={b.available_copies <= 0} onClick={() => { setIssueBook(b); setQuery(""); setResults([]); }} className="mr-2 rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-40">Issue</button>
                      <button onClick={() => removeBook(b.id)} className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Delete</button>
                    </td>
                  </tr>
                ))}
                {!books.length && <tr><td colSpan={4} className="px-4 py-6 text-center text-slate-400">No books yet.</td></tr>}
              </tbody>
            </table>
          </div>

          {issueBook && (
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-4">
              <div className="mb-2 text-sm font-semibold text-slate-700">Issue “{issueBook.title}” to a student</div>
              <div className="flex gap-2">
                <input className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Search student name / admission no" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} />
                <button onClick={search} className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white">Search</button>
                <button onClick={() => setIssueBook(null)} className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700">Cancel</button>
              </div>
              <div className="mt-2 space-y-1">
                {results.map((r) => (
                  <button key={r.id} onClick={() => issue(r.id)} className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-emerald-50">
                    <span>{r.full_name} <span className="text-xs text-slate-400">({r.class_grade}-{r.section})</span></span>
                    <span className="text-xs font-semibold text-emerald-600">Issue →</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "loans" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Filter:</span>
            <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm" value={loanFilter} onChange={(e) => setLoanFilter(e.target.value)}>
              <option value="">All</option><option value="issued">Issued</option><option value="returned">Returned</option><option value="overdue">Overdue</option>
            </select>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-2">Book</th><th className="px-4 py-2">Student</th><th className="px-4 py-2">Due</th><th className="px-4 py-2">Status</th><th className="px-4 py-2 text-right">Action</th></tr></thead>
              <tbody>
                {loans.map((l) => (
                  <tr key={l.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-medium text-slate-800">{l.book_title}</td>
                    <td className="px-4 py-2">{l.student_name}</td>
                    <td className="px-4 py-2">{l.due_on || "—"}</td>
                    <td className="px-4 py-2">
                      {l.status === "returned" ? <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">returned</span>
                        : l.overdue ? <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">overdue</span>
                        : <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800">issued</span>}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {l.status === "issued" && <button onClick={() => returnLoan(l.id)} className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">Return</button>}
                    </td>
                  </tr>
                ))}
                {!loans.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-400">No loans.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
