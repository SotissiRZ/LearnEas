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
  certificate_enabled?: boolean;
  certificate_auto_issue?: boolean;
  certificate_threshold_percent?: number;
  certificate_validity_months?: number | null;
  certificate_title?: string;
  certificate_subtitle?: string;
  certificate_description?: string;
  certificate_signatory_name?: string;
  certificate_signatory_title?: string;
  certificate_accent_color?: string;
  certificate_number_prefix?: string;
  certificate_show_duration?: boolean;
  certificate_show_instructor?: boolean;
  certificate_show_completion_date?: boolean;
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
  subtitles_file?: string | null;
  transcript?: string;
  hls_url?: string | null;
  audio_hls_url?: string | null;
  streaming_status?: "pending" | "processing" | "ready" | "failed" | string;
  streaming_variants?: Array<{ height: number; width?: number; bandwidth?: number }>;
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
  technical_admin?: boolean;
  avatar: string | null;
  country?: string;
  headline?: string;
  domain?: string;
}

export interface LessonProgress {
  id: number;
  enrollment: number;
  lesson: number;
  completed: boolean;
  watched_seconds: number;
  last_position_seconds: number;
  updated_at: string;
}

export interface CourseEnrollment {
  id: number;
  course: Course;
  purchased_at: string;
  progress_percent: number;
  completed: boolean;
  certificate_issued: boolean;
  last_accessed_lesson?: number | null;
  lesson_progress?: LessonProgress[];
}

export interface LessonNote {
  id: number;
  lesson: number;
  lesson_title: string;
  section_title: string;
  course_id: number;
  timestamp_seconds: number;
  content: string;
  created_at: string;
  updated_at: string;
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
  actual_duration_seconds: number;
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
  is_enrollment_open?: boolean;
  cohort_name?: string;
  cohort_timezone?: string;
  enrollment_deadline?: string | null;
  min_students?: number;
  created_at: string;
  description?: string;
  sessions?: FormationSession[];
  is_enrolled?: boolean;
  certificate_enabled?: boolean;
  certificate_auto_issue?: boolean;
  certificate_attendance_percent?: number;
  certificate_validity_months?: number | null;
  certificate_title?: string;
  certificate_subtitle?: string;
  certificate_description?: string;
  certificate_signatory_name?: string;
  certificate_signatory_title?: string;
  certificate_accent_color?: string;
  certificate_number_prefix?: string;
  certificate_show_duration?: boolean;
  certificate_show_instructor?: boolean;
  certificate_show_completion_date?: boolean;
}

export interface FormationEnrollment {
  id: number;
  formation: InteractiveFormation;
  enrolled_at: string;
  certificate_issued: boolean;
}

export interface MentorshipSlot {
  id: number;
  offering: number;
  starts_at: string;
  duration_minutes: number;
  is_active: boolean;
  is_available: boolean;
  session: number | null;
}

export interface MentorshipOffering {
  id: number;
  title: string;
  slug: string;
  description: string;
  instructor: Instructor;
  duration_minutes: number;
  price: string;
  language: string;
  timezone: string;
  booking_notice_hours: number;
  cancellation_notice_hours: number;
  published: boolean;
  next_slots: MentorshipSlot[];
  created_at: string;
}

export type MentorshipBookingStatus = "pending_payment" | "confirmed" | "completed" | "cancelled" | "expired";

export interface MentorshipBooking {
  id: number;
  offering: MentorshipOffering;
  slot: MentorshipSlot;
  status: MentorshipBookingStatus;
  price_snapshot: string;
  expires_at: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  learner_note: string;
  mentor_note: string;
  created_at: string;
  updated_at: string;
  join_session_id: number | null;
  mentor_name: string;
  learner_name: string;
}

export interface Certificate {
  id: number;
  certificate_number: string;
  verification_code: string;
  verification_url: string;
  status: "active" | "revoked" | "expired";
  effective_status: "active" | "revoked" | "expired";
  issued_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  revocation_reason: string;
  achievement_percent: string;
  student_name: string;
  content_type: "course" | "formation";
  content_title: string;
  instructor_name: string;
  title: string;
  subtitle: string;
  description: string;
  signatory_name: string;
  signatory_title: string;
  accent_color: string;
  duration_minutes: number;
  completed_at: string | null;
  display_options: Record<string, boolean>;
  metadata: Record<string, unknown>;
  course_enrollment: number | null;
  formation_enrollment: number | null;
}
