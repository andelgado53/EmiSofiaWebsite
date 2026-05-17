"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import NoteEditor from "../../../../components/NoteEditor";
import PhotoUpload from "../../../../components/PhotoUpload";
import LabelInput from "../../../../components/LabelInput";

interface PhotoData {
  s3_key: string;
  cdn_url: string;
  position: number;
}

const MAX_TITLE_LENGTH = 100;
const MAX_BODY_LENGTH = 50_000;

export default function NewNotePage() {
  const router = useRouter();
  const editorRef = useRef<any>(null);

  const [title, setTitle] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [labels, setLabels] = useState<string[]>([]);
  const [photos, setPhotos] = useState<PhotoData[]>([]);

  const [titleError, setTitleError] = useState("");
  const [bodyError, setBodyError] = useState("");
  const [generalError, setGeneralError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  function handleInsertPhoto(cdnUrl: string, float: "left" | "right") {
    // Insert the photo into the editor at the current cursor position
    if (editorRef.current) {
      editorRef.current.chain().focus().setImage({ src: cdnUrl, float }).run();
    }
  }

  function validate(status: "draft" | "published"): boolean {
    let valid = true;
    setTitleError("");
    setBodyError("");
    setGeneralError("");

    if (status === "published" && !title.trim()) {
      setTitleError("Title is required to publish a note.");
      valid = false;
    }

    if (bodyHtml.length > MAX_BODY_LENGTH) {
      setBodyError(
        `Body exceeds the maximum of ${MAX_BODY_LENGTH.toLocaleString()} characters (currently ${bodyHtml.length.toLocaleString()}).`
      );
      valid = false;
    }

    return valid;
  }

  async function handleSave(status: "draft" | "published") {
    if (!validate(status)) return;

    setIsSaving(true);
    setGeneralError("");

    try {
      const token = localStorage.getItem("token");
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;

      const res = await fetch(`${apiUrl}/api/cms/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: title.trim(),
          body_html: bodyHtml,
          status,
          labels,
          photos,
        }),
      });

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setGeneralError(data?.detail || "Failed to save note. Please try again.");
        return;
      }

      // On publish, trigger ISR revalidation via the Next.js revalidation endpoint
      if (status === "published") {
        try {
          await fetch("/api/revalidate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ secret: process.env.NEXT_PUBLIC_REVALIDATE_SECRET }),
          });
        } catch {
          // Revalidation failure is non-blocking; the note was saved successfully
        }
      }

      router.push("/cms/notes");
    } catch {
      setGeneralError("Unable to connect to the server. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">New Note</h1>
        <Link
          href="/cms/notes"
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to notes
        </Link>
      </div>

      {/* General error */}
      {generalError && (
        <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{generalError}</p>
        </div>
      )}

      {/* Title */}
      <div>
        <label htmlFor="note-title" className="block text-sm font-medium text-gray-700 mb-1">
          Title
        </label>
        <input
          id="note-title"
          type="text"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setTitleError("");
          }}
          maxLength={MAX_TITLE_LENGTH}
          placeholder="Enter note title..."
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            titleError ? "border-red-500" : "border-gray-300"
          }`}
        />
        <div className="flex justify-between mt-1">
          {titleError ? (
            <p role="alert" className="text-sm text-red-600">{titleError}</p>
          ) : (
            <span />
          )}
          <span className="text-xs text-gray-500">
            {title.length}/{MAX_TITLE_LENGTH}
          </span>
        </div>
      </div>

      {/* Body (Tiptap editor) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Body
        </label>
        <NoteEditor content={bodyHtml} onChange={setBodyHtml} onEditorReady={(editor) => { editorRef.current = editor; }} />
        <div className="flex justify-between mt-1">
          {bodyError ? (
            <p role="alert" className="text-sm text-red-600">{bodyError}</p>
          ) : (
            <span />
          )}
          <span
            className={`text-xs ${
              bodyHtml.length > MAX_BODY_LENGTH ? "text-red-600 font-medium" : "text-gray-500"
            }`}
          >
            {bodyHtml.length.toLocaleString()}/{MAX_BODY_LENGTH.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Photos */}
      <PhotoUpload photos={photos} onPhotosChange={setPhotos} onInsertPhoto={handleInsertPhoto} />

      {/* Labels */}
      <LabelInput labels={labels} onLabelsChange={setLabels} />

      {/* Action buttons */}
      <div className="flex gap-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={() => handleSave("draft")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Saving..." : "Save as Draft"}
        </button>
        <button
          type="button"
          onClick={() => handleSave("published")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Publishing..." : "Publish"}
        </button>
      </div>
    </div>
  );
}
