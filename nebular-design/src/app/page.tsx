'use client';

import Link from 'next/link';
import { ArrowRight, ArrowUpRight } from 'lucide-react';
import { BrickStack, G, WALL, type BrickSpec } from '@/components/Bricks';

/* ---------- content ---------- */

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
  { title: 'Empire State Building', pieces: 847, difficulty: 'Expert', img: '/gallery/empire-state.webp' },
  { title: 'Sydney Opera House', pieces: 623, difficulty: 'Hard', img: '/gallery/sydney-opera.webp' },
  { title: 'Eiffel Tower', pieces: 412, difficulty: 'Medium', img: '/gallery/eiffel-tower.webp' },
  { title: 'Big Ben', pieces: 534, difficulty: 'Hard', img: '/gallery/big-ben.webp' },
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
                  src={item.img}
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
