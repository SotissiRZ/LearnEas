export type EmployerStatus = "none" | "pending" | "approved" | "rejected" | "suspended";

export type EmployerProfile = {
  id?: number;
  company_name?: string;
  slug?: string;
  description?: string;
  industry?: string;
  company_size?: string;
  website_url?: string;
  logo?: string | null;
  country?: string;
  city?: string;
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
  employer: {
    id: number;
    company_name: string;
    slug: string;
    description: string;
    industry: string;
    company_size: string;
    website_url: string;
    logo: string | null;
    country: string;
    city: string;
  };
  title: string;
  slug: string;
  kind: OpportunityKind;
  contract_type: string;
  work_mode: WorkMode;
  experience_level: string;
  description: string;
  responsibilities: string[];
  requirements: string[];
  skills_required: string[];
  skills_optional: string[];
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

export type OpportunityApplication = {
  id: number;
  opportunity: number;
  opportunity_title: string;
  opportunity_slug: string;
  company_name: string;
  status: string;
  cover_letter: string;
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
