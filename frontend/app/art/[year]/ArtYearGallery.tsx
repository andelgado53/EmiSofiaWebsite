"use client";

import { useState } from "react";
import Lightbox from "@/components/Lightbox";

interface ArtPiece {
  id: number;
  cdn_url: string;
  title: string | null;
  position: number;
}

interface ArtYearGalleryProps {
  pieces: ArtPiece[];
}

export default function ArtYearGallery({ pieces }: ArtYearGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const lightboxPhotos = pieces.map((piece) => ({
    cdn_url: piece.cdn_url,
    position: piece.position,
    title: piece.title ?? undefined,
  }));

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {pieces.map((piece, index) => (
          <div key={piece.id}>
            <button
              type="button"
              onClick={() => setLightboxIndex(index)}
              className="relative aspect-square w-full overflow-hidden rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2"
              aria-label={
                piece.title
                  ? `View "${piece.title}"`
                  : `View art piece ${index + 1}`
              }
            >
              <img
                src={piece.cdn_url}
                alt={piece.title || `Art piece ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
            {piece.title && (
              <p className="mt-1 text-sm text-gray-700 truncate">
                {piece.title}
              </p>
            )}
          </div>
        ))}
      </div>

      {lightboxIndex !== null && (
        <Lightbox
          photos={lightboxPhotos}
          initialIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </>
  );
}
