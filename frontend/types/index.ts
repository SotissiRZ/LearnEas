export interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  courses_count: number;
}

export interface Instructor {
  id: number;
  full_name: string;
  avatar: string | null;
  bio: string;
  headline: string;
  domain: string;
  years_experience: number;
  courses_count: number;
}

export type Level = "beginner" | "intermediate" | "expert";

export interface Course {
  id: number;
  title: string;
  slug: string;
  subtitle: string;
  category: Category | null;
  instructor: Instructor;
  level: Level;
  language: string;
  price: string;
  discount_price: string | null;
  effective_price: number;
  is_free: boolean;
  thumbnail: string | null;
  total_duration_minutes: number;
  total_hours: number;
  total_lessons: number;
  students_count: number;
  rating_avg: string;
  rating_count: number;
  featured: boolean;
  published: boolean;
  created_at: string;
  description?: string;
  what_you_will_learn?: string[];
  requirements?: string[];
  target_audience?: string[];
  promo_video_url?: string;
  sections?: Section[];
  pdf_resources?: PDFResource[];
  is_enrolled?: boolean;
}

export interface Section {
  id: number;
  title: string;
  order: number;
  duration_minutes: number;
  lessons: Lesson[];
}

export interface Lesson {
  id: number;
  title: string;
  video_url: string | null;
  video_file: string | null;
  duration_minutes: number;
  order: number;
  is_preview: boolean;
  description: string;
  locked: boolean;
}

export interface PDFResource {
  id: number;
  title: string;
  cover_image: string | null;
  file: string | null;
  page_count: number;
  is_free_sample: boolean;
  order: number;
  locked: boolean;
}

export interface PDFProduct {
  id: number;
  title: string;
  slug: string;
  category: Category | null;
  instructor: Instructor;
  level: Level;
  language: string;
  price: string;
  is_free: boolean;
  cover_image: string | null;
  page_count: number;
  downloads_count: number;
  rating_avg: string;
  rating_count: number;
  featured: boolean;
  published: boolean;
  created_at: string;
  description?: string;
  file?: string | null;
  preview_file?: string | null;
  is_purchased?: boolean;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "instructor" | "student";
  avatar: string | null;
  headline?: string;
  domain?: string;
}

export interface CourseEnrollment {
  id: number;
  course: Course;
  purchased_at: string;
  progress_percent: number;
  completed: boolean;
  certificate_issued: boolean;
}

export interface FormationSession {
  id: number;
  session_number: number;
  scheduled_at: string;
  duration_minutes: number;
  completed: boolean;
  notes: string;
  started_at: string | null;
  ended_at: string | null;
  actual_duration_minutes: number;
  can_join: boolean;
}

export type FormationStatus = "draft" | "scheduled" | "in_progress" | "completed" | "cancelled";

export interface InteractiveFormation {
  id: number;
  title: string;
  slug: string;
  category: Category | null;
  instructor: Instructor;
  co_instructor: Instructor | null;
  level: Level;
  language: string;
  price: string;
  num_sessions: number;
  session_duration_minutes: number;
  max_students: number;
  thumbnail: string | null;
  start_date: string | null;
  end_date: string | null;
  status: FormationStatus;
  published: boolean;
  students_count: number;
  seats_left: number;
  is_full: boolean;
  created_at: string;
  description?: string;
  sessions?: FormationSession[];
  is_enrolled?: boolean;
}

export interface FormationEnrollment {
  id: number;
  formation: InteractiveFormation;
  enrolled_at: string;
  certificate_issued: boolean;
}
