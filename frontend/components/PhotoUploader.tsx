"use client";

import { useState, useRef, ChangeEvent, DragEvent } from "react";

interface PhotoData {
  s3_key: string;
  cdn_url: string;
  position: number;
}

interface PhotoUploaderProps {
  photos: PhotoData[];
  onChange?: (photos: PhotoData[]) => void;
  onPhotosChange?: (photos: PhotoData[]) => void;
}

interface UploadStatus {
  file: File;
  status: "uploading" | "done" | "error";
  error?: string;
}

const MAX_PHOTOS = 20;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png"];

export default function PhotoUploader({ photos, onChange, onPhotosChange }: PhotoUploaderProps) {
  const notifyChange = (updatedPhotos: PhotoData[]) => {
    if (onChange) onChange(updatedPhotos);
    if (onPhotosChange) onPhotosChange(updatedPhotos);
  };

  const [uploadStatuses, setUploadStatuses] = useState<Map<string, UploadStatus>>(new Map());
  const [errors, setErrors] = useState<string[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [confirmRemoveIndex, setConfirmRemoveIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isMaxPhotos = photos.length >= MAX_PHOTOS;

  function validateFile(file: File, currentCount: number): string | null {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `"${file.name}": Only JPEG and PNG files are accepted.`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `"${file.name}": File size must be 10 MB or less.`;
    }
    if (currentCount >= MAX_PHOTOS) {
      return `"${file.name}": Maximum of 20 photos per trip reached.`;
    }
    return null;
  }

  async function uploadFile(file: File, position: number, statusKey: string): Promise<PhotoData | null> {
    try {
      const token = localStorage.getItem("token");
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;

      // Request presigned URL
      const presignRes = await fetch(`${apiUrl}/api/cms/photos/presign`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type,
        }),
      });

      if (!presignRes.ok) {
        const data = await presignRes.json().catch(() => null);
        throw new Error(data?.detail || "Failed to get upload URL");
      }

      const { upload_url, s3_key, cdn_url } = await presignRes.json();

      // Upload file directly to S3 using fetch (same approach as working PhotoUpload component)
      const uploadRes = await fetch(upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": file.type,
        },
        body: file,
      });

      if (!uploadRes.ok) {
        throw new Error("Failed to upload photo to storage");
      }

      setUploadStatuses((prev) => {
        const next = new Map(prev);
        next.set(statusKey, { file, status: "done" });
        return next;
      });

      return { s3_key, cdn_url, position };
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setUploadStatuses((prev) => {
        const next = new Map(prev);
        next.set(statusKey, { file, status: "error", error: message });
        return next;
      });
      return null;
    }
  }

  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    setErrors([]);
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Reset the input so the same files can be re-selected
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    const fileArray = Array.from(files);
    const validationErrors: string[] = [];
    const validFiles: File[] = [];
    let currentCount = photos.length;

    for (const file of fileArray) {
      const error = validateFile(file, currentCount);
      if (error) {
        validationErrors.push(error);
      } else {
        validFiles.push(file);
        currentCount++;
      }
    }

    if (validationErrors.length > 0) {
      setErrors(validationErrors);
    }

    if (validFiles.length === 0) return;

    // Start uploads
    const uploadPromises: Promise<PhotoData | null>[] = [];
    let nextPosition = photos.length + 1;

    for (const file of validFiles) {
      const statusKey = `${Date.now()}-${file.name}`;
      setUploadStatuses((prev) => {
        const next = new Map(prev);
        next.set(statusKey, { file, status: "uploading" });
        return next;
      });
      uploadPromises.push(uploadFile(file, nextPosition, statusKey));
      nextPosition++;
    }

    const results = await Promise.all(uploadPromises);
    const newPhotos = results.filter((r): r is PhotoData => r !== null);

    if (newPhotos.length > 0) {
      notifyChange([...photos, ...newPhotos]);
    }

    // Clear done statuses after a delay
    setTimeout(() => {
      setUploadStatuses((prev) => {
        const next = new Map(prev);
        const entries = Array.from(next.entries());
        for (const [key, status] of entries) {
          if (status.status === "done") {
            next.delete(key);
          }
        }
        return next;
      });
    }, 3000);
  }

  function handleRemove(index: number) {
    setConfirmRemoveIndex(index);
  }

  function confirmRemove() {
    if (confirmRemoveIndex === null) return;
    const updated = photos
      .filter((_, i) => i !== confirmRemoveIndex)
      .map((photo, i) => ({ ...photo, position: i + 1 }));
    notifyChange(updated);
    setConfirmRemoveIndex(null);
    setErrors([]);
  }

  function cancelRemove() {
    setConfirmRemoveIndex(null);
  }

  // Drag and drop handlers
  function handleDragStart(e: DragEvent<HTMLDivElement>, index: number) {
    setDragIndex(index);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>, index: number) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverIndex(index);
  }

  function handleDragLeave() {
    setDragOverIndex(null);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>, dropIndex: number) {
    e.preventDefault();
    setDragOverIndex(null);

    if (dragIndex === null || dragIndex === dropIndex) {
      setDragIndex(null);
      return;
    }

    const reordered = [...photos];
    const [moved] = reordered.splice(dragIndex, 1);
    reordered.splice(dropIndex, 0, moved);

    // Recalculate positions as 1, 2, ..., N
    const updated = reordered.map((photo, i) => ({ ...photo, position: i + 1 }));
    notifyChange(updated);
    setDragIndex(null);
  }

  function handleDragEnd() {
    setDragIndex(null);
    setDragOverIndex(null);
  }

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Photos ({photos.length}/{MAX_PHOTOS})
      </label>

      {/* Photo grid with drag-and-drop */}
      {photos.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
          {photos.map((photo, index) => (
            <div
              key={photo.s3_key}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              className={`relative aspect-square rounded-lg overflow-hidden border-2 cursor-grab active:cursor-grabbing transition-all ${
                dragIndex === index
                  ? "opacity-50 border-blue-400"
                  : dragOverIndex === index
                  ? "border-blue-500 scale-105"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <img
                src={photo.cdn_url}
                alt={`Photo ${photo.position}`}
                className="w-full h-full object-cover"
                draggable={false}
              />
              <div className="absolute top-1 left-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
                {photo.position}
              </div>
              <button
                type="button"
                onClick={() => handleRemove(index)}
                className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold"
                aria-label={`Remove photo ${photo.position}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload progress indicators */}
      {uploadStatuses.size > 0 && (
        <ul className="space-y-2">
          {Array.from(uploadStatuses.entries()).map(([key, status]) => (
            <li key={key} className="text-sm">
              {status.status === "uploading" && (
                <span className="text-blue-600">
                  Uploading {status.file.name}...
                </span>
              )}
              {status.status === "done" && (
                <span className="text-green-600">✓ {status.file.name} uploaded</span>
              )}
              {status.status === "error" && (
                <span className="text-red-600">✗ {status.file.name}: {status.error}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Upload button */}
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          multiple
          onChange={handleFileSelect}
          disabled={isMaxPhotos}
          className="hidden"
          id="trip-photo-upload-input"
          aria-label="Upload photos"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isMaxPhotos}
          className="px-4 py-2 text-sm font-medium text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isMaxPhotos ? "Maximum photos reached (20)" : "Add Photos"}
        </button>
        <p className="mt-1 text-xs text-gray-500">
          JPEG or PNG, up to 10 MB each. Drag photos to reorder.
        </p>
      </div>

      {/* Validation errors */}
      {errors.length > 0 && (
        <div role="alert" className="space-y-1">
          {errors.map((error, i) => (
            <p key={i} className="text-sm text-red-600">{error}</p>
          ))}
        </div>
      )}

      {/* Remove confirmation dialog */}
      {confirmRemoveIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm mx-4">
            <p className="text-gray-800 font-medium mb-4">
              Remove this photo?
            </p>
            <p className="text-sm text-gray-600 mb-6">
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={cancelRemove}
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmRemove}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
