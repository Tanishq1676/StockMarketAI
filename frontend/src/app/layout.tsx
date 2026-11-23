import type { Metadata } from "next";
import Header from "@/components/Header";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "IndStock Intelligence — Indian Market Research",
  description:
    "AI-powered research assistant for NSE and BSE listed equities: historical analysis, forecasts, BUY/SELL signals and paper trading.",
  keywords: [
    "indian stock market",
    "NSE",
    "BSE",
    "AI stock analysis",
    "paper trading",
    "NIFTY 50",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Loaded at runtime so the production build never depends on network access.
            Falls back to the system UI stack when the font host is unreachable. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
        />
      </head>
      <body className="font-sans antialiased">
        <Header />
        <div className="relative z-10 min-h-screen lg:pl-[272px]">{children}</div>
      </body>
    </html>
  );
}
