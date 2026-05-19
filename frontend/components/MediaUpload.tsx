"use client";

import { useState, useRef, ChangeEvent, DragEvent } from "react";

export interface MediaData {
  s3_key: string;
  cdn_url: string;
  position: number;
  media_type: "photo" | "video";
}

interface MediaUploadProps {
  media: MediaData[];
  onChange?: (media: MediaData[]) => void;
  onMediaChange?: (media: MediaData[]) => void;
  maxItems?: number;
}

interface UploadingFile {
  name: string;
  status: "uploading" | "done" | "error";
  error?: string;
}

export const ALLOWED_TYPES: Record<string, { ext: string; maxSize: number }> = {
  "image/jpeg": { ext: "jpg", maxSize: 10 * 1024 * 1024 },
  "image/png": { ext: "png", maxSize: 10 * 1024 * 1024 },
  "video/mp4": { ext: "mp4", maxSize: 100 * 1024 * 1024 },
  "video/webm": { ext: "webm", maxSize: 100 * 1024 * 1024 },
};

export const EXT_TO_CONTENT_TYPE: Record<string, string> = {
  mp4: "video/mp4",
  webm: "video/webm",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
};

/**
 * Resolves the content type for a file, falling back to extension-based detection
 * when the browser MIME type is empty or undefined.
 */
export function resolveContentType(file: { name: string; type: string }): string | null {
  if (file.type && file.type in ALLOWED_TYPES) {
    return file.type;
  }
  // Fallback to extension
  const ext = file.name.toLowerCase().split(".").pop() || "";
  return EXT_TO_CONTENT_TYPE[ext] || null;
}

/**
 * Determines the media_type ("photo" or "video") based on a resolved content type.
 */
export function getMediaType(contentType: string): "photo" | "video" {
  return contentType.startsWith("video/") ? "video" : "photo";
}

export interface ValidationResult {
  valid: boolean;
  error?: string;
  contentType?: string;
}

/**
 * Validates a media file for type, size, and emptiness.
 * Exported separately for property-based testing.
 */
export function validateMediaFile(file: { name: string; type: string; size: number }): ValidationResult {
  // Reject 0-byte files
  if (file.size === 0) {
    return { valid: false, error: "File is empty." };
  }

  // Resolve content type (MIME or extension fallback)
  const contentType = resolveContentType(file);
  if (!contentType) {
    return { valid: false, error: "Only JPEG, PNG, MP4, and WebM files are accepted." };
  }

  // Check size limit based on media type
  const typeInfo = ALLOWED_TYPES[contentType];
  if (!typeInfo) {
    return { valid: false, error: "Only JPEG, PNG, MP4, and WebM files are accepted." };
  }

  if (file.size > typeInfo.maxSize) {
    const mediaType = getMediaType(contentType);
    if (mediaType === "video") {
      return { valid: false, error: "Video file size must be 100 MB or less." };
    } else {
      return { valid: false, error: "Photo file size must be 10 MB or less." };
    }
  }

  return { valid: true, contentType };
}


