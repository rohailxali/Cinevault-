"use client";

import Image from "next/image";
import { useState } from "react";

function stringToColor(str: string) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash) % 360;
  return `hsl(${h}, 50%, 20%)`;
}

interface PosterImageProps {
  src?: string | null;
  alt: string;
  className?: string;
  fill?: boolean;
  width?: number;
  height?: number;
  showTitleFallback?: boolean;
}

export function PosterImage({
  src,
  alt,
  className = "",
  fill = true,
  width,
  height,
  showTitleFallback = true,
}: PosterImageProps) {
  const [error, setError] = useState(false);

  const fallbackColor = stringToColor(alt);
  const fallbackGradient = `linear-gradient(135deg, ${fallbackColor}, #0a0a0f)`;

  if (!src || error) {
    return (
      <div
        className={`relative flex items-center justify-center p-4 text-center overflow-hidden ${className} bg-bg-surface`}
        style={{ background: fallbackGradient }}
      >
        {showTitleFallback && (
          <span className="text-text-primary font-bold text-shadow-md z-10 break-words line-clamp-4">
            {alt}
          </span>
        )}
        <div className="absolute inset-0 bg-black/20" />
      </div>
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      fill={fill}
      width={!fill ? width : undefined}
      height={!fill ? height : undefined}
      className={`object-cover ${className}`}
      onError={() => setError(true)}
      unoptimized // TMDB images
    />
  );
}
