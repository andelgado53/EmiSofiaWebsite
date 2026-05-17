"use client";

import { useState } from "react";
import PhotoUploader from "@/components/PhotoUploader";

export interface TripPhotoData {
  s3_key: string;
  cdn_url: string;
  position: number;
}

export interface TripFormData {
  title: string;
  trip_date: string;
  description: string;
  status: "draft" | "published";
  photos: TripPhotoData[];
}

interface TripFormProps {
  mode: "create" | "edit";
  initialData?: {
    title: string;
    trip_date: string;
    description: string;
    status: "draft" | "published";
    photos: TripPhotoData[];
  };
  onSubmit: (data: TripFormData) => Promise<void>;
}

const MAX_TITLE_LENGTH = 150;
const MAX_DESCRIPTION_LENGTH = 2000;

export default function TripForm({ mode, initialData, onSubmit }: TripFormProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [tripDate, setTripDate] = useState(initialData?.trip_date ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [status, setStatus] = useState<"draft" | "published">(initialData?.status ?? "draft");
  const [photos, setPhotos] = useState<TripPhotoData[]>(initialData?.photos ?? []);

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
      setTitleError(`Title exceeds the maximum of ${MAX_TITLE_LENGTH} characters.`);
      valid = false;
    }

    if (description.length > MAX_DESCRIPTION_LENGTH) {
      setDescriptionError(
        `Description exceeds the maximum of ${MAX_DESCRIPTION_LENGTH.toLocaleString()} characters.`
      );
      valid = false;
    }

    if (targetStatus === "published") {
      if (!title.trim()) {
        setTitleError("Title is required to publish a trip.");
        valid = false;
      }
      if (!tripDate) {
        setDateError("Trip date is required to publish a trip.");
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
        trip_date: tripDate,
        description: description.trim(),
        status: targetStatus,
        photos,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save trip. Please try again.";
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
        <label htmlFor="trip-title" className="block text-sm font-medium text-gray-700 mb-1">
          Title
        </label>
        <input
          id="trip-title"
          type="text"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setTitleError("");
          }}
          maxLength={MAX_TITLE_LENGTH}
          placeholder="Enter trip title..."
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
          <span
            className={`text-xs ${
              title.length > MAX_TITLE_LENGTH ? "text-red-600 font-medium" : "text-gray-500"
            }`}
          >
            {title.length}/{MAX_TITLE_LENGTH}
          </span>
        </div>
      </div>

      {/* Trip Date */}
      <div>
        <label htmlFor="trip-date" className="block text-sm font-medium text-gray-700 mb-1">
          Trip Date
        </label>
        <input
          id="trip-date"
          type="date"
          value={tripDate}
          onChange={(e) => {
            setTripDate(e.target.value);
            setDateError("");
          }}
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            dateError ? "border-red-500" : "border-gray-300"
          }`}
        />
        {dateError && (
          <p role="alert" className="text-sm text-red-600 mt-1">{dateError}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="trip-description" className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          id="trip-description"
          value={description}
          onChange={(e) => {
            setDescription(e.target.value);
            setDescriptionError("");
          }}
          maxLength={MAX_DESCRIPTION_LENGTH}
          placeholder="Describe the trip..."
          rows={5}
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y ${
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
        <label htmlFor="trip-status" className="block text-sm font-medium text-gray-700 mb-1">
          Status
        </label>
        <select
          id="trip-status"
          value={status}
          onChange={(e) => setStatus(e.target.value as "draft" | "published")}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>
      </div>

      {/* Photos */}
      <PhotoUploader photos={photos} onPhotosChange={setPhotos} />

      {/* Action buttons */}
      <div className="flex gap-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={() => handleSave("draft")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Saving..." : "Save Draft"}
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
