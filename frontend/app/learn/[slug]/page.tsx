import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { Course } from "@/types";
import LearnClient from "@/components/course/LearnClient";

async function getCourse(slug: string): Promise<Course | null> {
  try {
    return await api.get<Course>(`/catalog/courses/${slug}/`);
  } catch {
    return null;
  }
}

export default async function LearnPage({ params }: { params: { slug: string } }) {
  const course = await getCourse(params.slug);
  if (!course) notFound();
  return <LearnClient course={course} />;
}
