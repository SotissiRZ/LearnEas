import SearchClient from "@/components/discovery/SearchClient";

export const metadata = {
  title: "Recherche | KalanPro",
  description: "Recherchez des cours, formations, PDF, mentors, opportunités et entreprises sur KalanPro.",
  robots: { index: false, follow: true },
};

type Props = { searchParams: Promise<{ q?: string }> };

export default async function SearchPage({ searchParams }: Props) {
  const params = await searchParams;
  return <SearchClient initialQuery={(params.q || "").slice(0, 120)} />;
}
