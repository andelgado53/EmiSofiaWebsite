"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

export default function CmsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // The login page is at /cms exactly — don't guard it
  const isLoginPage = pathname === "/cms";

  // Read token synchronously on every render to avoid stale state
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || isLoginPage) return;

    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/cms");
    }
  }, [mounted, isLoginPage, pathname, router]);

  function handleLogout() {
    localStorage.removeItem("token");
    router.replace("/cms");
  }

  // Login page renders without the CMS header
  if (isLoginPage) {
    return <>{children}</>;
  }

  // Don't render until mounted (avoids SSR hydration mismatch)
  if (!mounted) {
    return null;
  }

  // Check token on every render (synchronous read)
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (!token) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <nav className="flex items-center gap-4">
          <span className="text-lg font-semibold text-gray-800">CMS</span>
          <Link
            href="/cms/notes"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Notes
          </Link>
          <Link
            href="/cms/trips"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Trips
          </Link>
          <Link
            href="/cms/art"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Art
          </Link>
        </nav>
        <button
          onClick={handleLogout}
          className="text-sm text-red-600 hover:text-red-800 font-medium"
        >
          Logout
        </button>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-8">{children}</main>
    </div>
  );
}
