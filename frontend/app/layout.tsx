import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NIRNAY — Verify before you trust",
  description: "Check financial content against evidence before acting on it.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
