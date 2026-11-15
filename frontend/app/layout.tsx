import type { Metadata } from "next";
import "./globals.css";
import { AppLayout } from "@/components/layout/AppLayout";

export const metadata: Metadata = {
  title: "OpsPulse — Retail & Distribution Operations Intelligence",
  description:
    "Enterprise Retail and Distribution Data Engineering and Business Operations Intelligence Platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased font-sans">
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  );
}
