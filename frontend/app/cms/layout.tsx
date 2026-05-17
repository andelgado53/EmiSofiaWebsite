"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

export default function CmsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  
  // Initialize auth state from localStorage immediately (synchronous check)
  const [isAuthed, setIsAuthed] = useState(() => {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("token");
  });

  // The login page is at /cms exactly — don't guard it
  const isLoginPage = pathname === "/cms";

  useEffect(() => {
    if (isLoginPage) {
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      setIsAuthed(false);
      router.replace("/cms");
    } else {
      setIsAuthed(true);
    }
  }, [isLoginPage, pathname, router]);

  function handleLogout() {
    localStorage.removeItem("token");
    setIsAuthed(false);
    router.replace("/cms");
  }

  // Login page renders without the CMS header
  if (isLoginPage) {
    return <>{children}</>;
  }

  // Show nothing while checking auth (prevents flash of protected content)
  if (!isAuthed) {
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
