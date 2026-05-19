"use client";

import { useState } from "react";
import Lightbox from "@/components/Lightbox";

interface ArtPiece {
  id: number;
  cdn_url: string;
  title: string | null;
  position: number;
  media_type: string;
}

interface ArtYearGalleryProps {
  pieces: ArtPiece[];
}

export default function ArtYearGallery({ pieces }: ArtYearGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // All pieces (photos and videos) go into the lightbox
  const lightboxPhotos = pieces.map((piece) => ({
    cdn_url: piece.cdn_url,
    position: piece.position,
    title: piece.title ?? undefined,
    media_type: piece.media_type,
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
                  : piece.media_type === "video"
                  ? `Play video ${index + 1}`
                  : `View art piece ${index + 1}`
              }
            >
              {piece.media_type === "video" ? (
                <div className="w-full h-full bg-gray-900 flex items-center justify-center relative">
                  <video
                    src={piece.cdn_url}
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
                  src={piece.cdn_url}
                  alt={piece.title || `Art piece ${index + 1}`}
                  className="w-full h-full object-cover"
                />
              )}
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
