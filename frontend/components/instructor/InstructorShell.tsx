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
    <div className="lg:fixed lg:inset-x-0 lg:bottom-0 lg:top-16 lg:z-30 lg:overflow-hidden lg:bg-white">
      <div className="container-app py-4 lg:h-full lg:max-w-none lg:px-0 lg:py-0">
        <div className="grid gap-4 lg:relative lg:block lg:h-full lg:min-h-0">
          <InstructorSidebar />
          <main className="min-w-0 lg:ml-16 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:overscroll-contain lg:px-5 lg:py-4 lg:pb-8 lg:transition-[margin-left] lg:duration-200 lg:ease-out lg:peer-hover:ml-60">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
