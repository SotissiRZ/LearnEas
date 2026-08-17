"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { MessageCircle, Send, Loader2, CheckCircle2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Instructor } from "@/types";

export default function ContactInstructorButton({ instructor }: { instructor: Instructor }) {
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  function handleOpen() {
    if (!hydrated) return;
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setOpen(true);
  }

  async function handleSend() {
    if (!message.trim()) return;
    setSending(true);
    setError("");
    try {
      await api.post("/chat/messages/", { recipient: instructor.id, content: message });
      setSent(true);
      setMessage("");
      setTimeout(() => { setOpen(false); setSent(false); }, 1500);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible d'envoyer le message.");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button onClick={handleOpen} className="btn-outline mt-3 !py-1.5 !text-xs">
        <MessageCircle size={14} /> Contacter {instructor.full_name.split(" ")[0]}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setOpen(false)}>
          <div className="card w-full max-w-md p-5" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-bold">Message à {instructor.full_name}</h3>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={18} />
              </button>
            </div>

            {sent ? (
              <div className="flex items-center gap-2 rounded-lg bg-brand-50 p-3 text-sm text-brand-700">
                <CheckCircle2 size={18} /> Message envoyé !
              </div>
            ) : (
              <>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={4}
                  placeholder={`Bonjour ${instructor.full_name.split(" ")[0]}, j'aurais une question sur...`}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
                {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
                <button onClick={handleSend} disabled={sending || !message.trim()} className="btn-primary mt-3 w-full">
                  {sending ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Envoyer
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
