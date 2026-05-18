import Link from "next/link";

interface YearSummary {
  year: number;
  cover_photo_url: string | null;
  count: number;
}

export const revalidate = 60;

async function getArtYears(): Promise<YearSummary[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/art/years`, {
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    return [];
  }

  return res.json();
}

export default async function ArtYearsPage() {
  const years = await getArtYears();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Emi&apos;s Art</h1>
      </div>

      {years.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg">
            No art available yet — check back soon.
          </p>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2">
          {years.map((yearItem) => (
            <Link
              key={yearItem.year}
              href={`/art/${yearItem.year}`}
              className="block rounded-lg border border-violet-200 bg-violet-50/40 overflow-hidden hover:border-violet-300 hover:shadow-sm transition-all"
            >
              <div className="aspect-[4/3] relative bg-gray-100">
                {yearItem.cover_photo_url ? (
                  <img
                    src={yearItem.cover_photo_url}
                    alt={`Art from ${yearItem.year}`}
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
                  {yearItem.year}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {yearItem.count} {yearItem.count === 1 ? "piece" : "pieces"}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
