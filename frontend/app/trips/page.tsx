interface TripListItem {
  id: number;
  title: string;
  trip_date: string;
  cover_photo_url: string | null;
}

interface PaginatedTrips {
  total: number;
  page: number;
  page_size: number;
  items: TripListItem[];
}

export const revalidate = 60;

async function getTrips(): Promise<PaginatedTrips> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/trips`, { next: { revalidate: 60 } });

  if (!res.ok) {
    return { total: 0, page: 1, page_size: 20, items: [] };
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

export default async function TripsPage() {
  const data = await getTrips();

  if (data.items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 text-lg">
          No trips available yet — check back soon.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      {data.items.map((trip) => (
        <a
          key={trip.id}
          href={`/trips/${trip.id}`}
          className="block rounded-lg border border-emerald-200 bg-emerald-50/40 overflow-hidden hover:border-emerald-300 hover:shadow-sm transition-all"
        >
          <div className="aspect-[4/3] relative bg-gray-100">
            {trip.cover_photo_url ? (
              <img
                src={trip.cover_photo_url}
                alt={trip.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <svg
                  className="w-12 h-12 text-gray-300"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                  />
                </svg>
              </div>
            )}
          </div>
          <div className="p-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {trip.title}
            </h2>
            <time
              className="mt-1 block text-sm text-gray-500"
              dateTime={trip.trip_date}
            >
              {formatDate(trip.trip_date)}
            </time>
          </div>
        </a>
      ))}
    </div>
  );
}
