import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vérifier un certificat · LearnEas",
  description: "Registre public de vérification des certificats LearnEas.",
  robots: { index: false, follow: false },
};

export default function CertificateVerifyLayout({ children }: { children: React.ReactNode }) {
  return children;
}
