interface Label {
  name: string;
}

interface NoteListItem {
  id: number;
  title: string;
  excerpt: string;
  published_at: string;
  labels: Label[];
}

interface PaginatedNotes {
  total: number;
  page: number;
  page_size: number;
  items: NoteListItem[];
}

export const revalidate = 60;

async function getNotes(): Promise<PaginatedNotes> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/notes`, { next: { revalidate: 60 } });

  if (!res.ok) {
    return { total: 0, page: 1, page_size: 20, items: [] };
  }

  return res.json();
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function NotesPage() {
  const data = await getNotes();

  if (data.items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 text-lg">
          No notes yet — check back soon.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {data.items.map((note) => (
        <a
          key={note.id}
          href={`/notes/${note.id}`}
          className="block rounded-lg border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
        >
          <h2 className="text-xl font-semibold text-gray-900">{note.title}</h2>
          <time
            className="mt-1 block text-sm text-gray-500"
            dateTime={note.published_at}
          >
            {formatDate(note.published_at)}
          </time>
          <p className="mt-3 text-gray-700 leading-relaxed">{note.excerpt}</p>
          {note.labels.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {note.labels.map((label) => (
                <span
                  key={label.name}
                  className="inline-block rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
                >
                  {label.name}
                </span>
              ))}
            </div>
          )}
        </a>
      ))}
    </div>
  );
}
