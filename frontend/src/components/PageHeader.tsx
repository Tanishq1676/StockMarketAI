import type { ReactNode } from "react";

export default function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <header className="mb-6 flex animate-fade-up flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <span className="eyebrow">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
            {eyebrow}
          </span>
        )}
        <h1 className="h1 mt-2">{title}</h1>
        {description && <p className="sub mt-2 max-w-2xl">{description}</p>}
      </div>
      {children && <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">{children}</div>}
    </header>
  );
}
