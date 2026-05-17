import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Emi Sofia",
  description: "A website for Emi — notes, art, trips, and more",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-sky-50 text-gray-900">
        <nav className="border-b border-gray-200 px-6 py-4 flex items-center gap-8">
          <Link
            href="/"
            className="text-xl font-semibold text-gray-900 hover:text-gray-700"
          >
            Emi Sofia
          </Link>
          <div className="flex items-center gap-6 text-sm">
            <Link
              href="/notes"
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              Notes for Emi
            </Link>
            <span className="text-gray-300 cursor-default" title="Coming soon">
              Emi&apos;s Art
            </span>
            <span className="text-gray-300 cursor-default" title="Coming soon">
              Family Trips
            </span>
          </div>
        </nav>
        <main className="mx-auto max-w-3xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
