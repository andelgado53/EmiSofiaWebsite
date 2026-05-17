"use client";

import { useState } from "react";

interface LabelInputProps {
  labels: string[];
  onLabelsChange: (labels: string[]) => void;
}

export default function LabelInput({ labels, onLabelsChange }: LabelInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const MAX_LABELS = 20;
  const MAX_LABEL_LENGTH = 50;

  const handleAdd = () => {
    setError(null);
    setWarning(null);

    const trimmed = inputValue.trim();

    if (!trimmed) {
      setError("Label cannot be empty.");
      return;
    }

    if (trimmed.length > MAX_LABEL_LENGTH) {
      setError(`Label must be 50 characters or fewer (currently ${trimmed.length}).`);
      return;
    }

    const isDuplicate = labels.some(
      (label) => label.toLowerCase() === trimmed.toLowerCase()
    );

    if (isDuplicate) {
      setWarning(`"${trimmed}" already exists (case-insensitive match).`);
      return;
    }

    onLabelsChange([...labels, trimmed]);
    setInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  const handleRemove = (index: number) => {
    const updated = labels.filter((_, i) => i !== index);
    onLabelsChange(updated);
    setError(null);
    setWarning(null);
  };

  const isAtMax = labels.length >= MAX_LABELS;

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Labels ({labels.length}/{MAX_LABELS})
      </label>

      {/* Label chips */}
      {labels.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {labels.map((label, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-800"
            >
              {label}
              <button
                type="button"
                onClick={() => handleRemove(index)}
                className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-blue-600 hover:bg-blue-200 hover:text-blue-900"
                aria-label={`Remove label ${label}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value);
            setError(null);
            setWarning(null);
          }}
          onKeyDown={handleKeyDown}
          disabled={isAtMax}
          placeholder={isAtMax ? "Maximum labels reached" : "Add a label..."}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100"
          aria-label="Label input"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={isAtMax}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          Add
        </button>
      </div>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Warning message */}
      {warning && (
        <p className="text-sm text-yellow-600" role="alert">
          {warning}
        </p>
      )}
    </div>
  );
}
