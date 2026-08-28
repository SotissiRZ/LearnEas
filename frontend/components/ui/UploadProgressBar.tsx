import { Loader2 } from "lucide-react";

export default function UploadProgressBar({ percent, label }: { percent: number; label?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <Loader2 size={12} className="animate-spin" /> {label || "Envoi en cours..."}
        </span>
        <span>{percent}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-brand-600 transition-all duration-150"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
