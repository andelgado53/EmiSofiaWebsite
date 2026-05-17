import { notFound } from "next/navigation";

interface Label {
  name: string;
}

interface Photo {
  cdn_url: string;
  position: number;
}

interface NoteDetail {
  id: number;
  title: string;
  body_html: string;
  published_at: string;
  labels: Label[];
  photos: Photo[];
}

export const revalidate = 60;

async function getNote(id: string): Promise<NoteDetail | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/notes/${id}`, {
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
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function NoteDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const note = await getNote(params.id);

  if (!note) {
    notFound();
  }

  return (
    <article className="max-w-3xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{note.title}</h1>
        <time
          className="mt-2 block text-sm text-gray-500"
          dateTime={note.published_at}
        >
          {formatDate(note.published_at)}
        </time>
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
      </header>

      <div
        className="note-body prose prose-gray max-w-none"
        dangerouslySetInnerHTML={{ __html: note.body_html }}
      />
    </article>
  );
}
