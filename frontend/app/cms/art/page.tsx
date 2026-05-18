"use client";

import { useEffect, useState, useRef, ChangeEvent, DragEvent } from "react";
import { useRouter } from "next/navigation";

interface CmsArtPiece {
  id: number;
  year: number;
  s3_key: string;
  cdn_url: string;
  title: string | null;
  position: number;
  status: string;
}

interface CmsYearGroup {
  year: number;
  pieces: CmsArtPiece[];
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png"];
const MAX_TITLE_LENGTH = 200;

function getCurrentYear(): number {
  return new Date().getFullYear();
}

function getValidYearRange(): { min: number; max: number } {
  return { min: 2020, max: getCurrentYear() };
}

export default function CmsArtPage() {
  const router = useRouter();
  const [yearGroups, setYearGroups] = useState<CmsYearGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // New piece form state
  const [newYear, setNewYear] = useState<number>(getCurrentYear());
  const [yearError, setYearError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Drag and drop state
  const [dragInfo, setDragInfo] = useState<{ year: number; index: number } | null>(null);
  const [dragOverInfo, setDragOverInfo] = useState<{ year: number; index: number } | null>(null);

  // Inline title editing state
  const [editingTitle, setEditingTitle] = useState<{ id: number; value: string } | null>(null);
  const [titleError, setTitleError] = useState("");

  // Delete confirmation state
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  useEffect(() => {
    fetchArt();
  }, []);

  function getToken(): string | null {
    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/cms");
      return null;
    }
    return token;
  }

  async function fetchArt() {
    setIsLoading(true);
    setError("");

    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/art`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        setError("Failed to load art pieces");
        return;
      }

      const data: CmsYearGroup[] = await res.json();
      setYearGroups(data);
    } catch {
      setError("Unable to connect to the server");
    } finally {
      setIsLoading(false);
    }
  }

  // --- Upload ---

  function validateFile(file: File): string | null {
    let valid = ALLOWED_TYPES.includes(file.type);
    if (!valid && file.name) {
      const ext = file.name.toLowerCase().split(".").pop() || "";
      valid = ["jpg", "jpeg", "png"].includes(ext);
    }
    if (!valid) return "Only JPEG and PNG files are accepted.";
    if (file.size > MAX_FILE_SIZE) return "File size must be 10 MB or less.";
    return null;
  }

  function validateYear(year: number): string {
    const { min, max } = getValidYearRange();
    if (!Number.isInteger(year) || year < min || year > max) {
      return `Year must be between ${min} and ${max}.`;
    }
    return "";
  }

  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const file = fileList[0];
    if (fileInputRef.current) fileInputRef.current.value = "";

    // Validate year
    const yErr = validateYear(newYear);
    if (yErr) {
      setYearError(yErr);
      return;
    }
    setYearError("");

    // Validate file
    const fErr = validateFile(file);
    if (fErr) {
      setUploadError(fErr);
      return;
    }
    setUploadError("");

    const token = getToken();
    if (!token) return;

    setUploading(true);
    setUploadError("");

    try {
      // Step 1: Get presigned URL
      const presignRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/photos/presign`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            filename: file.name,
            content_type: file.type || "image/jpeg",
          }),
        }
      );

      if (presignRes.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!presignRes.ok) {
        const data = await presignRes.json().catch(() => null);
        throw new Error(data?.detail || "Failed to get upload URL");
      }

      const { upload_url, s3_key, cdn_url } = await presignRes.json();

      // Step 2: Upload to S3
      const uploadRes = await fetch(upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "image/jpeg" },
        body: file,
      });

      if (!uploadRes.ok) {
        throw new Error("Failed to upload to storage");
      }

      // Step 3: Create art piece record
      const createRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/art`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            year: newYear,
            s3_key,
            cdn_url,
          }),
        }
      );

      if (createRes.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!createRes.ok) {
        const data = await createRes.json().catch(() => null);
        throw new Error(data?.detail || "Failed to create art piece");
      }

      // Refresh the list
      await fetchArt();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  }

  // --- Title editing ---

  function startEditTitle(piece: CmsArtPiece) {
    setEditingTitle({ id: piece.id, value: piece.title || "" });
    setTitleError("");
  }

  async function saveTitle() {
    if (!editingTitle) return;

    if (editingTitle.value.length > MAX_TITLE_LENGTH) {
      setTitleError(`Title must be ${MAX_TITLE_LENGTH} characters or less.`);
      return;
    }
    setTitleError("");

    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/art/${editingTitle.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ title: editingTitle.value || null }),
        }
      );

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || "Failed to update title");
        return;
      }

      setEditingTitle(null);
      await fetchArt();
    } catch {
      setError("Unable to connect to the server");
    }
  }

  function cancelEditTitle() {
    setEditingTitle(null);
    setTitleError("");
  }

  // --- Publish/Unpublish ---

  async function toggleStatus(piece: CmsArtPiece) {
    const token = getToken();
    if (!token) return;

    const newStatus = piece.status === "published" ? "draft" : "published";

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/art/${piece.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ status: newStatus }),
        }
      );

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || "Failed to update status");
        return;
      }

      await fetchArt();
    } catch {
      setError("Unable to connect to the server");
    }
  }

  // --- Delete ---

  async function handleDelete(pieceId: number) {
    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/art/${pieceId}`,
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
        setError("Failed to delete art piece");
        return;
      }

      setConfirmDelete(null);
      await fetchArt();
    } catch {
      setError("Unable to connect to the server");
    }
  }

  // --- Drag and drop reorder ---

  function handleDragStart(e: DragEvent<HTMLDivElement>, year: number, index: number) {
    setDragInfo({ year, index });
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>, year: number, index: number) {
    e.preventDefault();
    if (dragInfo && dragInfo.year === year) {
      setDragOverInfo({ year, index });
    }
  }

  function handleDragLeave() {
    setDragOverInfo(null);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>, year: number, dropIndex: number) {
    e.preventDefault();
    setDragOverInfo(null);

    if (!dragInfo || dragInfo.year !== year || dragInfo.index === dropIndex) {
      setDragInfo(null);
      return;
    }

    // Find the year group and reorder locally
    const group = yearGroups.find((g) => g.year === year);
    if (!group) {
      setDragInfo(null);
      return;
    }

    const reordered = [...group.pieces];
    const [moved] = reordered.splice(dragInfo.index, 1);
    reordered.splice(dropIndex, 0, moved);

    // Optimistically update UI
    setYearGroups((prev) =>
      prev.map((g) =>
        g.year === year ? { ...g, pieces: reordered } : g
      )
    );

    setDragInfo(null);

    // Call reorder endpoint
    saveReorder(year, reordered.map((p) => p.id));
  }

  function handleDragEnd() {
    setDragInfo(null);
    setDragOverInfo(null);
  }

  async function saveReorder(year: number, order: number[]) {
    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/cms/art/reorder`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ year, order }),
        }
      );

      if (res.status === 401) {
        localStorage.removeItem("token");
        router.replace("/cms");
        return;
      }

      if (!res.ok) {
        setError("Failed to reorder art pieces");
        await fetchArt(); // Revert optimistic update
        return;
      }
    } catch {
      setError("Unable to connect to the server");
      await fetchArt(); // Revert optimistic update
    }
  }

  // --- Render ---

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading art pieces...</p>
      </div>
    );
  }

  const { min: minYear, max: maxYear } = getValidYearRange();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Art</h1>
      </div>

      {error && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {error}
        </p>
      )}

      {/* Upload new art piece */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Add New Art Piece</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="art-year" className="block text-sm font-medium text-gray-700 mb-1">
              Year
            </label>
            <input
              id="art-year"
              type="number"
              min={minYear}
              max={maxYear}
              value={newYear}
              onChange={(e) => {
                setNewYear(parseInt(e.target.value, 10) || minYear);
                setYearError("");
              }}
              className="w-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {yearError && (
              <p className="mt-1 text-xs text-red-600">{yearError}</p>
            )}
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,.jpg,.jpeg,.png"
              onChange={handleFileSelect}
              disabled={uploading}
              className="hidden"
              aria-label="Upload art piece"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? "Uploading..." : "Upload Image"}
            </button>
            <p className="mt-1 text-xs text-gray-500">JPEG or PNG, up to 10 MB</p>
          </div>
        </div>
        {uploadError && (
          <p role="alert" className="mt-3 text-sm text-red-600">
            {uploadError}
          </p>
        )}
      </div>

      {/* Art pieces grouped by year */}
      {yearGroups.length === 0 ? (
        <p className="text-gray-500 py-8 text-center">
          No art pieces yet. Upload your first piece!
        </p>
      ) : (
        <div className="space-y-8">
          {yearGroups.map((group) => (
            <div key={group.year} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">{group.year}</h2>
                <p className="text-sm text-gray-500">{group.pieces.length} piece{group.pieces.length !== 1 ? "s" : ""}</p>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {group.pieces.map((piece, index) => (
                    <div
                      key={piece.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, group.year, index)}
                      onDragOver={(e) => handleDragOver(e, group.year, index)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, group.year, index)}
                      onDragEnd={handleDragEnd}
                      className={`relative rounded-lg border-2 overflow-hidden cursor-grab active:cursor-grabbing transition-all ${
                        dragInfo?.year === group.year && dragInfo?.index === index
                          ? "opacity-50 border-blue-400"
                          : dragOverInfo?.year === group.year && dragOverInfo?.index === index
                          ? "border-blue-500 scale-105"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      {/* Image */}
                      <div className="aspect-square relative">
                        <img
                          src={piece.cdn_url}
                          alt={piece.title || `Art piece ${piece.position}`}
                          className="w-full h-full object-cover"
                          draggable={false}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = "none";
                            const placeholder = target.nextElementSibling as HTMLElement;
                            if (placeholder) placeholder.style.display = "flex";
                          }}
                        />
                        <div
                          className="absolute inset-0 items-center justify-center bg-gray-100 text-gray-400 hidden"
                        >
                          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      </div>

                      {/* Status badge */}
                      <div className="absolute top-2 left-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            piece.status === "published"
                              ? "bg-green-100 text-green-800"
                              : "bg-yellow-100 text-yellow-800"
                          }`}
                        >
                          {piece.status}
                        </span>
                      </div>

                      {/* Position badge */}
                      <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
                        {piece.position}
                      </div>

                      {/* Controls */}
                      <div className="p-3 space-y-2">
                        {/* Title */}
                        {editingTitle && editingTitle.id === piece.id ? (
                          <div>
                            <input
                              type="text"
                              value={editingTitle.value}
                              onChange={(e) =>
                                setEditingTitle({ ...editingTitle, value: e.target.value })
                              }
                              maxLength={MAX_TITLE_LENGTH + 1}
                              placeholder="Enter title..."
                              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveTitle();
                                if (e.key === "Escape") cancelEditTitle();
                              }}
                              autoFocus
                            />
                            {titleError && (
                              <p className="mt-1 text-xs text-red-600">{titleError}</p>
                            )}
                            <div className="flex gap-1 mt-1">
                              <button
                                type="button"
                                onClick={saveTitle}
                                className="text-xs text-blue-600 hover:text-blue-800"
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                onClick={cancelEditTitle}
                                className="text-xs text-gray-500 hover:text-gray-700"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => startEditTitle(piece)}
                            className="w-full text-left text-xs text-gray-700 hover:text-gray-900 truncate"
                            title={piece.title || "Click to add title"}
                          >
                            {piece.title || <span className="italic text-gray-400">No title</span>}
                          </button>
                        )}

                        {/* Action buttons */}
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => toggleStatus(piece)}
                            className={`flex-1 text-xs px-2 py-1 rounded font-medium ${
                              piece.status === "published"
                                ? "bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                                : "bg-green-100 text-green-800 hover:bg-green-200"
                            }`}
                          >
                            {piece.status === "published" ? "Unpublish" : "Publish"}
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDelete(piece.id)}
                            className="text-xs px-2 py-1 rounded font-medium bg-red-100 text-red-700 hover:bg-red-200"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-gray-400">Drag pieces to reorder within this year.</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm mx-4">
            <p className="text-gray-800 font-medium mb-4">Delete this art piece?</p>
            <p className="text-sm text-gray-600 mb-6">
              This will permanently remove the image from storage. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleDelete(confirmDelete)}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
