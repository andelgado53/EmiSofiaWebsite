"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

export default function CmsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthed, setIsAuthed] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // The login page is at /cms exactly — don't guard it
  const isLoginPage = pathname === "/cms";

  useEffect(() => {
    // Check auth on mount and whenever we return to a non-login page
    if (isLoginPage) {
      setIsChecking(false);
      return;
    }

    const token = localStorage.getItem("token");
    if (token) {
      setIsAuthed(true);
    } else {
      setIsAuthed(false);
      router.replace("/cms");
    }
    setIsChecking(false);
  }, [isLoginPage, router]);

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
  if (isChecking || !isAuthed) {
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
