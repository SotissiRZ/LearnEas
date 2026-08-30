"use client";
import { useParams } from "next/navigation";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Course } from "@/types";
import LearnClient from "@/components/course/LearnClient";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";

export default function LearnPage() { const params = useParams<{ slug: string }>();
  const { ready } = useAuthGuard();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    api.get<Course>(`/catalog/courses/${params.slug}/`)
      .then(setCourse)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Cours introuvable."));
  }, [ready, params.slug]);

  if (!ready || (!course && !error)) return <GuardScreen />;
  if (error || !course) {
    return <div className="container-app py-20 text-center text-gray-500">{error || "Cours introuvable."}</div>;
  }
  return <LearnClient course={course} />;
}
