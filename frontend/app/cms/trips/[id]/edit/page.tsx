"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import TripForm, { TripFormData, TripPhotoData } from "@/components/TripForm";

interface CmsTripPhoto {
  s3_key: string;
  cdn_url: string;
  position: number;
}

interface CmsTripDetailResponse {
  id: number;
  title: string;
  trip_date: string;
  description: string | null;
  status: "draft" | "published";
  published_at: string | null;
  photos: CmsTripPhoto[];
}

export default function EditTripPage() {
  const router = useRouter();
  const params = useParams();
  const tripId = params.id as string;

  const [token, setToken] = useState<string | null>(null);
  const [tripData, setTripData] = useState<CmsTripDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [generalError, setGeneralError] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      router.replace("/cms");
      return;
    }
    setToken(stored);
  }, [router]);

  useEffect(() => {
    if (!token) return;

    async function loadTrip() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const res = await fetch(`${apiUrl}/api/cms/trips/${tripId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.status === 401) {
          localStorage.removeItem("token");
          router.replace("/cms");
          return;
        }

        if (res.status === 404) {
          setNotFound(true);
          setIsLoading(false);
          return;
        }

        if (!res.ok) {
          setGeneralError("Failed to load trip.");
          setIsLoading(false);
          return;
        }

        const data: CmsTripDetailResponse = await res.json();
        setTripData(data);
      } catch {
        setGeneralError("Unable to connect to the server. Please try again.");
      } finally {
        setIsLoading(false);
      }
    }

    loadTrip();
  }, [token, tripId, router]);

  async function handleSubmit(data: TripFormData) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    const res = await fetch(`${apiUrl}/api/cms/trips/${tripId}`, {
      method: "PUT",
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
      throw new Error(body?.detail || "Failed to update trip. Please try again.");
    }

    router.push("/cms/trips");
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      "Are you sure you want to delete this trip? This action cannot be undone."
    );
    if (!confirmed) return;

    setIsDeleting(true);
    setGeneralError("");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${apiUrl}/api/cms/trips/${tripId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setGeneralError(body?.detail || "Failed to delete trip. Please try again.");
        return;
      }

      router.push("/cms/trips");
    } catch {
      setGeneralError("Unable to connect to the server. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  }

  if (!token || isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading trip...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-700 text-lg">Trip not found</p>
        </div>
        <div className="text-center">
          <Link
            href="/cms/trips"
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            ← Back to trips
          </Link>
        </div>
      </div>
    );
  }

  const initialData = tripData
    ? {
        title: tripData.title,
        trip_date: tripData.trip_date,
        description: tripData.description ?? "",
        status: tripData.status,
        photos: tripData.photos.map((p): TripPhotoData => ({
          s3_key: p.s3_key,
          cdn_url: p.cdn_url,
          position: p.position,
        })),
      }
    : undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Edit Trip</h1>
        <Link
          href="/cms/trips"
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to trips
        </Link>
      </div>

      {/* General error */}
      {generalError && (
        <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{generalError}</p>
        </div>
      )}

      <TripForm mode="edit" initialData={initialData} onSubmit={handleSubmit} />

      {/* Delete section */}
      <div className="pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-red-700">Danger Zone</h2>
            <p className="text-sm text-gray-500">
              Permanently delete this trip and all its photos.
            </p>
          </div>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? "Deleting..." : "Delete Trip"}
          </button>
        </div>
      </div>
    </div>
  );
}
