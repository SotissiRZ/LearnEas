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
  legal_name?: string;
  registration_number?: string;
  registration_country?: string;
  verification_status?: "unverified" | "pending" | "verified" | "rejected";
  verification_note?: string;
  verification_submitted_at?: string | null;
  identity_verified_at?: string | null;
  is_identity_verified?: boolean;
  open_opportunities_count?: number;
  status: EmployerStatus;
  review_note?: string;
  reviewed_by_name?: string;
  reviewed_at?: string | null;
  created_at?: string;
  updated_at?: string;
};


export type CompanyProfile = {
  id: number;
  name: string;
  slug: string;
  tagline?: string;
  description?: string;
  industry?: string;
  website_url?: string;
  contact_email?: string;
  logo?: string | null;
  banner?: string | null;
  country?: string;
  city?: string;
  status?: EmployerStatus;
  verification_status?: "unverified" | "pending" | "verified" | "rejected";
  [key: string]: any;
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

export type OpportunityKind =
  | "job"
  | "internship"
  | "freelance"
  | "mission"
  | "apprenticeship"
  | "volunteer";
export type OpportunityWorkMode = "remote" | "hybrid" | "onsite";
export type WorkMode = OpportunityWorkMode;
export type OpportunityExperience = "entry" | "junior" | "mid" | "senior" | "lead";
export type OpportunityStatus =
  | "draft"
  | "pending_review"
  | "published"
  | "rejected"
  | "closed"
  | "filled"
  | "archived";
export type JobApplicationStatus =
  | "submitted"
  | "reviewing"
  | "shortlisted"
  | "interview"
  | "offer"
  | "hired"
  | "rejected"
  | "withdrawn";

export type Opportunity = {
  id: number;
  employer: EmployerProfile & { id: number; company_name: string; slug: string; status: EmployerStatus };
  /** Legacy/admin compatibility: older moderation screens use `company` instead of `employer`. */
  company: CompanyProfile;
  title: string;
  slug: string;
  kind: OpportunityKind;
  contract_type: string;
  work_mode: OpportunityWorkMode;
  experience_level: OpportunityExperience;
  description: string;
  department: string;
  openings: number;
  cover_image: string | null;
  responsibilities: string[];
  requirements: string[];
  skills_required: string[];
  /** Legacy alias retained for pre-v75 admin/opportunity screens. */
  required_skills: string[];
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
  status: OpportunityStatus;
  featured: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  applications_count?: number;
  match_score?: number | null;
  already_applied?: boolean;
  is_open: boolean;
  /** Compatibility fields used by the recruiter workspace introduced before the salary_* API naming was consolidated. */
  compensation_min?: string | number | null;
  compensation_max?: string | number | null;
  compensation_currency?: string;
  compensation_period: "hour" | "month" | "year" | "project";
  [key: string]: any;
};

export type ScreeningAnswer = { question: string; answer: string };

export type OpportunityApplication = {
  id: number;
  opportunity: number;
  opportunity_title: string;
  opportunity_slug: string;
  company_name: string;
  status: JobApplicationStatus;
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

export type EmployerJobApplication = {
  id: number;
  opportunity: number;
  opportunity_title: string;
  opportunity_slug: string;
  status: JobApplicationStatus;
  candidate_name: string;
  candidate_email: string;
  candidate_country: string;
  candidate_headline: string;
  cover_letter: string;
  cv_file: string | null;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  employer_message?: string;
  candidate_snapshot?: {
    portfolio_public?: boolean;
    portfolio_slug?: string;
    verified_projects_count?: number;
    active_certificates_count?: number;
    [key: string]: unknown;
  };
  submitted_at: string;
  updated_at?: string;
  [key: string]: any;
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
  match_score?: number | null;
  match_breakdown?: {
    total: number;
    components: Record<string, number>;
    matched_required_skills: string[];
    missing_required_skills: string[];
    matched_optional_skills: string[];
    strengths: string[];
  } | null;
  updated_at: string;
};

export type SavedTalentSearch = {
  id: number;
  name: string;
  search_text: string;
  country: string;
  availability: string;
  min_experience: number;
  opportunity: number | null;
  opportunity_title: string;
  min_match_score: number;
  alerts_enabled: boolean;
  last_checked_at: string | null;
  last_match_count: number;
  created_at: string;
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
