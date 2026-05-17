"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export default function CmsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthed, setIsAuthed] = useState(false);

  // The login page is at /cms exactly — don't guard it
  const isLoginPage = pathname === "/cms";

  useEffect(() => {
    if (isLoginPage) {
      setIsAuthed(true);
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/cms");
    } else {
      setIsAuthed(true);
    }
  }, [isLoginPage, router]);

  function handleLogout() {
    localStorage.removeItem("token");
    router.replace("/cms");
  }

  // Show nothing while checking auth (prevents flash of protected content)
  if (!isAuthed) {
    return null;
  }

  // Login page renders without the CMS header
  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <nav className="flex items-center gap-4">
          <span className="text-lg font-semibold text-gray-800">CMS</span>
          <a
            href="/cms/notes"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Notes
          </a>
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
