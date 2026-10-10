import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["600", "700"],
});

export const metadata: Metadata = {
  title: "Cureva Care",
  description:
    "Maternal-care intelligence and reporting for ANC, Delivery, and PNC registers.",
};

// Runs synchronously during HTML parsing, before first paint, so the correct
// theme is applied with no flash (cureva-docs/09-ui-design-system.md "How the
// toggle works"; Next.js preventing-flash-before-hydration guide). An explicit
// light/dark choice lives in localStorage; absence (or "system") follows the OS.
const NO_FLASH_THEME = `(function(){try{var t=localStorage.getItem('cv-theme');if(!t||t==='system'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning className={spaceGrotesk.variable}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_THEME }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
