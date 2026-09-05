export type EmployerStatus = "none" | "pending" | "approved" | "rejected" | "suspended";

export type EmployerProfile = {
  id?: number;
  company_name?: string;
  slug?: string;
  tagline?: string;
  description?: string;
  industry?: string;
  company_size?: string;
  website_url?: string;
  linkedin_url?: string;
  contact_email?: string;
  founded_year?: number | null;
  brand_color?: string;
  logo?: string | null;
  banner?: string | null;
  values?: string[];
  benefits?: string[];
  hiring_regions?: string[];
  country?: string;
  city?: string;
  open_opportunities_count?: number;
  status: EmployerStatus;
  review_note?: string;
  reviewed_by_name?: string;
  reviewed_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type CandidateProfile = {
  id: number;
  headline: string;
  summary: string;
  skills: string[];
  desired_roles: string[];
  preferred_kinds: string[];
  preferred_work_modes: string[];
  preferred_countries: string[];
  minimum_salary: string | null;
  salary_currency: string;
  availability: string;
  years_experience: number;
  resume_url: string | null;
  is_searchable: boolean;
  portfolio_slug: string;
  updated_at: string;
};

export type OpportunityKind = "job" | "internship" | "freelance" | "mission";
export type WorkMode = "remote" | "hybrid" | "onsite";

export type Opportunity = {
  id: number;
  employer: EmployerProfile & { id: number; company_name: string; slug: string; status: EmployerStatus };
  title: string;
  slug: string;
  kind: OpportunityKind;
  contract_type: string;
  work_mode: WorkMode;
  experience_level: string;
  description: string;
  department: string;
  openings: number;
  cover_image: string | null;
  responsibilities: string[];
  requirements: string[];
  skills_required: string[];
  skills_optional: string[];
  screening_questions: string[];
  country: string;
  city: string;
  remote_worldwide: boolean;
  salary_min: string | null;
  salary_max: string | null;
  salary_currency: string;
  salary_period: string;
  show_salary: boolean;
  apply_mode: "internal" | "external";
  external_application_url: string;
  application_deadline: string | null;
  status: "draft" | "published" | "closed" | "archived";
  featured: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  applications_count?: number;
  match_score?: number | null;
  already_applied?: boolean;
  is_open: boolean;
};

export type ScreeningAnswer = { question: string; answer: string };

export type OpportunityApplication = {
  id: number;
  opportunity: number;
  opportunity_title: string;
  opportunity_slug: string;
  company_name: string;
  status: string;
  cover_letter: string;
  screening_answers: ScreeningAnswer[];
  resume_url: string | null;
  share_portfolio: boolean;
  match_score: number;
  candidate_name_snapshot: string;
  candidate_email_snapshot: string;
  country_snapshot: string;
  headline_snapshot: string;
  skills_snapshot: string[];
  portfolio_snapshot: { slug?: string; title?: string; about?: string; skills?: string[]; is_public?: boolean };
  certificates_snapshot: Array<{ number: string; verification_code: string; title: string; skills: string[]; issued_at: string }>;
  verified_projects_snapshot: Array<{
    title: string;
    course: string;
    assignment: string;
    instructor: string;
    score: string | null;
    max_score: number | null;
    verified_at: string | null;
    skills: string[];
  }>;
  recruiter_note?: string;
  recruiter_rating?: number;
  recruiter_tags?: string[];
  next_step_at?: string | null;
  applied_at: string;
  updated_at: string;
};

export type Talent = {
  id: number;
  full_name: string;
  avatar: string | null;
  country: string;
  headline: string;
  summary: string;
  skills: string[];
  desired_roles: string[];
  availability: string;
  years_experience: number;
  portfolio_slug: string;
  updated_at: string;
};

export type TalentBookmark = {
  id: number;
  talent: number;
  talent_detail: Talent;
  note: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type EmployerAnalytics = {
  opportunities_total: number;
  published: number;
  drafts: number;
  applications_total: number;
  pipeline: Record<string, number>;
  shortlisted: number;
  interviews: number;
  offers: number;
  hires: number;
  average_match: number;
  bookmarked_talents: number;
};

export type TalentAccessLog = {
  id: number;
  access_type: "profile" | "bookmark" | "application";
  company_name: string;
  company_slug?: string;
  created_at: string;
};

export type EmployerEntitlement = {
  id: number;
  kind: "single_post" | "pro" | "business";
  entitlement_key: string;
  starts_at: string | null;
  ends_at: string | null;
  revoked_at: string | null;
  consumed_at: string | null;
  consumed_opportunity: { id: number; title: string; slug: string; status: string } | null;
  current?: boolean;
  revocation_reason?: string;
  created_at: string;
};

export type EmployerCommercialAccess = {
  plan: "starter" | "pro" | "business";
  active_job_limit: number;
  talent_pool: boolean;
  unused_single_post_credits: number;
  entitlements: EmployerEntitlement[];
};

export type ApplicationHistoryEvent = {
  id: number;
  event_type: string;
  label: string;
  metadata: Record<string, unknown>;
  actor_name?: string;
  created_at: string;
};

export type RecruitmentInterview = {
  id: number;
  application: number;
  scheduled_at: string;
  duration_minutes: number;
  mode: string;
  location_or_url: string;
  candidate_message: string;
  status: "scheduled" | "completed" | "cancelled";
  created_at: string;
  updated_at: string;
};

export type EmploymentOffer = {
  id: number;
  application: number;
  title: string;
  message: string;
  salary_amount: string | null;
  salary_currency: string;
  start_date: string | null;
  expires_at: string | null;
  status: "pending" | "accepted" | "declined" | "withdrawn";
  responded_at: string | null;
  created_at: string;
  updated_at: string;
};