export default function MediaUpload({ media, onChange, onMediaChange, maxItems = 20 }: MediaUploadProps) {
  const [uploading, setUploading] = useState<UploadingFile[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [confirmRemoveIndex, setConfirmRemoveIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function notifyChange(updatedMedia: MediaData[]) {
    if (onChange) onChange(updatedMedia);
    if (onMediaChange) onMediaChange(updatedMedia);
  }

  async function uploadSingleFile(file: File, position: number): Promise<MediaData | null> {
    const token = localStorage.getItem("token");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    const contentType = resolveContentType(file) || file.type;
    const mediaType = getMediaType(contentType);

    // Step 1: Get presigned URL from the media presign endpoint
    const presignRes = await fetch(`${apiUrl}/api/cms/media/presign`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        filename: file.name,
        content_type: contentType,
      }),
    });

    if (!presignRes.ok) {
      const data = await presignRes.json().catch(() => null);
      throw new Error(data?.detail || "Failed to get upload URL");
    }

    const { upload_url, s3_key, cdn_url } = await presignRes.json();

    // Step 2: Upload to S3
    const uploadRes = await fetch(upload_url, {
      method: "PUT",
      headers: { "Content-Type": contentType },
      body: file,
    });

    if (!uploadRes.ok) {
      throw new Error("Failed to upload to storage");
    }

    return { s3_key, cdn_url, position, media_type: mediaType };
  }

  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const selectedFiles = Array.from(fileList);

    // Reset input so same files can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";

    // Clear previous errors
    setErrors([]);

    // Validate
    const validFiles: File[] = [];
    const newErrors: string[] = [];
    let count = media.length;

    for (const file of selectedFiles) {
      if (count >= maxItems) {
        newErrors.push(`"${file.name}": Maximum of ${maxItems} media items reached.`);
        continue;
      }
      const result = validateMediaFile(file);
      if (!result.valid) {
        newErrors.push(`"${file.name}": ${result.error}`);
      } else {
        validFiles.push(file);
        count++;
      }
    }

    if (newErrors.length > 0) setErrors(newErrors);
    if (validFiles.length === 0) return;

    // Show uploading state
    setUploading(validFiles.map((f) => ({ name: f.name, status: "uploading" })));

    // Upload each file
    const results: MediaData[] = [];
    const uploadErrors: string[] = [];
    let nextPos = media.length + 1;

    for (let i = 0; i < validFiles.length; i++) {
      const file = validFiles[i];
      try {
        const result = await uploadSingleFile(file, nextPos);
        if (result) {
          results.push(result);
          nextPos++;
          setUploading((prev) =>
            prev.map((u, idx) => (idx === i ? { ...u, status: "done" } : u))
          );
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        uploadErrors.push(`"${file.name}": ${msg}`);
        setUploading((prev) =>
          prev.map((u, idx) => (idx === i ? { ...u, status: "error", error: msg } : u))
        );
      }
    }

    if (uploadErrors.length > 0) {
      setErrors((prev) => [...prev, ...uploadErrors]);
    }

    if (results.length > 0) {
      notifyChange([...media, ...results]);
    }

    // Clear uploading indicators after delay
    setTimeout(() => setUploading([]), 3000);
  }

  function handleRemove(index: number) {
    setConfirmRemoveIndex(index);
  }

  function confirmRemove() {
    if (confirmRemoveIndex === null) return;
    const updated = media
      .filter((_, i) => i !== confirmRemoveIndex)
      .map((item, i) => ({ ...item, position: i + 1 }));
    notifyChange(updated);
    setConfirmRemoveIndex(null);
  }

  // Drag and drop reordering
  function handleDragStart(e: DragEvent<HTMLDivElement>, index: number) {
    setDragIndex(index);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>, index: number) {
    e.preventDefault();
    setDragOverIndex(index);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>, dropIndex: number) {
    e.preventDefault();
    setDragOverIndex(null);
    if (dragIndex === null || dragIndex === dropIndex) {
      setDragIndex(null);
      return;
    }

    const reordered = [...media];
    const [moved] = reordered.splice(dragIndex, 1);
    reordered.splice(dropIndex, 0, moved);
    notifyChange(reordered.map((item, i) => ({ ...item, position: i + 1 })));
    setDragIndex(null);
  }

  function handleDragEnd() {
    setDragIndex(null);
    setDragOverIndex(null);
  }

  const isMaxItems = media.length >= maxItems;

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Media ({media.length}/{maxItems})
      </label>

      {/* Media grid */}
      {media.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
          {media.map((item, index) => (
            <div
              key={item.s3_key}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={() => setDragOverIndex(null)}
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
              {item.media_type === "video" ? (
                /* Static placeholder for video preview */
                <div className="w-full h-full bg-gray-800 flex items-center justify-center">
                  <svg
                    className="w-10 h-10 text-white opacity-80"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
              ) : (
                <img
                  src={item.cdn_url}
                  alt={`Photo ${item.position}`}
                  className="w-full h-full object-cover"
                  draggable={false}
                />
              )}

              {/* Video icon overlay */}
              {item.media_type === "video" && (
                <div className="absolute bottom-1 left-1 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
                  </svg>
                  Video
                </div>
              )}

              {/* Position badge */}
              <div className="absolute top-1 left-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
                {item.position}
              </div>

              {/* Remove button */}
              <button
                type="button"
                onClick={() => handleRemove(index)}
                className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold"
                aria-label={`Remove ${item.media_type} ${item.position}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload status */}
      {uploading.length > 0 && (
        <ul className="space-y-1">
          {uploading.map((u, i) => (
            <li key={i} className="text-sm">
              {u.status === "uploading" && (
                <span className="text-blue-600">Uploading {u.name}...</span>
              )}
              {u.status === "done" && (
                <span className="text-green-600">✓ {u.name} uploaded</span>
              )}
              {u.status === "error" && (
                <span className="text-red-600">✗ {u.name}: {u.error}</span>
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
          accept="image/jpeg,image/png,video/mp4,video/webm,.jpg,.jpeg,.png,.mp4,.webm"
          multiple
          onChange={handleFileSelect}
          disabled={isMaxItems}
          className="hidden"
          aria-label="Upload media"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isMaxItems}
          className="px-4 py-2 text-sm font-medium text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isMaxItems ? `Maximum media reached (${maxItems})` : "Add Media"}
        </button>
        <p className="mt-1 text-xs text-gray-500">
          JPEG, PNG, MP4, or WebM. Photos up to 10 MB, videos up to 100 MB. Drag to reorder.
        </p>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div role="alert" className="space-y-1">
          {errors.map((error, i) => (
            <p key={i} className="text-sm text-red-600">
              {error}
            </p>
          ))}
        </div>
      )}

      {/* Remove confirmation */}
      {confirmRemoveIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm mx-4">
            <p className="text-gray-800 font-medium mb-4">Remove this media item?</p>
            <p className="text-sm text-gray-600 mb-6">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirmRemoveIndex(null)}
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
