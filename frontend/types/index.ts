export interface Domain {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  order: number;
  courses_count?: number;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  domain: Domain | null;
  courses_count?: number;
}

export interface Instructor {
  id: number;
  full_name: string;
  avatar: string | null;
  bio: string;
  headline: string;
  domain: string;
  years_experience: number;
  courses_count?: number;
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
  project_count?: number;
  required_project_count?: number;
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
  qr_url?: string;
  issuer_name?: string;
  issuer_country?: string;
  skills_snapshot?: string[];
  projects_snapshot?: Array<{
    title: string;
    required_for_certificate?: boolean;
    score?: number | null;
    max_score?: number | null;
    validated_at?: string | null;
    validated_by?: string;
    skills?: string[];
  }>;
  credential_digest?: string;
  schema_version?: number;
  supersedes_certificate_number?: string | null;
  replacement_verification_url?: string | null;
  events?: Array<{
    id: number;
    event_type: "issued" | "revoked" | "reissued" | "expired";
    actor_name: string;
    details: Record<string, unknown>;
    created_at: string;
  }>;
}

export type ProjectSubmissionStatus = "draft" | "submitted" | "changes_requested" | "approved" | "rejected";

export interface ProjectSubmissionSummary {
  id: number;
  assignment: number;
  assignment_title: string;
  course_title: string;
  title: string;
  summary: string;
  external_url: string;
  repository_url: string;
  artifact_file: string | null;
  cover_image: string | null;
  skills: string[];
  status: ProjectSubmissionStatus;
  score: string | null;
  instructor_feedback: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  resubmission_count: number;
  is_late: boolean;
  can_resubmit: boolean;
  updated_at: string;
}

export interface ProjectAssignment {
  id: number;
  course: number;
  course_title: string;
  course_slug: string;
  instructor_name: string;
  title: string;
  slug: string;
  brief: string;
  instructions: string;
  objectives: string[];
  deliverables: string[];
  skills: string[];
  due_days_after_enrollment: number | null;
  max_score: number;
  passing_score: number;
  required_for_certificate: boolean;
  allow_resubmission: boolean;
  max_resubmissions: number | null;
  published: boolean;
  order: number;
  due_at: string | null;
  submission: ProjectSubmissionSummary | null;
  submissions_count?: number;
  awaiting_review_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectSubmission extends ProjectSubmissionSummary {
  student_name: string;
  student_email: string;
  course_slug: string;
  passing_score: number;
  max_score: number;
  required_for_certificate: boolean;
  enrollment: number;
  student: number;
  reviewed_by: number | null;
  revisions: Array<{
    id: number;
    revision_number: number;
    title: string;
    summary: string;
    external_url: string;
    repository_url: string;
    artifact_file: string | null;
    cover_image: string | null;
    skills: string[];
    submitted_at: string;
  }>;
}

export interface PortfolioProfile {
  id: number;
  slug: string;
  is_public: boolean;
  title: string;
  about: string;
  skills: string[];
  website_url: string;
  linkedin_url: string;
  github_url: string;
  open_to_work: boolean;
  show_country: boolean;
  show_project_scores: boolean;
  full_name: string;
  avatar: string | null;
  country: string;
  user_headline: string;
  public_url: string;
  updated_at: string;
}

export interface PortfolioItem {
  id: number;
  source_submission: number | null;
  title: string;
  description: string;
  cover_image: string | null;
  external_url: string;
  repository_url: string;
  skills: string[];
  is_public: boolean;
  featured: boolean;
  order: number;
  is_verified: boolean;
  verified_course_title: string;
  verified_assignment_title: string;
  verified_instructor_name: string;
  verified_at: string | null;
  verified_score: string | null;
  verified_max_score: number | null;
  verified_score_display: string | null;
  created_at: string;
  updated_at: string;
}

export interface PublicPortfolio {
  slug: string;
  title: string;
  about: string;
  skills: string[];
  website_url: string;
  linkedin_url: string;
  github_url: string;
  open_to_work: boolean;
  full_name: string;
  avatar: string | null;
  country: string;
  user_headline: string;
  updated_at: string;
  items: Array<{
    id: number;
    title: string;
    description: string;
    cover_image: string | null;
    external_url: string;
    repository_url: string;
    skills: string[];
    featured: boolean;
    is_verified: boolean;
    verified_course_title: string;
    verified_assignment_title: string;
    verified_instructor_name: string;
    verified_at: string | null;
    score: { value: number; max: number | null } | null;
  }>;
}

export interface AIQuota {
  used: number;
  limit: number;
  remaining: number;
  unlimited: boolean;
}

export interface AIStatus {
  enabled: boolean;
  rag_enabled: boolean;
  history_enabled: boolean;
  tools_enabled: boolean;
  dry_run: boolean;
  provider_ready: boolean;
  model: string;
  quota: AIQuota;
}

export interface AISource {
  id: number;
  title: string;
  type: "course" | "lesson" | "pdf_resource" | "pdf_product" | string;
  path: string;
  metadata: Record<string, unknown>;
  score?: number;
}


export interface AIAction {
  id: number;
  token: string;
  tool: string;
  label: string;
  status: "proposed" | "executed" | "rejected" | "failed" | string;
  requires_confirmation: boolean;
  expires_at?: string | null;
  result?: Record<string, unknown>;
  error?: string;
}

export interface AIMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources: AISource[];
  actions?: AIAction[];
  provider?: string;
  model?: string;
  feedback?: "helpful" | "unhelpful" | "";
  feedback_comment?: string;
  feedback_at?: string | null;
  created_at: string;
}

export interface AIConversation {
  id: number;
  title: string;
  context_preview: Record<string, unknown>;
  archived: boolean;
  created_at: string;
  updated_at: string;
  messages_count?: number;
  messages?: AIMessage[];
}

export interface AIAdminSettings {
  enabled: boolean;
  rag_enabled: boolean;
  history_enabled: boolean;
  tools_enabled: boolean;
  student_enabled: boolean;
  instructor_enabled: boolean;
  admin_enabled: boolean;
  default_model: string;
  student_monthly_limit: number;
  instructor_monthly_limit: number;
  admin_monthly_limit: number;
  max_history_messages: number;
  max_context_chunks: number;
  max_output_tokens: number;
  temperature: string | number;
  input_cost_per_million_eur: string | number;
  output_cost_per_million_eur: string | number;
  custom_system_prompt: string;
  updated_at: string;
}
