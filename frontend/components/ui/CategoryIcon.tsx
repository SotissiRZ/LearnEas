import * as Icons from "lucide-react";
import { BookOpen } from "lucide-react";

export default function CategoryIcon({ name, size = 20, className }: { name: string; size?: number; className?: string }) {
  const IconComp = (Icons as any)[name] || BookOpen;
  return <IconComp size={size} className={className} />;
}
