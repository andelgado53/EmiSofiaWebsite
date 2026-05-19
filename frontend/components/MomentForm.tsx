"use client";

import { useState, useRef, ChangeEvent, DragEvent } from "react";

export interface MomentPhotoData {
  s3_key: string;
  cdn_url: string;
  position: number;
}

export interface MomentFormData {
  title: string;
  moment_date: string;
  description: string;
  status: "draft" | "published";
  photos: MomentPhotoData[];
}

interface MomentFormProps {
  mode: "create" | "edit";
  initialData?: {
    title: string;
    moment_date: string;
    description: string;
    status: "draft" | "published";
    photos: MomentPhotoData[];
  };
  onSubmit: (data: MomentFormData) => Promise<void>;
}

interface UploadingFile {
  name: string;
  status: "uploading" | "done" | "error";
  error?: string;
}

const MAX_TITLE_LENGTH = 150;
const MAX_DESCRIPTION_LENGTH = 2000;
const MAX_PHOTOS = 2;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png"];

export default function MomentForm({ mode, initialData, onSubmit }: MomentFormProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [momentDate, setMomentDate] = useState(initialData?.moment_date ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [status, setStatus] = useState<"draft" | "published">(initialData?.status ?? "draft");
  const [photos, setPhotos] = useState<MomentPhotoData[]>(initialData?.photos ?? []);

  const [titleError, setTitleError] = useState("");
  const [dateError, setDateError] = useState("");
  const [descriptionError, setDescriptionError] = useState("");
  const [generalError, setGeneralError] = useState("");
  const [photoErrors, setPhotoErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Photo upload state
  const [uploading, setUploading] = useState<UploadingFile[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function validate(targetStatus: "draft" | "published"): boolean {
    let valid = true;
    setTitleError("");
    setDateError("");
    setDescriptionError("");
    setGeneralError("");

    if (title.length > MAX_TITLE_LENGTH) {
      setTitleError(`Title must be between 1 and ${MAX_TITLE_LENGTH} characters.`);
      valid = false;
    }

    if (description.length > MAX_DESCRIPTION_LENGTH) {
      setDescriptionError(
        `Description must be between 1 and ${MAX_DESCRIPTION_LENGTH.toLocaleString()} characters.`
      );
      valid = false;
    }

    if (targetStatus === "published") {
      if (!title.trim()) {
        setTitleError("Title is required to publish a moment.");
        valid = false;
      }
      if (!momentDate) {
        setDateError("Date is required to publish a moment.");
        valid = false;
      }
      if (!description.trim()) {
        setDescriptionError("Description is required to publish a moment.");
        valid = false;
      }
    }

    return valid;
  }

  async function handleSave(targetStatus: "draft" | "published") {
    if (!validate(targetStatus)) return;

    setIsSaving(true);
    setGeneralError("");

    try {
      await onSubmit({
        title: title.trim(),
        moment_date: momentDate,
        description: description.trim(),
        status: targetStatus,
        photos,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save moment. Please try again.";
      setGeneralError(message);
    } finally {
      setIsSaving(false);
    }
  }

  // --- Photo upload logic ---

  function isValidFile(file: File): string | null {
    let valid = ALLOWED_TYPES.includes(file.type);
    if (!valid && file.name) {
      const ext = file.name.toLowerCase().split(".").pop() || "";
      valid = ["jpg", "jpeg", "png"].includes(ext);
    }
    if (!valid) return `"${file.name}": Only JPEG and PNG files are accepted.`;
    if (file.size > MAX_FILE_SIZE) return `"${file.name}": File size must be 10 MB or less.`;
    return null;
  }

  async function uploadSingleFile(file: File, position: number): Promise<MomentPhotoData | null> {
    const token = localStorage.getItem("token");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

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

    const selectedFiles = Array.from(fileList);

    if (fileInputRef.current) fileInputRef.current.value = "";

    setPhotoErrors([]);

    const validFiles: File[] = [];
    const newErrors: string[] = [];
    let count = photos.length;

    for (const file of selectedFiles) {
      if (count >= MAX_PHOTOS) {
        newErrors.push(`"${file.name}": Maximum of ${MAX_PHOTOS} photos per moment reached.`);
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

    if (newErrors.length > 0) setPhotoErrors(newErrors);
    if (validFiles.length === 0) return;

    setUploading(validFiles.map((f) => ({ name: f.name, status: "uploading" })));

    const results: MomentPhotoData[] = [];
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
      setPhotoErrors((prev) => [...prev, ...uploadErrors]);
    }

    if (results.length > 0) {
      setPhotos((prev) => [...prev, ...results]);
    }

    setTimeout(() => setUploading([]), 3000);
  }

  function handleRemovePhoto(index: number) {
    const updated = photos
      .filter((_, i) => i !== index)
      .map((photo, i) => ({ ...photo, position: i + 1 }));
    setPhotos(updated);
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
    if (dragIndex === null || dragIndex === dropIndex) {
      setDragIndex(null);
      return;
    }

    const reordered = [...photos];
    const [moved] = reordered.splice(dragIndex, 1);
    reordered.splice(dropIndex, 0, moved);
    setPhotos(reordered.map((p, i) => ({ ...p, position: i + 1 })));
    setDragIndex(null);
  }

  function handleDragEnd() {
    setDragIndex(null);
    setDragOverIndex(null);
  }

  const isMaxPhotos = photos.length >= MAX_PHOTOS;

  return (
    <div className="space-y-6">
      {/* General error */}
      {generalError && (
        <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{generalError}</p>
        </div>
      )}

      {/* Title */}
      <div>
        <label htmlFor="moment-title" className="block text-sm font-medium text-gray-700 mb-1">
          Title
        </label>
        <input
          id="moment-title"
          type="text"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setTitleError("");
          }}
          maxLength={MAX_TITLE_LENGTH}
          placeholder="Enter moment title..."
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-pink-500 ${
            titleError ? "border-red-500" : "border-gray-300"
          }`}
        />
        <div className="flex justify-between mt-1">
          {titleError ? (
            <p role="alert" className="text-sm text-red-600">{titleError}</p>
          ) : (
            <span />
          )}
          <span
            className={`text-xs ${
              title.length > MAX_TITLE_LENGTH ? "text-red-600 font-medium" : "text-gray-500"
            }`}
          >
            {title.length}/{MAX_TITLE_LENGTH}
          </span>
        </div>
      </div>

      {/* Moment Date */}
      <div>
        <label htmlFor="moment-date" className="block text-sm font-medium text-gray-700 mb-1">
          Date
        </label>
        <input
          id="moment-date"
          type="date"
          value={momentDate}
          onChange={(e) => {
            setMomentDate(e.target.value);
            setDateError("");
          }}
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-pink-500 ${
            dateError ? "border-red-500" : "border-gray-300"
          }`}
        />
        {dateError && (
          <p role="alert" className="text-sm text-red-600 mt-1">{dateError}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="moment-description" className="block text-sm font-medium text-gray-700 mb-1">
          Description <span className="text-red-500">*</span>
        </label>
        <textarea
          id="moment-description"
          value={description}
          onChange={(e) => {
            setDescription(e.target.value);
            setDescriptionError("");
          }}
          maxLength={MAX_DESCRIPTION_LENGTH}
          placeholder="Describe this moment..."
          rows={6}
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-pink-500 resize-y ${
            descriptionError ? "border-red-500" : "border-gray-300"
          }`}
        />
        <div className="flex justify-between mt-1">
          {descriptionError ? (
            <p role="alert" className="text-sm text-red-600">{descriptionError}</p>
          ) : (
            <span />
          )}
          <span
            className={`text-xs ${
              description.length > MAX_DESCRIPTION_LENGTH ? "text-red-600 font-medium" : "text-gray-500"
            }`}
          >
            {description.length.toLocaleString()}/{MAX_DESCRIPTION_LENGTH.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Status */}
      <div>
        <label htmlFor="moment-status" className="block text-sm font-medium text-gray-700 mb-1">
          Status
        </label>
        <select
          id="moment-status"
          value={status}
          onChange={(e) => setStatus(e.target.value as "draft" | "published")}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-pink-500"
        >
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>
      </div>

      {/* Photos */}
      <div className="space-y-4">
        <label className="block text-sm font-medium text-gray-700">
          Photos ({photos.length}/{MAX_PHOTOS})
        </label>

        {/* Photo list - inline display */}
        {photos.length > 0 && (
          <div className="space-y-3">
            {photos.map((photo, index) => (
              <div
                key={photo.s3_key}
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragLeave={() => setDragOverIndex(null)}
                onDrop={(e) => handleDrop(e, index)}
                onDragEnd={handleDragEnd}
                className={`relative rounded-lg overflow-hidden border-2 cursor-grab active:cursor-grabbing transition-all ${
                  dragIndex === index
                    ? "opacity-50 border-pink-400"
                    : dragOverIndex === index
                    ? "border-pink-500 scale-[1.01]"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <img
                  src={photo.cdn_url}
                  alt={`Photo ${photo.position}`}
                  className="w-full h-auto object-contain"
                  draggable={false}
                />
                <div className="absolute top-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                  {photo.position}
                </div>
                <button
                  type="button"
                  onClick={() => handleRemovePhoto(index)}
                  className="absolute top-2 right-2 bg-red-600 hover:bg-red-700 text-white rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold"
                  aria-label={`Remove photo ${photo.position}`}
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
                  <span className="text-pink-600">Uploading {u.name}...</span>
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
            accept="image/jpeg,image/png,.jpg,.jpeg,.png"
            multiple
            onChange={handleFileSelect}
            disabled={isMaxPhotos}
            className="hidden"
            aria-label="Upload photos"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isMaxPhotos}
            className="px-4 py-2 text-sm font-medium text-pink-600 border border-pink-600 rounded-md hover:bg-pink-50 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isMaxPhotos ? `Maximum photos reached (${MAX_PHOTOS})` : "Add Photos"}
          </button>
          <p className="mt-1 text-xs text-gray-500">
            JPEG or PNG, up to 10 MB each. Max {MAX_PHOTOS} photos. Drag photos to reorder.
          </p>
        </div>

        {/* Photo errors */}
        {photoErrors.length > 0 && (
          <div role="alert" className="space-y-1">
            {photoErrors.map((error, i) => (
              <p key={i} className="text-sm text-red-600">{error}</p>
            ))}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={() => handleSave("draft")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Saving..." : "Save Draft"}
        </button>
        <button
          type="button"
          onClick={() => handleSave("published")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-white bg-pink-600 rounded-md hover:bg-pink-700 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Publishing..." : "Publish"}
        </button>
      </div>
    </div>
  );
}
