import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import AppHydrator from "@/components/layout/AppHydrator";

export const metadata: Metadata = {
  title: "LearnEas — Apprenez sans limites",
  description:
    "LearnEas est la plateforme de formation en ligne qui vous permet d'acheter des cours complets " +
    "(playlists vidéo) et des ressources PDF, avec suivi de progression et certificats.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="flex min-h-screen flex-col font-sans">
        <AppHydrator />
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
