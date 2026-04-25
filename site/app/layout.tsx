import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Frontier Signals",
  description: "A publishing system for recurring research and synthesized updates."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
