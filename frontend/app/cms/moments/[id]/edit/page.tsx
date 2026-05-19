"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import MomentForm, { MomentFormData } from "@/components/MomentForm";
import { MediaData } from "@/components/MediaUpload";

interface CmsMomentPhoto {
  s3_key: string;
  cdn_url: string;
  position: number;
  media_type?: "photo" | "video";
}

interface CmsMomentDetailResponse {
  id: number;
  title: string;
  moment_date: string;
  description: string;
  status: "draft" | "published";
  published_at: string | null;
  photos: CmsMomentPhoto[];
}

export default function EditMomentPage() {
  const router = useRouter();
  const params = useParams();
  const momentId = params.id as string;

  const [token, setToken] = useState<string | null>(null);
  const [momentData, setMomentData] = useState<CmsMomentDetailResponse | null>(null);
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

    async function loadMoment() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const res = await fetch(`${apiUrl}/api/cms/moments/${momentId}`, {
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
          setGeneralError("Failed to load moment.");
          setIsLoading(false);
          return;
        }

        const data: CmsMomentDetailResponse = await res.json();
        setMomentData(data);
      } catch {
        setGeneralError("Unable to connect to the server. Please try again.");
      } finally {
        setIsLoading(false);
      }
    }

    loadMoment();
  }, [token, momentId, router]);

  async function handleSubmit(data: MomentFormData) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    const res = await fetch(`${apiUrl}/api/cms/moments/${momentId}`, {
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
      throw new Error(body?.detail || "Failed to update moment. Please try again.");
    }

    router.push("/cms/moments");
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      "Are you sure you want to delete this moment? This action cannot be undone."
    );
    if (!confirmed) return;

    setIsDeleting(true);
    setGeneralError("");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${apiUrl}/api/cms/moments/${momentId}`, {
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
        setGeneralError(body?.detail || "Failed to delete moment. Please try again.");
        return;
      }

      router.push("/cms/moments");
    } catch {
      setGeneralError("Unable to connect to the server. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  }

  if (!token || isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading moment...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-700 text-lg">Moment not found</p>
        </div>
        <div className="text-center">
          <Link
            href="/cms/moments"
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            ← Back to moments
          </Link>
        </div>
      </div>
    );
  }

  const initialData = momentData
    ? {
        title: momentData.title,
        moment_date: momentData.moment_date,
        description: momentData.description,
        status: momentData.status,
        photos: momentData.photos.map((p): MediaData => ({
          s3_key: p.s3_key,
          cdn_url: p.cdn_url,
          position: p.position,
          media_type: p.media_type || "photo",
        })),
      }
    : undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Edit Moment</h1>
        <Link
          href="/cms/moments"
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to moments
        </Link>
      </div>

      {/* General error */}
      {generalError && (
        <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{generalError}</p>
        </div>
      )}

      <MomentForm mode="edit" initialData={initialData} onSubmit={handleSubmit} />

      {/* Delete section */}
      <div className="pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-red-700">Danger Zone</h2>
            <p className="text-sm text-gray-500">
              Permanently delete this moment and all its photos.
            </p>
          </div>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? "Deleting..." : "Delete Moment"}
          </button>
        </div>
      </div>
    </div>
  );
}
