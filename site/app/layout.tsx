import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "jinubot",
  description: "A publishing system for recurring research and synthesized updates.",
  icons: {
    icon: "/images/jinju1.png",
    shortcut: "/images/jinju1.png",
    apple: "/images/jinju1.png"
  }
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
