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

interface UploadingFile {
  name: string;
  status: "uploading" | "done" | "error";
  error?: string;
}

const MAX_PHOTOS = 20;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png"];

export default function PhotoUploader({ photos, onChange, onPhotosChange }: PhotoUploaderProps) {
  const [uploading, setUploading] = useState<UploadingFile[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [confirmRemoveIndex, setConfirmRemoveIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function notifyChange(updatedPhotos: PhotoData[]) {
    if (onChange) onChange(updatedPhotos);
    if (onPhotosChange) onPhotosChange(updatedPhotos);
  }

  function isValidFile(file: File): string | null {
    // Check MIME type or fall back to extension
    let valid = ALLOWED_TYPES.includes(file.type);
    if (!valid && file.name) {
      const ext = file.name.toLowerCase().split(".").pop() || "";
      valid = ["jpg", "jpeg", "png"].includes(ext);
    }
    if (!valid) return `"${file.name}": Only JPEG and PNG files are accepted.`;
    if (file.size > MAX_FILE_SIZE) return `"${file.name}": File size must be 10 MB or less.`;
    return null;
  }

  async function uploadSingleFile(file: File, position: number): Promise<PhotoData | null> {
    const token = localStorage.getItem("token");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    // Step 1: Get presigned URL
    const presignRes = await fetch(`${apiUrl}/api/cms/photos/presign`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || "image/jpeg",
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
      headers: { "Content-Type": file.type || "image/jpeg" },
      body: file,
    });

    if (!uploadRes.ok) {
      throw new Error("Failed to upload to storage");
    }

    return { s3_key, cdn_url, position };
  }

  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    // Grab files before resetting input
    const selectedFiles = Array.from(fileList);

    // Reset input so same files can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";

    // Clear previous errors
    setErrors([]);

    // Validate
    const validFiles: File[] = [];
    const newErrors: string[] = [];
    let count = photos.length;

    for (const file of selectedFiles) {
      if (count >= MAX_PHOTOS) {
        newErrors.push(`"${file.name}": Maximum of 20 photos per trip reached.`);
        continue;
      }
      const err = isValidFile(file);
      if (err) {
        newErrors.push(err);
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
    const results: PhotoData[] = [];
    const uploadErrors: string[] = [];
    let nextPos = photos.length + 1;

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
      notifyChange([...photos, ...results]);
    }

    // Clear uploading indicators after delay
    setTimeout(() => setUploading([]), 3000);
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
  }

  // Drag and drop
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
    if (dragIndex === null || dragIndex === dropIndex) { setDragIndex(null); return; }

    const reordered = [...photos];
    const [moved] = reordered.splice(dragIndex, 1);
    reordered.splice(dropIndex, 0, moved);
    notifyChange(reordered.map((p, i) => ({ ...p, position: i + 1 })));
    setDragIndex(null);
  }

  function handleDragEnd() { setDragIndex(null); setDragOverIndex(null); }

  const isMaxPhotos = photos.length >= MAX_PHOTOS;

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Photos ({photos.length}/{MAX_PHOTOS})
      </label>

      {/* Photo grid */}
      {photos.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
          {photos.map((photo, index) => (
            <div
              key={photo.s3_key}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={() => setDragOverIndex(null)}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              className={`relative aspect-square rounded-lg overflow-hidden border-2 cursor-grab active:cursor-grabbing transition-all ${
                dragIndex === index ? "opacity-50 border-blue-400"
                  : dragOverIndex === index ? "border-blue-500 scale-105"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <img src={photo.cdn_url} alt={`Photo ${photo.position}`} className="w-full h-full object-cover" draggable={false} />
              <div className="absolute top-1 left-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">{photo.position}</div>
              <button type="button" onClick={() => handleRemove(index)} className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold" aria-label={`Remove photo ${photo.position}`}>×</button>
            </div>
          ))}
        </div>
      )}

      {/* Upload status */}
      {uploading.length > 0 && (
        <ul className="space-y-1">
          {uploading.map((u, i) => (
            <li key={i} className="text-sm">
              {u.status === "uploading" && <span className="text-blue-600">Uploading {u.name}...</span>}
              {u.status === "done" && <span className="text-green-600">✓ {u.name} uploaded</span>}
              {u.status === "error" && <span className="text-red-600">✗ {u.name}: {u.error}</span>}
            </li>
          ))}
        </ul>
      )}

      {/* Upload button */}
      <div>
        <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,.jpg,.jpeg,.png" multiple onChange={handleFileSelect} disabled={isMaxPhotos} className="hidden" aria-label="Upload photos" />
        <button type="button" onClick={() => fileInputRef.current?.click()} disabled={isMaxPhotos} className="px-4 py-2 text-sm font-medium text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed">
          {isMaxPhotos ? "Maximum photos reached (20)" : "Add Photos"}
        </button>
        <p className="mt-1 text-xs text-gray-500">JPEG or PNG, up to 10 MB each. Drag photos to reorder.</p>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div role="alert" className="space-y-1">
          {errors.map((error, i) => (<p key={i} className="text-sm text-red-600">{error}</p>))}
        </div>
      )}

      {/* Remove confirmation */}
      {confirmRemoveIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm mx-4">
            <p className="text-gray-800 font-medium mb-4">Remove this photo?</p>
            <p className="text-sm text-gray-600 mb-6">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setConfirmRemoveIndex(null)} className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50">Cancel</button>
              <button type="button" onClick={confirmRemove} className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700">Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
