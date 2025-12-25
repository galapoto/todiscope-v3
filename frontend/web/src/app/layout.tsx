import type { Metadata } from "next";
import { IBM_Plex_Mono, Inter } from "next/font/google";
import "./globals.css";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import Providers from "./providers";
import { DegradedBanner } from "@/components/system/degraded-banner";

const inter = Inter({
  variable: "--font-primary",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-code",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Todiscope V3",
  description: "AI governance and reporting cockpit.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning data-theme="dark" className="overflow-x-hidden">
      <body
        className={`${inter.variable} ${plexMono.variable} min-h-screen overflow-x-hidden bg-[var(--surface-0)] text-[var(--ink-1)] antialiased`}
      >
        <Providers>
          <DegradedBanner />
          {children}
        </Providers>
      </body>
    </html>
  );
}
