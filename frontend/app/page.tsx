import Link from "next/link";

export default function HomePage() {
  return (
    <div className="py-12 text-center space-y-8">
      <h1 className="text-4xl font-bold text-gray-900">Emi Sofia</h1>
      <p className="text-lg text-gray-600 max-w-md mx-auto">
        A place for notes, art, adventures, and everything in between.
      </p>

      <div className="grid gap-4 max-w-sm mx-auto">
        <Link
          href="/notes"
          className="block p-4 rounded-lg border border-amber-200 bg-amber-50 hover:border-amber-300 hover:shadow-sm transition-all"
        >
          <h2 className="text-lg font-semibold text-gray-900">Notes for Emi</h2>
          <p className="text-sm text-gray-600 mt-1">
            Thoughts, lessons, and reflections from mom and dad
          </p>
        </Link>

        <Link
          href="/art"
          className="block p-4 rounded-lg border border-violet-200 bg-violet-50 hover:border-violet-300 hover:shadow-sm transition-all"
        >
          <h2 className="text-lg font-semibold text-gray-900">Emi&apos;s Art</h2>
          <p className="text-sm text-gray-600 mt-1">
            Drawings, paintings, and creative adventures
          </p>
        </Link>

        <Link
          href="/trips"
          className="block p-4 rounded-lg border border-emerald-200 bg-emerald-50 hover:border-emerald-300 hover:shadow-sm transition-all"
        >
          <h2 className="text-lg font-semibold text-gray-900">Family Trips</h2>
          <p className="text-sm text-gray-600 mt-1">
            Photos and memories from our family adventures
          </p>
        </Link>

        <Link
          href="/moments"
          className="block p-4 rounded-lg border border-rose-200 bg-rose-50 hover:border-rose-300 hover:shadow-sm transition-all"
        >
          <h2 className="text-lg font-semibold text-gray-900">Emi&apos;s Big Moments</h2>
          <p className="text-sm text-gray-600 mt-1">
            Milestones, firsts, and unforgettable memories
          </p>
        </Link>
      </div>
    </div>
  );
}
