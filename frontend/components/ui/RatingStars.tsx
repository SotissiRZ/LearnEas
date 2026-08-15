import { Star } from "lucide-react";

export default function RatingStars({ value, count, size = 14 }: { value: number; count?: number; size?: number }) {
  const rounded = Math.round(value * 2) / 2;
  return (
    <div className="flex items-center gap-1">
      <span className="text-sm font-semibold text-amber-600">{value.toFixed(1)}</span>
      <div className="flex">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star
            key={i}
            size={size}
            className={i <= rounded ? "fill-amber-400 text-amber-400" : "fill-gray-200 text-gray-200"}
          />
        ))}
      </div>
      {typeof count === "number" && <span className="text-xs text-gray-400">({count})</span>}
    </div>
  );
}
