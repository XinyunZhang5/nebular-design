/* ---------- Isometric brick with grainy-gradient skin ----------
   Shared signature visual. Used on home + Build / Community / Profile
   so every page reads as the same product. Pure deterministic SVG,
   no hooks, no randomness. */

function shade(hex: string, amt: number) {
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 255;
  let g = (n >> 8) & 255;
  let b = n & 255;
  if (amt >= 0) {
    r += (255 - r) * amt;
    g += (255 - g) * amt;
    b += (255 - b) * amt;
  } else {
    const f = 1 + amt;
    r *= f;
    g *= f;
    b *= f;
  }
  const h = (v: number) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0');
  return `#${h(r)}${h(g)}${h(b)}`;
}

const ISO_A = Math.PI / 6;
const ISO_COS = Math.cos(ISO_A);
const ISO_SIN = Math.sin(ISO_A);
export const WALL = 1.15;
const STUD_H = 0.36;
const STUD_R = 0.33;

function proj(x: number, y: number, z: number, unit: number): [number, number] {
  return [(x - y) * ISO_COS * unit, (x + y) * ISO_SIN * unit - z * unit];
}

export type BrickSpec = { ox: number; oy: number; oz: number; w: number; d: number; from: string; to: string; opacity?: number };

/* Shared gradient palette — the four brick colours used across the app. */
export const G = {
  yellow: { from: '#FCE181', to: '#F6C846' },
  coral: { from: '#FBC0A6', to: '#F89A93' },
  sky: { from: '#B4DEF3', to: '#84C6EC' },
  lilac: { from: '#D3CEF5', to: '#B4ABE8' },
};

