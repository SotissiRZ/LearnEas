export type DiscoveryKind = "course" | "formation" | "pdf" | "mentor" | "opportunity" | "company" | "talent";

export type DiscoveryResult = {
  type: DiscoveryKind;
  id: number;
  title: string;
  subtitle: string;
  description: string;
  url: string;
  image: string | null;
  score: number;
  reason?: string;
  meta: Record<string, string | number | boolean | string[] | null | undefined>;
};

export type GlobalSearchResponse = {
  query: string;
  types: DiscoveryKind[];
  available_types: DiscoveryKind[];
  count: number;
  groups: Partial<Record<DiscoveryKind, DiscoveryResult[]>>;
  results: DiscoveryResult[];
};

export type RecommendationResponse = {
  personalized: boolean;
  signals: string[];
  learning: DiscoveryResult[];
  opportunities: DiscoveryResult[];
  talents: DiscoveryResult[];
};
