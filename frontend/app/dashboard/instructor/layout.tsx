import { ReactNode } from "react";
import InstructorShell from "@/components/instructor/InstructorShell";

export default function InstructorLayout({ children }: { children: ReactNode }) {
  return <InstructorShell>{children}</InstructorShell>;
}
