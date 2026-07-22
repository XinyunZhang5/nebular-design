'use client';

import Link from 'next/link';
import { ArrowRight, ArrowUpRight } from 'lucide-react';

/* ---------- Isometric brick with grainy-gradient skin ---------- */

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
const WALL = 1.15;
const STUD_H = 0.36;
const STUD_R = 0.33;

function proj(x: number, y: number, z: number, unit: number): [number, number] {
  return [(x - y) * ISO_COS * unit, (x + y) * ISO_SIN * unit - z * unit];
}

type BrickSpec = { ox: number; oy: number; oz: number; w: number; d: number; from: string; to: string; opacity?: number };

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

function BrickStack({
  bricks,
  unit = 60,
  ns,
  className = '',
  style,
}: {
  bricks: BrickSpec[];
  unit?: number;
  ns: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const order = bricks
    .map((b, i) => ({ b, i }))
    .sort((a, z) => a.b.oz - z.b.oz || a.b.ox + a.b.oy - (z.b.ox + z.b.oy));
  const allPts = bricks.flatMap((b) => brickExtent(b, unit));
  const xs = allPts.map((p) => p[0]);
  const ys = allPts.map((p) => p[1]);
  const pad = unit * 0.65;
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

/* ---------- content ---------- */

const G = {
  yellow: { from: '#FCE181', to: '#F6C846' },
  coral: { from: '#FBC0A6', to: '#F89A93' },
  sky: { from: '#B4DEF3', to: '#84C6EC' },
  lilac: { from: '#D3CEF5', to: '#B4ABE8' },
};

const HERO_BRICKS: BrickSpec[] = [
  { ox: 0, oy: 0, oz: 0, w: 4, d: 2, ...G.lilac },
  { ox: 0, oy: 0.5, oz: WALL, w: 2, d: 1, ...G.sky },
  { ox: 2, oy: 0.5, oz: WALL, w: 2, d: 1, ...G.coral },
  { ox: 1, oy: 0.5, oz: WALL * 2, w: 2, d: 1, ...G.yellow },
];

const STEPS = [
  { title: 'Photograph it', description: 'Snap any building or structure, or drop in a photo you already have.', g: G.yellow },
  { title: 'AI maps the bricks', description: 'The engine reads the geometry and matches every part to a real LEGO piece.', g: G.sky },
  { title: 'Build it for real', description: 'Get the full parts list plus step-by-step instructions, then start clicking bricks.', g: G.coral },
];

const GALLERY = [
  { title: 'Empire State Building', pieces: 847, difficulty: 'Expert', seed: 'empire-state-skyscraper-newyork' },
  { title: 'Sydney Opera House', pieces: 623, difficulty: 'Hard', seed: 'sydney-opera-house-harbour' },
  { title: 'Eiffel Tower', pieces: 412, difficulty: 'Medium', seed: 'eiffel-tower-paris-sky' },
  { title: 'Big Ben', pieces: 534, difficulty: 'Hard', seed: 'big-ben-london-clocktower' },
];

export default function HomePage() {
  return (
    <div className="bg-lego-bg">
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="max-w-6xl mx-auto px-6 min-h-[calc(100dvh-4rem)] grid lg:grid-cols-[1fr_1.05fr] gap-8 items-center">
          <div className="animate-fade-up py-14 lg:py-0 order-2 lg:order-1">
            <div className="eyebrow-min mb-6">AI LEGO studio</div>
            <h1 className="display-xl text-lego-black mb-7" style={{ fontSize: 'clamp(2.7rem, 5.6vw, 4.6rem)' }}>
              Any building,
              <br />
              rebuilt in bricks.
            </h1>
            <p className="text-lego-dark-gray text-lg font-medium max-w-md mb-10 leading-relaxed">
              Photograph a structure. Our AI rebuilds it from real LEGO parts and hands you the blueprint.
            </p>
            <div className="flex flex-wrap items-center gap-x-7 gap-y-4">
              <Link href="/upload" className="btn-pill">
                Start building
                <ArrowRight size={18} strokeWidth={2.4} />
              </Link>
              <Link href="/chat" className="btn-ghost">
                Explore community
                <ArrowUpRight size={16} strokeWidth={2.4} />
              </Link>
            </div>
          </div>

          <div className="relative h-[340px] sm:h-[440px] lg:h-[560px] order-1 lg:order-2 flex items-center justify-center">
            <BrickStack ns="hero" bricks={HERO_BRICKS} unit={62} className="brick-shadow animate-drift w-[92%] max-w-[560px] h-auto" />
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="max-w-6xl mx-auto px-6 py-28">
        <div className="max-w-xl mb-16">
          <h2 className="display-xl text-lego-black" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
            From a photo to
            <br />
            a finished build.
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-x-10 gap-y-14">
          {STEPS.map((step, i) => (
            <div key={i} className="animate-fade-up" style={{ animationDelay: `${i * 0.08}s` }}>
              <BrickStack
                ns={`step${i}`}
                bricks={[{ ox: 0, oy: 0, oz: 0, w: 2, d: 1, ...step.g }]}
                unit={38}
                className="w-20 h-auto mb-7 brick-shadow"
              />
              <div className="text-sm font-bold text-lego-gray mb-2">0{i + 1}</div>
              <h3 className="font-extrabold text-xl text-lego-black mb-2.5">{step.title}</h3>
              <p className="text-lego-dark-gray font-medium leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* GALLERY */}
      <section className="max-w-6xl mx-auto px-6 py-24 border-t hairline">
        <div className="mb-14 max-w-xl">
          <h2 className="display-xl text-lego-black" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
            See what others
            <br />
            are building.
          </h2>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
          {GALLERY.map((item, i) => (
            <div key={i} className="group">
              <div
                className="relative rounded-2xl overflow-hidden aspect-[4/5] mb-3.5"
                style={{ boxShadow: '0 22px 34px rgba(28,28,28,0.09)' }}
              >
                <img
                  src={`https://picsum.photos/seed/${item.seed}/600/750`}
                  alt={item.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  loading="lazy"
                />
                <span className="absolute top-3 left-3 text-[11px] font-bold px-2.5 py-1 rounded-full bg-white/90 backdrop-blur text-lego-black">
                  {item.difficulty}
                </span>
              </div>
              <h4 className="font-bold text-lego-black">{item.title}</h4>
              <p className="text-sm text-lego-gray font-medium mt-0.5">{item.pieces} pieces</p>
            </div>
          ))}
        </div>
      </section>

      {/* COMMUNITY */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="relative overflow-hidden rounded-[32px] bg-lego-black px-8 md:px-16 py-16 md:py-24">
          <div className="relative z-10 max-w-lg">
            <h2 className="display-xl text-white mb-5" style={{ fontSize: 'clamp(1.9rem, 3.6vw, 2.8rem)' }}>
              Find your fellow
              <br />
              brick builders.
            </h2>
            <p className="text-white/55 text-lg font-medium mb-9 leading-relaxed">
              Chat in real time, share your builds, and meet people who love LEGO as much as you do.
            </p>
            <Link href="/chat" className="btn-pill btn-pill-yellow">
              Open chat room
              <ArrowRight size={18} strokeWidth={2.4} />
            </Link>
          </div>
          <BrickStack
            ns="cta"
            bricks={[
              { ox: 0, oy: 0, oz: 0, w: 3, d: 2, ...G.sky },
              { ox: 0.5, oy: 0.5, oz: WALL, w: 2, d: 1, ...G.yellow },
            ]}
            unit={52}
            className="hidden md:block absolute right-4 lg:right-14 bottom-[-10%] w-[40%] max-w-[340px] h-auto animate-drift"
          />
        </div>
      </section>

      {/* FOOTER */}
      <footer className="max-w-6xl mx-auto px-6 py-12 border-t hairline flex flex-col sm:flex-row justify-between items-center gap-5">
        <div className="flex items-center gap-2.5">
          <span
            className="w-7 h-7 rounded-[7px] bg-lego-yellow flex items-center justify-center"
            style={{ boxShadow: 'inset 0 -3px 0 rgba(0,0,0,0.14)' }}
          >
            <span className="font-black text-sm text-lego-black leading-none">N</span>
          </span>
          <span className="font-extrabold text-lego-black">nebular</span>
        </div>
        <p className="text-sm text-lego-gray font-medium">Built for LEGO enthusiasts everywhere</p>
        <div className="flex gap-6 text-sm font-semibold text-lego-black/50">
          <Link href="/upload" className="hover:text-lego-black transition-colors">Build</Link>
          <Link href="/chat" className="hover:text-lego-black transition-colors">Community</Link>
          <Link href="/register" className="hover:text-lego-black transition-colors">Sign up</Link>
        </div>
      </footer>
    </div>
  );
}
