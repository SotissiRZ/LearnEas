import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import AppHydrator from "@/components/layout/AppHydrator";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "LearnEas · La formation en ligne pensée pour l'Afrique",
  description:
    "LearnEas est la plateforme africaine de formation en ligne : cours complets (playlists vidéo), " +
    "formations interactives en direct et ressources PDF, avec paiement par Mobile Money, carte ou PayPal.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="flex min-h-screen flex-col font-sans">
        <AppHydrator />
        <Navbar />
        <div className="h-16 shrink-0" aria-hidden="true" />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
