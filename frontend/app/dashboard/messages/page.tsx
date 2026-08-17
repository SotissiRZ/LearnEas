"use client";

import { useEffect, useMemo, useState } from "react";
import { MessageCircle, Send, Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface ChatMessage {
  id: number;
  sender: number;
  sender_name: string;
  recipient: number;
  recipient_name: string;
  content: string;
  created_at: string;
}

export default function MessagesPage() {
  const { user, ready } = useAuthGuard();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: ChatMessage[] } | ChatMessage[]>("/chat/messages/")
      .then((d: any) => setMessages(d.results || d))
      .finally(() => setLoading(false));
  }, [ready]);

  const conversations = useMemo(() => {
    if (!user) return [];
    const map = new Map<number, { id: number; name: string; lastMessage: ChatMessage }>();
    for (const m of messages) {
      const otherId = m.sender === user.id ? m.recipient : m.sender;
      const otherName = m.sender === user.id ? m.recipient_name : m.sender_name;
      const existing = map.get(otherId);
      if (!existing || new Date(m.created_at) > new Date(existing.lastMessage.created_at)) {
        map.set(otherId, { id: otherId, name: otherName, lastMessage: m });
      }
    }
    return Array.from(map.values()).sort(
      (a, b) => new Date(b.lastMessage.created_at).getTime() - new Date(a.lastMessage.created_at).getTime()
    );
  }, [messages, user]);

  const activeThread = useMemo(
    () => messages
      .filter((m) => (user && (m.sender === activeId || m.recipient === activeId)))
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
    [messages, activeId, user]
  );

  async function handleReply() {
    if (!reply.trim() || !activeId) return;
    setSending(true);
    try {
      const msg = await api.post<ChatMessage>("/chat/messages/", { recipient: activeId, content: reply });
      setMessages((prev) => [...prev, msg]);
      setReply("");
    } catch {
      /* noop */
    } finally {
      setSending(false);
    }
  }

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <h1 className="mb-6 flex items-center gap-2 text-2xl font-extrabold">
        <MessageCircle className="text-brand-600" /> Messagerie
      </h1>

      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : conversations.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          Aucune conversation pour le moment. Contactez un instructeur depuis une fiche cours pour démarrer une discussion.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-0 overflow-hidden rounded-xl2 border border-gray-100 md:grid-cols-[280px_1fr]">
          <div className="divide-y divide-gray-100 border-b border-gray-100 md:border-b-0 md:border-r">
            {conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveId(c.id)}
                className={`block w-full p-4 text-left text-sm hover:bg-gray-50 ${activeId === c.id ? "bg-brand-50" : ""}`}
              >
                <p className="font-semibold">{c.name}</p>
                <p className="line-clamp-1 text-xs text-gray-500">{c.lastMessage.content}</p>
              </button>
            ))}
          </div>

          <div className="flex flex-col p-4">
            {!activeId ? (
              <p className="m-auto text-sm text-gray-400">Sélectionnez une conversation</p>
            ) : (
              <>
                <div className="flex-1 space-y-3 overflow-y-auto pb-4" style={{ maxHeight: 400 }}>
                  {activeThread.map((m) => (
                    <div
                      key={m.id}
                      className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                        m.sender === user?.id ? "ml-auto bg-brand-600 text-white" : "bg-gray-100 text-ink"
                      }`}
                    >
                      {m.content}
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 border-t border-gray-100 pt-3">
                  <input
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleReply()}
                    placeholder="Votre message..."
                    className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  />
                  <button onClick={handleReply} disabled={sending} className="btn-primary !px-4">
                    {sending ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
