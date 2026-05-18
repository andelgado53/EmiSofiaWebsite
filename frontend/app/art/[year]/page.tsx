import Link from "next/link";
import ArtYearGallery from "./ArtYearGallery";

interface ArtPiece {
  id: number;
  cdn_url: string;
  title: string | null;
  position: number;
}

export const revalidate = 60;

async function getArtPieces(year: string): Promise<ArtPiece[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/art/years/${year}`, {
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    return [];
  }

  return res.json();
}

export default async function ArtYearGalleryPage({
  params,
}: {
  params: { year: string };
}) {
  const pieces = await getArtPieces(params.year);
  const sortedPieces = [...pieces].sort((a, b) => a.position - b.position);

  return (
    <div>
      <div className="mb-6 flex items-center gap-4">
        <Link
          href="/art"
          className="text-sm text-violet-700 hover:text-violet-900 font-medium"
        >
          ← All Years
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">{params.year}</h1>
      </div>

      {sortedPieces.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg">
            No art available for this year.
          </p>
          <Link
            href="/art"
            className="mt-4 inline-block text-violet-700 hover:text-violet-900 font-medium"
          >
            ← Back to year list
          </Link>
        </div>
      ) : (
        <ArtYearGallery pieces={sortedPieces} />
      )}
    </div>
  );
}
