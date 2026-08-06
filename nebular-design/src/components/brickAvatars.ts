import { WALL, type BrickSpec } from './Bricks';

/**
 * Avatar data and geometry, deliberately kept out of the `'use client'` module.
 *
 * A client module only exposes component references across the server boundary —
 * plain exports like an array arrive as an unusable proxy, so importing
 * AVATAR_KEYS from BrickAvatar.tsx into a server component fails at runtime with
 * "map is not a function". Keeping the data here means either side can read it.
 */

export const AVATAR_KEYS = ['🟡', '🔵', '🟢', '🔴', '🟠', '🟣', '⚫', '🟤'] as const;
export type AvatarKey = (typeof AVATAR_KEYS)[number];

export type Colour = { from: string; to: string };

/** Light-to-saturated pairs, matching the convention in Bricks' G palette. */
export const PALETTE: Record<string, Colour> = {
  '🟡': { from: '#FCE181', to: '#F6C846' },
  '🔵': { from: '#8FC4F0', to: '#3F7ED4' },
  '🟢': { from: '#A8DFA0', to: '#4FA855' },
  '🔴': { from: '#F6A79C', to: '#DC4B3E' },
  '🟠': { from: '#FBCF92', to: '#EE9A2C' },
  '🟣': { from: '#D6BCF5', to: '#9E5FDE' },
  '⚫': { from: '#7A7D84', to: '#2B2D33' },
  '🟤': { from: '#C9A484', to: '#8B5A36' },
};

/** Nudge a hex toward black, so two bricks of one colour still read as two bricks. */
function darken(hex: string, amount: number) {
  const n = parseInt(hex.slice(1), 16);
  const f = 1 - amount;
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) =>
    Math.round(v * f).toString(16).padStart(2, '0'),
  );
  return `#${c.join('')}`;
}

const second = (c: Colour, amount: number): Colour => ({
  from: darken(c.from, amount),
  to: darken(c.to, amount),
});

/**
 * One silhouette per avatar, all on a 2x2 footprint so the auto-fitted viewBox
 * scales them alike in a row. Each follows the idiom already used on the upload
 * and profile pages: a base brick with a smaller topper offset by half a stud,
 * or a pair of bars on a single level.
 */
export const SHAPES: Record<string, (c: Colour) => BrickSpec[]> = {
  // The archetype: one clean 2x2.
  '🟡': (c) => [{ ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...c }],

  // Tower — the tallest silhouette in the set.
  '🔵': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...c },
    { ox: 0, oy: 0, oz: WALL, w: 2, d: 2, ...second(c, 0.07) },
  ],

  // Half cap running across.
  '🟢': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...c },
    { ox: 0, oy: 0.5, oz: WALL, w: 2, d: 1, ...second(c, 0.06) },
  ],

  // Half cap the other way round.
  '🔴': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...c },
    { ox: 0.5, oy: 0, oz: WALL, w: 1, d: 2, ...second(c, 0.06) },
  ],

  // Two bars laid side by side on one level.
  '🟠': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 2, d: 1, ...c },
    { ox: 0, oy: 1, oz: 0, w: 2, d: 1, ...second(c, 0.09) },
  ],

  // Single stud perched on a corner.
  '🟣': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...c },
    { ox: 0, oy: 0, oz: WALL, w: 1, d: 1, ...second(c, 0.06) },
  ],

  // Centred stud — the classic topper.
  '⚫': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...c },
    { ox: 0.5, oy: 0.5, oz: WALL, w: 1, d: 1, ...second(c, 0.05) },
  ],

  // Two bars stood the other way.
  '🟤': (c) => [
    { ox: 0, oy: 0, oz: 0, w: 1, d: 2, ...c },
    { ox: 1, oy: 0, oz: 0, w: 1, d: 2, ...second(c, 0.09) },
  ],
};

export const FALLBACK_KEY: AvatarKey = '🟡';

export function bricksFor(avatar: string): BrickSpec[] {
  const colour = PALETTE[avatar] ?? PALETTE[FALLBACK_KEY];
  const build = SHAPES[avatar] ?? SHAPES[FALLBACK_KEY];
  return build(colour);
}
