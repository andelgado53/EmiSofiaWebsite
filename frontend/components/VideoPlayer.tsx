"use client";

import { useState } from "react";

interface VideoPlayerProps {
  src: string;
  alt?: string;
  className?: string;
}

export default function VideoPlayer({ src, alt, className }: VideoPlayerProps) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 text-gray-500 rounded-md ${className ?? ""}`}
        role="alert"
        aria-label={alt ?? "Video unavailable"}
      >
        <p>Video unavailable</p>
      </div>
    );
  }

  return (
    <video
      src={src}
      controls
      className={className}
      aria-label={alt ?? "Video"}
      onError={() => setHasError(true)}
    >
      Your browser does not support the video element.
    </video>
  );
}
