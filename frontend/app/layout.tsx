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
        <nav className="bg-white/80 backdrop-blur-sm border-b border-sky-100 px-6 py-4 flex items-center gap-8 sticky top-0 z-40 shadow-sm">
          <Link
            href="/"
            className="text-xl font-bold bg-gradient-to-r from-sky-600 to-indigo-500 bg-clip-text text-transparent hover:from-sky-500 hover:to-indigo-400 transition-all"
          >
            🎵 Emi Sofia
          </Link>
          <div className="flex items-center gap-5 text-sm">
            <Link
              href="/notes"
              className="text-amber-700 hover:text-amber-900 font-medium px-2.5 py-1 rounded-full hover:bg-amber-50 transition-colors"
            >
              Notes for Emi
            </Link>
            <span className="text-gray-300 cursor-default px-2.5 py-1" title="Coming soon">
              Emi&apos;s Art
            </span>
            <Link
              href="/trips"
              className="text-emerald-700 hover:text-emerald-900 font-medium px-2.5 py-1 rounded-full hover:bg-emerald-50 transition-colors"
            >
              Family Trips
            </Link>
          </div>
        </nav>
        <main className="mx-auto max-w-3xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
