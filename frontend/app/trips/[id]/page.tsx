import { notFound } from "next/navigation";
import PhotoGallery from "@/components/PhotoGallery";

interface TripPhoto {
  cdn_url: string;
  position: number;
}

interface TripDetail {
  id: number;
  title: string;
  trip_date: string;
  description: string | null;
  photos: TripPhoto[];
}

export const revalidate = 60;

async function getTrip(id: string): Promise<TripDetail | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/trips/${id}`, {
    next: { revalidate: 60 },
  });

  if (res.status === 404) {
    return null;
  }

  if (!res.ok) {
    return null;
  }

  return res.json();
}

function formatDate(dateString: string): string {
  const date = new Date(dateString + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function TripDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const trip = await getTrip(params.id);

  if (!trip) {
    notFound();
  }

  return (
    <article className="max-w-4xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{trip.title}</h1>
        <time
          className="mt-2 block text-sm text-gray-500"
          dateTime={trip.trip_date}
        >
          {formatDate(trip.trip_date)}
        </time>
      </header>

      {trip.description && (
        <div className="mb-8 text-gray-700 leading-relaxed">
          {trip.description.split("\n").map((paragraph, index) => (
            <p key={index} className={index > 0 ? "mt-4" : ""}>
              {paragraph}
            </p>
          ))}
        </div>
      )}

      {trip.photos.length > 0 && <PhotoGallery photos={trip.photos} />}
    </article>
  );
}
