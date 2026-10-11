import type { Metadata, Viewport } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import "./globals.css";

// next/font self-hosts these files at build time; browsers make no third-party font requests.
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-source-serif",
});

export const metadata: Metadata = {
  title: "NIRNAY — Check financial claims against evidence",
  description:
    "Paste a financial message or claim. NIRNAY separates its claims, retrieves sources, and shows what the evidence can and cannot establish.",
};

export const viewport: Viewport = {
  themeColor: "#faf6ee",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html className={`${inter.variable} ${sourceSerif.variable}`} lang="en-IN">
      <body>
        <a className="skip-link" href="#main">
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
