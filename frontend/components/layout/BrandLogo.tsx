import Link from "next/link";

export default function BrandLogo({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
  return (
    <Link href="/" className={`inline-flex shrink-0 items-center gap-2.5 ${className}`} aria-label="KalanPro - Accueil">
      <span className="relative grid h-9 w-9 place-items-center overflow-hidden rounded-xl bg-white text-navy-950 shadow-sm ring-1 ring-white/20">
        <span className="absolute -left-1 top-0 h-5 w-2.5 rotate-45 rounded-sm bg-brand-500" aria-hidden="true" />
        <span className="relative text-[22px] font-black leading-none tracking-[-0.12em]">K</span>
      </span>
      {!compact && (
        <span className="text-xl font-black tracking-tight text-white">
          Kalan<span className="text-brand-500">Pro</span>
        </span>
      )}
    </Link>
  );
}
