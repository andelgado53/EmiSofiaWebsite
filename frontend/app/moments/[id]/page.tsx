import { notFound } from "next/navigation";

interface MomentPhoto {
  cdn_url: string;
  position: number;
}

interface MomentDetail {
  id: number;
  title: string;
  moment_date: string;
  description: string;
  photos: MomentPhoto[];
}

export const revalidate = 60;

async function getMoment(id: string): Promise<MomentDetail | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/moments/${id}`, {
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

export default async function MomentDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const moment = await getMoment(params.id);

  if (!moment) {
    notFound();
  }

  const sortedPhotos = [...moment.photos].sort(
    (a, b) => a.position - b.position
  );

  return (
    <article className="max-w-4xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{moment.title}</h1>
        <time
          className="mt-2 block text-sm text-gray-500"
          dateTime={moment.moment_date}
        >
          {formatDate(moment.moment_date)}
        </time>
      </header>

      <div className="mb-8 text-gray-700 leading-relaxed">
        {moment.description.split("\n").map((paragraph, index) => (
          <p key={index} className={index > 0 ? "mt-4" : ""}>
            {paragraph}
          </p>
        ))}
      </div>

      {sortedPhotos.length > 0 && (
        <div className="space-y-6">
          {sortedPhotos.map((photo, index) => (
            <img
              key={photo.cdn_url}
              src={photo.cdn_url}
              alt={`${moment.title} photo ${index + 1}`}
              className="w-full h-auto rounded-md"
            />
          ))}
        </div>
      )}
    </article>
  );
}
