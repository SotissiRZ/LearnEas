import { safePublicGet } from "@/lib/serverPublicApi";
import { HelpCircle } from "lucide-react";

interface FAQItem { id: number; question: string; answer: string; }

export default async function FaqPage() {
  const result = await safePublicGet<{ results: FAQItem[] } | FAQItem[]>("/faq/", { results: [] } as any, 300);
  const data = result.data;
  const items: FAQItem[] = (data as any).results || (data as any);

  return (
    <div className="container-app max-w-3xl py-10">
      <h1 className="mb-6 flex items-center gap-2 text-3xl font-extrabold">
        <HelpCircle className="text-brand-600" /> Foire aux questions
      </h1>
      {items.length === 0 ? (
        <p className="text-gray-500">Aucune question pour le moment.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <details key={item.id} className="card p-4">
              <summary className="cursor-pointer font-semibold">{item.question}</summary>
              <p className="mt-2 text-sm text-gray-600">{item.answer}</p>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