function BrickBody({ spec, unit, gid, grainId }: { spec: BrickSpec; unit: number; gid: string; grainId: string }) {
  const { ox, oy, oz, w, d, from, to, opacity = 0.98 } = spec;
  const P = (x: number, y: number, z: number): [number, number] => proj(ox + x, oy + y, oz + z, unit);

  const c0 = P(0, 0, WALL);
  const c1 = P(w, 0, WALL);
  const c2 = P(w, d, WALL);
  const c3 = P(0, d, WALL);
  const top = [c0, c1, c2, c3];
  const right = [P(w, 0, WALL), P(w, d, WALL), P(w, d, 0), P(w, 0, 0)];
  const left = [P(0, d, WALL), P(w, d, WALL), P(w, d, 0), P(0, d, 0)];

  const rx = STUD_R * Math.SQRT2 * ISO_COS * unit;
  const ry = STUD_R * Math.SQRT2 * ISO_SIN * unit;
  const studs: { bx: number; by: number; tx: number; ty: number }[] = [];
  for (let i = 0; i < w; i++) {
    for (let j = 0; j < d; j++) {
      const b = P(i + 0.5, j + 0.5, WALL);
      const t = P(i + 0.5, j + 0.5, WALL + STUD_H);
      studs.push({ bx: b[0], by: b[1], tx: t[0], ty: t[1] });
    }
  }

  const facePts = [...top, ...right, ...left];
  const fxs = facePts.map((p) => p[0]);
  const fys = facePts.map((p) => p[1]);
  const bx0 = Math.min(...fxs);
  const by0 = Math.min(...fys) - ry * 1.6;
  const bw = Math.max(...fxs) - bx0;
  const bh = Math.max(...fys) - by0 + ry;

  const leftFrom = shade(from, -0.16);
  const leftTo = shade(to, -0.16);
  const rightFrom = shade(from, -0.31);
  const rightTo = shade(to, -0.31);
  const discFrom = shade(from, 0.16);
  const discTo = shade(to, 0.06);
  const wallFrom = shade(from, -0.25);
  const wallTo = shade(to, -0.25);
  const ao = shade(to, -0.4);

  const pts = (a: [number, number][]) => a.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const g = gid;
  const grainRect = (
    <rect
      x={bx0.toFixed(1)}
      y={by0.toFixed(1)}
      width={bw.toFixed(1)}
      height={bh.toFixed(1)}
      filter={`url(#${grainId})`}
      opacity="0.5"
      style={{ mixBlendMode: 'overlay' }}
    />
  );

  return (
    <g opacity={opacity}>
      <defs>
        <linearGradient id={`${g}-top`} gradientUnits="userSpaceOnUse" x1={c0[0].toFixed(1)} y1={c0[1].toFixed(1)} x2={c2[0].toFixed(1)} y2={c2[1].toFixed(1)}>
          <stop offset="0" stopColor={from} />
          <stop offset="1" stopColor={to} />
        </linearGradient>
        <linearGradient id={`${g}-left`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={leftFrom} />
          <stop offset="1" stopColor={leftTo} />
        </linearGradient>
        <linearGradient id={`${g}-right`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={rightFrom} />
          <stop offset="1" stopColor={rightTo} />
        </linearGradient>
        <linearGradient id={`${g}-disc`} x1="0.2" y1="0" x2="0.7" y2="1">
          <stop offset="0" stopColor={discFrom} />
          <stop offset="1" stopColor={discTo} />
        </linearGradient>
        <linearGradient id={`${g}-wall`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={wallFrom} />
          <stop offset="1" stopColor={wallTo} />
        </linearGradient>
        <clipPath id={`${g}-ct`}>
          <polygon points={pts(top)} />
        </clipPath>
        <clipPath id={`${g}-cl`}>
          <polygon points={pts(left)} />
        </clipPath>
        <clipPath id={`${g}-cr`}>
          <polygon points={pts(right)} />
        </clipPath>
      </defs>

      <g clipPath={`url(#${g}-cr)`} style={{ isolation: 'isolate' }}>
        <polygon points={pts(right)} fill={`url(#${g}-right)`} />
        {grainRect}
      </g>

      <g clipPath={`url(#${g}-cl)`} style={{ isolation: 'isolate' }}>
        <polygon points={pts(left)} fill={`url(#${g}-left)`} />
        {grainRect}
      </g>

      <g clipPath={`url(#${g}-ct)`} style={{ isolation: 'isolate' }}>
        <polygon points={pts(top)} fill={`url(#${g}-top)`} />
        {studs.map((s, i) => (
          <ellipse key={i} cx={s.bx.toFixed(1)} cy={s.by.toFixed(1)} rx={(rx * 1.5).toFixed(1)} ry={(ry * 1.5).toFixed(1)} fill={ao} opacity="0.3" style={{ mixBlendMode: 'multiply' }} />
        ))}
        {grainRect}
      </g>

      {studs.map((s, i) => (
        <g key={i}>
          <path
            d={`M ${(s.tx - rx).toFixed(1)} ${s.ty.toFixed(1)} L ${(s.bx - rx).toFixed(1)} ${s.by.toFixed(1)} A ${rx.toFixed(1)} ${ry.toFixed(1)} 0 0 0 ${(s.bx + rx).toFixed(1)} ${s.by.toFixed(1)} L ${(s.tx + rx).toFixed(1)} ${s.ty.toFixed(1)} Z`}
            fill={`url(#${g}-wall)`}
          />
          <ellipse cx={s.tx.toFixed(1)} cy={s.ty.toFixed(1)} rx={rx.toFixed(1)} ry={ry.toFixed(1)} fill={`url(#${g}-disc)`} />
        </g>
      ))}
    </g>
  );
}

function brickExtent(spec: BrickSpec, unit: number): [number, number][] {
  const { ox, oy, oz, w, d } = spec;
  const pts: [number, number][] = [];
  for (const z of [oz, oz + WALL + STUD_H]) {
    for (const x of [ox, ox + w]) {
      for (const y of [oy, oy + d]) {
        pts.push(proj(x, y, z, unit));
      }
    }
  }
  return pts;
}

export function BrickStack({
  bricks,
  unit = 60,
  ns,
  className = '',
  style,
  padScale = 0.65,
}: {
  bricks: BrickSpec[];
  unit?: number;
  ns: string;
  className?: string;
  style?: React.CSSProperties;
  /** Breathing room around the stack, as a multiple of `unit`. The default suits
   *  hero marks that float on a page; small fixed-size uses like avatars want
   *  much less, or the brick shrinks to a dot inside its box. */
  padScale?: number;
}) {
  const order = bricks
    .map((b, i) => ({ b, i }))
    .sort((a, z) => a.b.oz - z.b.oz || a.b.ox + a.b.oy - (z.b.ox + z.b.oy));
  const allPts = bricks.flatMap((b) => brickExtent(b, unit));
  const xs = allPts.map((p) => p[0]);
  const ys = allPts.map((p) => p[1]);
  const pad = unit * padScale;
  const minX = Math.min(...xs) - pad;
  const minY = Math.min(...ys) - pad;
  const vbW = Math.max(...xs) - minX + pad;
  const vbH = Math.max(...ys) - minY + pad;
  const grainId = `grain-${ns}`;
  return (
    <svg
      className={className}
      style={style}
      viewBox={`${minX.toFixed(1)} ${minY.toFixed(1)} ${vbW.toFixed(1)} ${vbH.toFixed(1)}`}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <filter id={grainId} x="0%" y="0%" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" result="n" />
          <feColorMatrix in="n" type="saturate" values="0" />
        </filter>
      </defs>
      {order.map(({ b, i }) => (
        <BrickBody key={i} spec={b} unit={unit} gid={`${ns}-${i}`} grainId={grainId} />
      ))}
    </svg>
  );
}
