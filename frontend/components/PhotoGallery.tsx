"use client";

import { useState } from "react";
import Lightbox from "@/components/Lightbox";

interface Photo {
  cdn_url: string;
  position: number;
  media_type?: string;
}

interface PhotoGalleryProps {
  photos: Photo[];
}

export default function PhotoGallery({ photos }: PhotoGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const sortedPhotos = [...photos].sort((a, b) => a.position - b.position);

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {sortedPhotos.map((photo, index) => (
          <div key={photo.cdn_url} className="relative aspect-square overflow-hidden rounded-md">
            <button
              type="button"
              onClick={() => setLightboxIndex(index)}
              className="w-full h-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              aria-label={photo.media_type === "video" ? `Play video ${index + 1}` : `View photo ${index + 1}`}
            >
              {photo.media_type === "video" ? (
                <div className="w-full h-full bg-gray-900 flex items-center justify-center relative">
                  <video
                    src={photo.cdn_url}
                    className="w-full h-full object-cover"
                    muted
                    playsInline
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-black/60 rounded-full p-3">
                      <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                  </div>
                </div>
              ) : (
                <img
                  src={photo.cdn_url}
                  alt={`Trip photo ${index + 1}`}
                  className="w-full h-full object-cover"
                />
              )}
            </button>
          </div>
        ))}
      </div>

      {lightboxIndex !== null && (
        <Lightbox
          photos={sortedPhotos}
          initialIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </>
  );
}
