import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NIRNAY",
  description: "A foundation for financial content verification and literacy.",
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
