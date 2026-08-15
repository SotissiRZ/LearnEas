"use client";

import { useState } from "react";
import { Mail, Send } from "lucide-react";

export default function ContactPage() {
  const [sent, setSent] = useState(false);

  return (
    <div className="container-app max-w-xl py-16">
      <h1 className="mb-2 flex items-center gap-2 text-3xl font-extrabold"><Mail className="text-brand-600" /> Contactez-nous</h1>
      <p className="mb-8 text-gray-500">Une question, un problème ? Écrivez-nous, nous répondons sous 24h.</p>

      {sent ? (
        <div className="card p-6 text-brand-700">Merci, votre message a bien été envoyé !</div>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); setSent(true); }} className="card flex flex-col gap-4 p-6">
          <input required placeholder="Votre nom" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <input required type="email" placeholder="Votre email" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <textarea required rows={5} placeholder="Votre message" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <button type="submit" className="btn-primary"><Send size={16} /> Envoyer</button>
        </form>
      )}
    </div>
  );
}
