"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface TripPhoto {
  cdn_url: string;
  position: number;
}

interface CmsTripDetail {
  id: number;
  title: string;
  trip_date: string;
  description: string | null;
  status: string;
  published_at: string | null;
  photos: TripPhoto[];
}

export default function CmsTripsPage() {
  const router = useRouter();
  const [trips, setTrips] = useState<CmsTripDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTrips();
  }, []);

  async function fetchTrips() {
    setIsLoading(true);
    setError("");

    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/cms");
      return;
    }

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/trips`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        setError("Failed to load trips");
        return;
      }

      const data = await res.json();
      setTrips(data);
    } catch {
      setError("Unable to connect to the server");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDelete(tripId: number) {
    if (!confirm("Are you sure you want to delete this trip? All photos will be permanently removed.")) return;

    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/cms");
      return;
    }

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/trips/${tripId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        setError("Failed to delete trip");
        return;
      }

      // Refresh the list
      fetchTrips();
    } catch {
      setError("Unable to connect to the server");
    }
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading trips...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Trips</h1>
        <Link
          href="/cms/trips/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          New Trip
        </Link>
      </div>

      {error && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {error}
        </p>
      )}

      {trips.length === 0 ? (
        <p className="text-gray-500 py-8 text-center">
          No trips yet. Create your first trip!
        </p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Trip Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {trips.map((trip) => (
                <tr key={trip.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {trip.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        trip.status === "published"
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {trip.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(trip.trip_date)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                    <Link
                      href={`/cms/trips/${trip.id}/edit`}
                      className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      Edit
                    </Link>
                    <button
                      onClick={() => handleDelete(trip.id)}
                      className="inline-flex items-center px-3 py-1 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
