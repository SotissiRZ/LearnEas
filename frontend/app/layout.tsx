import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import AppHydrator from "@/components/layout/AppHydrator";
import LazyKalanProAssistant from "@/components/ai/LazyKalanProAssistant";
import NavigationPerformance from "@/components/layout/NavigationPerformance";
import NetworkStatus from "@/components/layout/NetworkStatus";
import ServiceWorkerRegistration from "@/components/layout/ServiceWorkerRegistration";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "KalanPro · Apprendre, progresser, travailler",
  description: "KalanPro réunit formations, mentorat, projets, certificats et opportunités professionnelles pour l'Afrique francophone.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="flex min-h-screen flex-col font-sans">
        <AppHydrator />
        <ServiceWorkerRegistration />
        <NavigationPerformance />
        <NetworkStatus />
        <Navbar />
        <div className="h-20 shrink-0" aria-hidden="true" />
        <main className="flex-1">{children}</main>
        <Footer />
        <LazyKalanProAssistant />
      </body>
    </html>
  );
}
