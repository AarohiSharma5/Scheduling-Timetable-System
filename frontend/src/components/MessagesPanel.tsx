import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";

interface Conversation {
  user_id: number;
  name: string;
  role: string | null;
  last_message: string;
  last_at: string | null;
  unread: number;
}

interface DirEntry { id: number; name: string; role: string }

interface Msg {
  id: number;
  body: string;
  mine: boolean | null;
  read: boolean;
  created_at: string | null;
}

export default function MessagesPanel() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [directory, setDirectory] = useState<DirEntry[]>([]);
  const [activeUser, setActiveUser] = useState<number | null>(null);
  const [partnerName, setPartnerName] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [err, setErr] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const loadConversations = async () => setConversations(await api.messages.conversations());

  useEffect(() => {
    loadConversations().catch(() => setErr("Could not load messages."));
    api.messages.directory().then(setDirectory).catch(() => {});
  }, []);

  const openThread = async (userId: number, name?: string) => {
    setActiveUser(userId);
    setShowNew(false);
    const res = await api.messages.thread(userId);
    setPartnerName(name || res.partner.name);
    setMessages(res.messages);
    loadConversations();
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  };

  const send = async () => {
    if (!draft.trim() || activeUser == null) return;
    try {
      await api.messages.send({ recipient_id: activeUser, body: draft.trim() });
      setDraft("");
      const res = await api.messages.thread(activeUser);
      setMessages(res.messages);
      loadConversations();
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Could not send message.");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Messages</h2>
        <button onClick={() => { setShowNew((v) => !v); setActiveUser(null); }} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">
          {showNew ? "Close" : "+ New message"}
        </button>
      </div>
      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Left: conversations / directory */}
        <div className="rounded-xl border border-slate-200 bg-white">
          {showNew ? (
            <div className="max-h-[28rem] overflow-y-auto">
              <div className="border-b border-slate-100 px-4 py-2 text-xs font-semibold uppercase text-slate-400">Start a conversation</div>
              {directory.map((d) => (
                <button key={d.id} onClick={() => openThread(d.id, d.name)} className="flex w-full items-center justify-between px-4 py-3 text-left text-sm hover:bg-slate-50">
                  <span className="font-medium text-slate-800">{d.name}</span>
                  <span className="text-xs capitalize text-slate-400">{d.role}</span>
                </button>
              ))}
              {!directory.length && <div className="px-4 py-6 text-center text-sm text-slate-400">No one to message.</div>}
            </div>
          ) : (
            <div className="max-h-[28rem] overflow-y-auto">
              {conversations.map((c) => (
                <button key={c.user_id} onClick={() => openThread(c.user_id, c.name)} className={`flex w-full flex-col px-4 py-3 text-left hover:bg-slate-50 ${activeUser === c.user_id ? "bg-indigo-50" : ""}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-800">{c.name}</span>
                    {c.unread > 0 && <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white">{c.unread}</span>}
                  </div>
                  <span className="truncate text-xs text-slate-500">{c.last_message}</span>
                </button>
              ))}
              {!conversations.length && <div className="px-4 py-6 text-center text-sm text-slate-400">No conversations yet.</div>}
            </div>
          )}
        </div>

        {/* Right: thread */}
        <div className="flex min-h-[28rem] flex-col rounded-xl border border-slate-200 bg-white md:col-span-2">
          {activeUser == null ? (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-400">Select a conversation</div>
          ) : (
            <>
              <div className="border-b border-slate-100 px-4 py-3 font-semibold text-slate-800">{partnerName}</div>
              <div className="flex-1 space-y-2 overflow-y-auto p-4">
                {messages.map((m) => (
                  <div key={m.id} className={`flex ${m.mine ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${m.mine ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                      {m.body}
                      <div className={`mt-0.5 text-[10px] ${m.mine ? "text-indigo-200" : "text-slate-400"}`}>
                        {m.created_at ? new Date(m.created_at).toLocaleString() : ""}
                      </div>
                    </div>
                  </div>
                ))}
                {!messages.length && <div className="text-center text-sm text-slate-400">No messages yet. Say hello!</div>}
                <div ref={endRef} />
              </div>
              <div className="flex gap-2 border-t border-slate-100 p-3">
                <input className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Type a message…" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
                <button onClick={send} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">Send</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
