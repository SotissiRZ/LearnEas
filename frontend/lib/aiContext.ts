export type AIPageContext = {
  path?: string;
  kind?: string;
  course_slug?: string;
  lesson_id?: number;
  lesson_title?: string;
  pdf_slug?: string;
  opportunity_slug?: string;
};

export const AI_CONTEXT_EVENT = "kalanpro:ai-context";

declare global {
  interface Window { __KALANPRO_AI_CONTEXT__?: AIPageContext }
}

export function publishAIContext(context: AIPageContext) {
  if (typeof window === "undefined") return;
  const value = { ...context, path: context.path || window.location.pathname };
  window.__KALANPRO_AI_CONTEXT__ = value;
  window.dispatchEvent(new CustomEvent(AI_CONTEXT_EVENT, { detail: value }));
}

export function inferAIContext(pathname: string): AIPageContext {
  const context: AIPageContext = { path: pathname };
  let match = pathname.match(/^\/(?:learn|courses)\/([^/?#]+)/);
  if (match) return { ...context, kind: pathname.startsWith("/learn/") ? "course-learning" : "course", course_slug: decodeURIComponent(match[1]) };
  match = pathname.match(/^\/pdfs\/([^/?#]+)/);
  if (match) return { ...context, kind: "pdf", pdf_slug: decodeURIComponent(match[1]) };
  match = pathname.match(/^\/opportunities\/([^/?#]+)/);
  if (match) return { ...context, kind: "opportunity", opportunity_slug: decodeURIComponent(match[1]) };
  return context;
}

export function currentAIContext(pathname: string): AIPageContext {
  const inferred = inferAIContext(pathname);
  if (typeof window === "undefined") return inferred;
  const published = window.__KALANPRO_AI_CONTEXT__;
  if (published?.path === pathname) return { ...inferred, ...published, path: pathname };
  return inferred;
}
