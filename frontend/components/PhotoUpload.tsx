"use client";

import { useState, useRef, ChangeEvent } from "react";

interface PhotoData {
  s3_key: string;
  cdn_url: string;
  position: number;
}

interface PhotoUploadProps {
  photos: PhotoData[];
  onPhotosChange: (photos: PhotoData[]) => void;
  onInsertPhoto?: (cdnUrl: string, float: "left" | "right") => void;
}

interface UploadStatus {
  file: File;
  progress: "uploading" | "done" | "error";
  error?: string;
}

const MAX_PHOTOS = 2;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png"];

export default function PhotoUpload({ photos, onPhotosChange, onInsertPhoto }: PhotoUploadProps) {
  const [uploadStatuses, setUploadStatuses] = useState<Map<number, UploadStatus>>(new Map());
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isMaxPhotos = photos.length >= MAX_PHOTOS;

  function validateFile(file: File): string | null {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return "Only JPEG and PNG files are accepted.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "File size must be 10 MB or less.";
    }
    return null;
  }

  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    setError("");
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset the input so the same file can be re-selected
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    if (photos.length >= MAX_PHOTOS) {
      setError("A maximum of two photos is allowed per note.");
      return;
    }

    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    const position = photos.length + 1;
    const statusKey = Date.now();

    setUploadStatuses((prev) => {
      const next = new Map(prev);
      next.set(statusKey, { file, progress: "uploading" });
      return next;
    });

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

      // Upload file directly to S3
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

      // Update upload status to done
      setUploadStatuses((prev) => {
        const next = new Map(prev);
        next.set(statusKey, { file, progress: "done" });
        return next;
      });

      // Add photo to parent form state
      const newPhoto: PhotoData = { s3_key, cdn_url, position };
      onPhotosChange([...photos, newPhoto]);

      // Clear the status after a short delay
      setTimeout(() => {
        setUploadStatuses((prev) => {
          const next = new Map(prev);
          next.delete(statusKey);
          return next;
        });
      }, 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setUploadStatuses((prev) => {
        const next = new Map(prev);
        next.set(statusKey, { file, progress: "error", error: message });
        return next;
      });
    }
  }

  function handleRemove(index: number) {
    const updated = photos
      .filter((_, i) => i !== index)
      .map((photo, i) => ({ ...photo, position: i + 1 }));
    onPhotosChange(updated);
    setError("");
  }

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Photos ({photos.length}/{MAX_PHOTOS})
      </label>

      {/* Attached photos */}
      {photos.length > 0 && (
        <ul className="space-y-2">
          {photos.map((photo, index) => (
            <li
              key={photo.s3_key}
              className="flex items-center justify-between p-2 bg-gray-50 rounded-md border border-gray-200"
            >
              <div className="flex items-center gap-2 min-w-0">
                <img
                  src={photo.cdn_url}
                  alt={`Photo ${photo.position}`}
                  className="w-10 h-10 object-cover rounded"
                />
                <span className="text-sm text-gray-600 truncate">
                  Photo {photo.position}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {onInsertPhoto && (
                  <>
                    <button
                      type="button"
                      onClick={() => onInsertPhoto(photo.cdn_url, "left")}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-1 border border-blue-300 rounded"
                      title="Insert at cursor, float left"
                    >
                      ← Insert Left
                    </button>
                    <button
                      type="button"
                      onClick={() => onInsertPhoto(photo.cdn_url, "right")}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-1 border border-blue-300 rounded"
                      title="Insert at cursor, float right"
                    >
                      Insert Right →
                    </button>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => handleRemove(index)}
                  className="text-sm text-red-600 hover:text-red-800 font-medium px-2 py-1"
                  aria-label={`Remove photo ${photo.position}`}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Upload statuses */}
      {uploadStatuses.size > 0 && (
        <ul className="space-y-1">
          {Array.from(uploadStatuses.entries()).map(([key, status]) => (
            <li key={key} className="text-sm">
              {status.progress === "uploading" && (
                <span className="text-blue-600">
                  Uploading {status.file.name}...
                </span>
              )}
              {status.progress === "done" && (
                <span className="text-green-600">
                  ✓ {status.file.name} uploaded
                </span>
              )}
              {status.progress === "error" && (
                <span className="text-red-600">
                  ✗ {status.file.name}: {status.error}
                </span>
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
          onChange={handleFileSelect}
          disabled={isMaxPhotos}
          className="hidden"
          id="photo-upload-input"
          aria-label="Upload photo"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isMaxPhotos}
          className="px-4 py-2 text-sm font-medium text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isMaxPhotos ? "Maximum photos reached" : "Add Photo"}
        </button>
      </div>

      {/* Error message */}
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
