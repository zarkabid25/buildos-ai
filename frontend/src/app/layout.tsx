import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BuildOS AI",
  description: "AI-Native Construction ERP & Inventory Management",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
