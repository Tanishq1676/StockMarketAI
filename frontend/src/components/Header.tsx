"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type IconName =
  | "dashboard"
  | "stocks"
  | "portfolio"
  | "paper"
  | "alerts"
  | "news"
  | "reports"
  | "menu"
  | "close"
  | "spark";

function Icon({ name, className = "h-[18px] w-[18px]" }: { name: IconName; className?: string }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (name) {
    case "dashboard":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <rect x="3" y="3" width="7" height="7" rx="1.6" />
          <rect x="14" y="3" width="7" height="7" rx="1.6" />
          <rect x="3" y="14" width="7" height="7" rx="1.6" />
          <rect x="14" y="14" width="7" height="7" rx="1.6" />
        </svg>
      );
    case "stocks":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M3 17l5-5 4 3 6-8" />
          <path d="M15 7h3v3" />
          <path d="M3 21h18" />
        </svg>
      );
    case "portfolio":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <rect x="3" y="7" width="18" height="13" rx="2.4" />
          <path d="M9 7V5.5A1.5 1.5 0 0110.5 4h3A1.5 1.5 0 0115 5.5V7" />
          <path d="M3 12.5h18" />
        </svg>
      );
    case "paper":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M4 6.5h16" />
          <path d="M4 12h16" />
          <path d="M4 17.5h9" />
          <circle cx="17.5" cy="17.5" r="3.5" />
        </svg>
      );
    case "alerts":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M18 15.5V11a6 6 0 10-12 0v4.5L4.5 18h15L18 15.5z" />
          <path d="M9.5 21a2.6 2.6 0 005 0" />
        </svg>
      );
    case "news":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M4 5.5A1.5 1.5 0 015.5 4H17a1.5 1.5 0 011.5 1.5V18a2 2 0 002 2H6a2 2 0 01-2-2V5.5z" />
          <path d="M8 8h6.5M8 11.5h6.5M8 15h4" />
        </svg>
      );
    case "reports":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M7 3.5h7l4 4V19a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 016 19V5A1.5 1.5 0 017.5 3.5z" />
          <path d="M14 3.5V8h4" />
          <path d="M9.5 13h5M9.5 16h3.5" />
        </svg>
      );
    case "menu":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      );
    case "close":
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 24 24" className={className} {...common}>
          <path d="M3 17l5-5 4 3 6-8" />
          <path d="M15 7h3v3" />
        </svg>
      );
  }
}

const NAV_GROUPS: { label: string; items: { href: string; label: string; icon: IconName }[] }[] = [
  {
    label: "Overview",
    items: [{ href: "/", label: "Dashboard", icon: "dashboard" }],
  },
  {
    label: "Markets",
    items: [
      { href: "/stocks", label: "All Stocks", icon: "stocks" },
      { href: "/news", label: "Market News", icon: "news" },
      { href: "/reports", label: "AI Reports", icon: "reports" },
    ],
  },
  {
    label: "Trading",
    items: [
      { href: "/portfolio", label: "Portfolio", icon: "portfolio" },
      { href: "/paper-trading", label: "Paper Trading", icon: "paper" },
      { href: "/alerts", label: "Alerts", icon: "alerts" },
    ],
  },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-cta shadow-emerald">
        <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <path d="M7 4v16M12 7v10M17 3v18" />
        </svg>
      </span>
      <span className="leading-none">
        <span className="block text-[15px] font-extrabold tracking-tight text-ink">IndStock</span>
        <span className="mt-1 block text-[9.5px] font-bold uppercase tracking-[0.24em] text-accent">
          Intelligence
        </span>
      </span>
      {compact ? null : <span className="sr-only">Home</span>}
    </Link>
  );
}

function NavContent({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-4 py-5">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-2 px-2 text-[10px] font-bold uppercase tracking-[0.2em] text-fg-dim">
            {group.label}
          </p>
          <ul className="space-y-1">
            {group.items.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={`group relative flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-semibold transition-all duration-200 ${
                      active
                        ? "bg-accent-soft text-accent-dark shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]"
                        : "text-fg-muted hover:bg-white/70 hover:text-ink"
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-accent" />
                    )}
                    <span
                      className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-colors ${
                        active
                          ? "border-accent/20 bg-white text-accent"
                          : "border-line/70 bg-white/60 text-fg-muted group-hover:border-accent/20 group-hover:text-accent"
                      }`}
                    >
                      <Icon name={item.icon} />
                    </span>
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      <div className="mt-auto space-y-3 pt-2">
        <div className="rounded-2xl border border-line/80 bg-white/65 p-3.5">
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-accent-dark">
            <span className="live-dot" />
            Market feed
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-fg-muted">
            NSE &amp; BSE research data, refreshed every 60 seconds.
          </p>
          <div className="mt-3 flex items-center justify-between border-t border-line/70 pt-2.5">
            <span className="text-[11px] text-fg-dim">Engine</span>
            <span className="pill pill-accent">AI research</span>
          </div>
        </div>
        <p className="px-1 text-[10px] leading-relaxed text-fg-dim">
          Educational research tool. Not investment advice. Forecasts carry uncertainty.
        </p>
      </div>
    </nav>
  );
}

export default function Header() {
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[272px] flex-col border-r border-line/80 glass lg:flex">
        <div className="flex h-[76px] items-center border-b border-line/70 px-5">
          <Brand />
        </div>
        <NavContent pathname={pathname} />
      </aside>

      {/* Mobile top bar */}
      <div className="sticky top-0 z-40 border-b border-line/80 glass lg:hidden">
        <div className="flex h-16 items-center justify-between px-4">
          <Brand compact />
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-accent-dark sm:flex">
              <span className="live-dot" /> Feed
            </span>
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-label="Open navigation menu"
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-white/70 text-fg-muted transition hover:border-accent/30 hover:text-accent"
            >
              <Icon name="menu" className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <button
            type="button"
            aria-label="Close navigation menu"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-ink/30 backdrop-blur-sm"
          />
          <div className="absolute inset-y-0 left-0 flex w-[288px] max-w-[85vw] animate-slide-in flex-col border-r border-line bg-white/95 shadow-2xl backdrop-blur-xl">
            <div className="flex h-16 items-center justify-between border-b border-line/70 px-4">
              <Brand />
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close navigation menu"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-fg-muted transition hover:text-ink"
              >
                <Icon name="close" className="h-4 w-4" />
              </button>
            </div>
            <NavContent pathname={pathname} onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
