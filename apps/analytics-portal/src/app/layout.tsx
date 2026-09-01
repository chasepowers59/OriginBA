import { Inter } from "next/font/google";
import type { Metadata } from "next";
import { AuthProvider } from "@/components/AuthProvider";
import { PortalThemeProvider } from "@/components/PortalThemeProvider";
import { DEFAULT_BRAND, brandLine } from "@/lib/brand";
import "./globals.css";

// Inter is the bundled FALLBACK; the body stack prefers locally-installed Aptos
// (Origin's brand face, shipped with M365) — see globals.css and brandFont.test.ts.
const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });

export const metadata: Metadata = {
  title: brandLine(DEFAULT_BRAND),
  description: DEFAULT_BRAND.tagline,
  icons: {
    icon: DEFAULT_BRAND.logo_src ?? "/brand-icon.svg",
    apple: DEFAULT_BRAND.logo_src ?? "/brand-icon.svg",
  },
};

const colorModeScript = `
(function () {
  try {
    var stored = localStorage.getItem('portal-color-mode');
    var dark = stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', dark);
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: colorModeScript }} />
      </head>
      <body className={`${inter.variable} antialiased`}>
        <AuthProvider>
          <PortalThemeProvider>{children}</PortalThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
