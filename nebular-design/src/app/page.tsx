'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

const FLOATING_BRICKS = [
  { color: '#E3000B', size: 80, x: '8%', y: '20%', delay: '0s', rotate: -15 },
  { color: '#006DB7', size: 56, x: '85%', y: '15%', delay: '0.8s', rotate: 10 },
  { color: '#007934', size: 64, x: '75%', y: '60%', delay: '1.6s', rotate: -8 },
  { color: '#FF6B00', size: 48, x: '12%', y: '70%', delay: '0.4s', rotate: 20 },
  { color: '#9B59B6', size: 52, x: '90%', y: '45%', delay: '1.2s', rotate: -5 },
];

function LegoMiniBlock({ color, size, studs = 2 }: { color: string; size: number; studs?: number }) {
  return (
    <div
      className="relative"
      style={{
        width: size,
        height: size * 0.625,
        background: color,
        borderRadius: 5,
        border: '2.5px solid rgba(0,0,0,0.35)',
        boxShadow: `3px 3px 0 rgba(0,0,0,0.35), inset 0 -4px 0 rgba(0,0,0,0.15)`,
      }}
    >
      {/* Studs */}
      <div className="absolute -top-[9px] left-0 right-0 flex justify-evenly">
        {Array.from({ length: studs }).map((_, i) => (
          <div
            key={i}
            style={{
              width: size * 0.28,
              height: size * 0.28,
              background: color,
              borderRadius: '50%',
              border: '2px solid rgba(0,0,0,0.3)',
              boxShadow: `inset 0 -2px 3px rgba(0,0,0,0.2)`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

const STEPS = [
  {
    number: '01',
    title: 'Upload Your Photo',
    description: 'Take a photo of any building, structure, or design. Drag it in or browse your files.',
    color: '#E3000B',
    icon: '📸',
  },
  {
    number: '02',
    title: 'AI Analyzes & Matches',
    description: 'Our AI engine breaks down the geometry and matches every part to real LEGO brick types.',
    color: '#006DB7',
    icon: '🧠',
  },
  {
    number: '03',
    title: 'Build Step by Step',
    description: 'Get your full brick list plus clear assembly instructions. Start building!',
    color: '#007934',
    icon: '🏗️',
  },
];

const GALLERY = [
  { title: 'Empire State Building', pieces: 847, difficulty: 'Expert', color: '#E3000B', emoji: '🏙️' },
  { title: 'Sydney Opera House', pieces: 623, difficulty: 'Hard', color: '#006DB7', emoji: '🏛️' },
  { title: 'Eiffel Tower', pieces: 412, difficulty: 'Medium', color: '#007934', emoji: '🗼' },
  { title: 'Big Ben', pieces: 534, difficulty: 'Hard', color: '#FF6B00', emoji: '🕰️' },
];

export default function HomePage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="bg-lego-bg">
      {/* HERO */}
      <section className="relative overflow-hidden lego-stud-bg min-h-[80vh] flex items-center">
        {/* Floating bricks — only render after mount to avoid hydration mismatch */}
        {mounted && FLOATING_BRICKS.map((b, i) => (
          <div
            key={i}
            className="absolute hidden lg:block pointer-events-none"
            style={{
              left: b.x,
              top: b.y,
              transform: `rotate(${b.rotate}deg)`,
              animation: `float 4s ease-in-out ${b.delay} infinite`,
              opacity: 0.85,
            }}
          >
            <LegoMiniBlock color={b.color} size={b.size} studs={b.size > 60 ? 4 : 2} />
          </div>
        ))}

        <div className="relative z-10 max-w-6xl mx-auto px-6 py-20 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 lego-badge mb-8">
            <span>🧱</span>
            <span>AI-Powered LEGO Creator</span>
          </div>

          {/* Headline */}
          <h1
            className="font-black text-lego-black mb-6 leading-none"
            style={{ fontSize: 'clamp(2.8rem, 7vw, 5.5rem)', letterSpacing: '-0.03em' }}
          >
            Turn Any Building
            <br />
            <span
              className="relative inline-block px-3 py-1 mx-2"
              style={{
                background: '#F7D117',
                border: '3px solid #1C1C1C',
                boxShadow: '6px 6px 0 #1C1C1C',
              }}
            >
              Into LEGO
            </span>
            <br />
            Masterpiece
          </h1>

          <p className="text-lego-dark-gray text-xl font-semibold max-w-xl mx-auto mb-10">
            Upload a photo. Our AI breaks it into real LEGO bricks.<br className="hidden sm:block" />
            Get the piece list and start building.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link href="/upload" className="btn-lego text-base px-8 py-4">
              🚀 Start Building
            </Link>
            <Link href="/chat" className="btn-lego-outline text-base px-8 py-4">
              💬 Join Community
            </Link>
          </div>

          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-8 mt-16">
            {[
              { label: 'Builds Created', value: '2,400+' },
              { label: 'LEGO Parts in DB', value: '15,000+' },
              { label: 'Builders Online', value: '320' },
            ].map(({ label, value }) => (
              <div key={label} className="lego-card px-6 py-4 text-center" style={{ minWidth: 130 }}>
                <div className="font-black text-2xl text-lego-black">{value}</div>
                <div className="text-sm font-semibold text-lego-dark-gray mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <span className="lego-badge mb-4">How It Works</span>
          <h2 className="section-title mt-4">
            Three Steps to Your<br />LEGO Dream Build
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {STEPS.map((step, i) => (
            <div
              key={i}
              className="lego-card p-6 relative group"
              style={{ '--card-accent': step.color } as React.CSSProperties}
            >
              {/* Step number */}
              <div
                className="w-12 h-12 rounded-md flex items-center justify-center font-black text-white text-lg mb-4 border-2 border-lego-black"
                style={{ background: step.color, boxShadow: '3px 3px 0 #1C1C1C' }}
              >
                {step.number}
              </div>

              {/* Icon */}
              <div className="text-4xl mb-3">{step.icon}</div>

              <h3 className="font-black text-xl text-lego-black mb-2">{step.title}</h3>
              <p className="text-lego-dark-gray font-semibold leading-relaxed">{step.description}</p>

              {/* Connector dot */}
              {i < STEPS.length - 1 && (
                <div className="hidden md:block absolute -right-5 top-1/2 -translate-y-1/2 z-10">
                  <div className="w-8 h-8 rounded-full bg-lego-yellow border-2 border-lego-black flex items-center justify-center font-black text-xs">
                    →
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* GALLERY PREVIEW */}
      <section className="lego-stud-bg py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <span className="lego-badge mb-4">Featured Builds</span>
            <h2 className="section-title mt-4">
              See What Others<br />Are Building
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {GALLERY.map((item, i) => (
              <div key={i} className="lego-card overflow-hidden cursor-pointer group">
                {/* Image placeholder */}
                <div
                  className="h-40 flex items-center justify-center relative"
                  style={{ background: `${item.color}22`, borderBottom: '2.5px solid #1C1C1C' }}
                >
                  <span className="text-6xl">{item.emoji}</span>
                  <div className="absolute top-2 right-2">
                    <span
                      className="lego-badge"
                      style={{
                        background: item.color,
                        color: '#fff',
                        borderColor: '#1C1C1C',
                        fontSize: 11,
                        padding: '2px 8px',
                      }}
                    >
                      {item.difficulty}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <h4 className="font-black text-lego-black">{item.title}</h4>
                  <p className="text-lego-dark-gray text-sm font-semibold mt-1">
                    🧱 {item.pieces} pieces
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center mt-10">
            <Link href="/upload" className="btn-lego text-base px-8 py-4">
              🧱 Create Your Own Build →
            </Link>
          </div>
        </div>
      </section>

      {/* COMMUNITY CTA */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div
          className="rounded-xl p-10 md:p-16 text-center relative overflow-hidden border-[3px] border-lego-black"
          style={{
            background: '#1C1C1C',
            boxShadow: '8px 8px 0 #F7D117',
          }}
        >
          {/* Background studs */}
          <div className="absolute inset-0 opacity-5 pointer-events-none"
            style={{
              backgroundImage: 'radial-gradient(circle, white 2px, transparent 2px)',
              backgroundSize: '28px 28px',
            }}
          />

          <div className="relative z-10">
            <span className="lego-badge mb-6 inline-flex">👥 Community</span>
            <h2 className="section-title text-lego-yellow mb-4">
              Find Your Fellow<br />Brick Builders
            </h2>
            <p className="text-lego-gray text-lg font-semibold max-w-lg mx-auto mb-8">
              Chat in real-time, share your builds, make friends who love LEGO as much as you do.
            </p>
            <Link href="/chat" className="btn-lego text-base px-10 py-4">
              💬 Open Chat Room
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t-[3px] border-lego-black bg-lego-yellow">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-lego-black rounded flex items-center justify-center border-2 border-lego-black">
              <span className="text-lego-yellow font-black text-sm">N</span>
            </div>
            <span className="font-black text-lego-black">NEBULAR DESIGN</span>
          </div>
          <p className="text-lego-black font-semibold text-sm">
            Built with ❤️ for LEGO enthusiasts everywhere
          </p>
          <div className="flex gap-4">
            <Link href="/upload" className="text-lego-black font-bold text-sm hover:underline">Build</Link>
            <Link href="/chat" className="text-lego-black font-bold text-sm hover:underline">Community</Link>
            <Link href="/register" className="text-lego-black font-bold text-sm hover:underline">Sign Up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
