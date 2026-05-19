"use client";

import { useState } from "react";
import Lightbox from "@/components/Lightbox";
import VideoPlayer from "@/components/VideoPlayer";

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
            {photo.media_type === "video" ? (
              <VideoPlayer
                src={photo.cdn_url}
                alt={`Trip video ${index + 1}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <button
                type="button"
                onClick={() => setLightboxIndex(index)}
                className="w-full h-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                aria-label={`View photo ${index + 1}`}
              >
                <img
                  src={photo.cdn_url}
                  alt={`Trip photo ${index + 1}`}
                  className="w-full h-full object-cover"
                />
              </button>
            )}
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
