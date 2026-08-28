"use client";

import { ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";
import InstructorSidebar from "./InstructorSidebar";

export default function InstructorShell({ children }: { children: ReactNode }) {
  const { user, hydrated } = useAuth();

  // Les étudiants qui consultent /dashboard/instructor voient le formulaire de candidature
  // sans sidebar instructeur tant que leur rôle n'a pas été approuvé.
  if (!hydrated || !user || !["instructor", "admin"].includes(user.role)) return <>{children}</>;

  return (
    <div className="container-app py-8">
      <div className="grid gap-6 lg:grid-cols-[235px_minmax(0,1fr)]">
        <InstructorSidebar />
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}
