"use client";

import { useState } from "react";
import Lightbox from "@/components/Lightbox";

interface Photo {
  cdn_url: string;
  position: number;
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
          <button
            key={photo.cdn_url}
            type="button"
            onClick={() => setLightboxIndex(index)}
            className="relative aspect-square overflow-hidden rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            aria-label={`View photo ${index + 1}`}
          >
            <img
              src={photo.cdn_url}
              alt={`Trip photo ${index + 1}`}
              className="w-full h-full object-cover"
            />
          </button>
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
