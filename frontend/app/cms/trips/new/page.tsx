"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import TripForm, { TripFormData } from "@/components/TripForm";

export default function NewTripPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      router.replace("/cms");
      return;
    }
    setToken(stored);
  }, [router]);

  async function handleSubmit(data: TripFormData) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    const res = await fetch(`${apiUrl}/api/cms/trips`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });

    if (res.status === 401) {
      localStorage.removeItem("token");
      router.replace("/cms");
      return;
    }

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || "Failed to create trip. Please try again.");
    }

    router.push("/cms/trips");
  }

  if (!token) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">New Trip</h1>
        <Link
          href="/cms/trips"
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to trips
        </Link>
      </div>

      <TripForm mode="create" onSubmit={handleSubmit} />
    </div>
  );
}
