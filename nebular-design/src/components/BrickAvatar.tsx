'use client';

import { useId } from 'react';
import { BrickStack } from './Bricks';
import { bricksFor } from './brickAvatars';

/**
 * Avatars as isometric bricks, drawn with the same renderer as every other brick
 * in the product so they carry the same grain, shading and light angle.
 *
 * The stored value stays the emoji it always was ('🟡', '🔵', …). Existing
 * accounts keep their avatar and nothing needs migrating — only the rendering
 * changed.
 *
 * Data and geometry live in ./brickAvatars so server components can import them;
 * see the note there about the client boundary.
 */
export default function BrickAvatar({
  avatar,
  size = 44,
  className = '',
  shadow = true,
}: {
  avatar: string;
  size?: number;
  className?: string;
  shadow?: boolean;
}) {
  // Gradient and clip-path ids are document-global in SVG. The same avatar can
  // appear dozens of times in a chat log, so every instance needs its own
  // namespace or they all inherit the first one's colour.
  const ns = useId().replace(/:/g, '');

  return (
    <BrickStack
      ns={`av-${ns}`}
      bricks={bricksFor(avatar)}
      unit={30}
      padScale={0.16}
      className={className}
      style={{
        width: size,
        height: size,
        flexShrink: 0,
        // The global .brick-shadow is tuned for hero bricks (34px offset) and
        // smears into a blob at avatar scale, so the offset tracks the size.
        filter: shadow
          ? `drop-shadow(0 ${(size * 0.09).toFixed(1)}px ${(size * 0.11).toFixed(1)}px rgba(28,28,28,0.20))`
          : undefined,
      }}
    />
  );
}
