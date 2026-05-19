"use client";

import { useState } from "react";
import MediaUpload, { MediaData } from "@/components/MediaUpload";

export interface MomentFormData {
  title: string;
  moment_date: string;
  description: string;
  status: "draft" | "published";
  photos: MediaData[];
}

interface MomentFormProps {
  mode: "create" | "edit";
  initialData?: {
    title: string;
    moment_date: string;
    description: string;
    status: "draft" | "published";
    photos: MediaData[];
  };
  onSubmit: (data: MomentFormData) => Promise<void>;
}

const MAX_TITLE_LENGTH = 150;
const MAX_DESCRIPTION_LENGTH = 2000;

export default function MomentForm({ mode, initialData, onSubmit }: MomentFormProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [momentDate, setMomentDate] = useState(initialData?.moment_date ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [status, setStatus] = useState<"draft" | "published">(initialData?.status ?? "draft");
  const [media, setMedia] = useState<MediaData[]>(initialData?.photos ?? []);

  const [titleError, setTitleError] = useState("");
  const [dateError, setDateError] = useState("");
  const [descriptionError, setDescriptionError] = useState("");
  const [generalError, setGeneralError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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
        photos: media,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save moment. Please try again.";
      setGeneralError(message);
    } finally {
      setIsSaving(false);
    }
  }

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

      {/* Media */}
      <MediaUpload media={media} onMediaChange={setMedia} maxItems={2} />

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
