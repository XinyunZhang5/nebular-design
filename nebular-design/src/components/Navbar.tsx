'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';

const LEGO_COLORS = ['#E3000B', '#006DB7', '#007934', '#FF6B00', '#9B59B6'];

function LegoStud({ color }: { color: string }) {
  return (
    <div
      className="w-5 h-5 rounded-full border-2 border-black/20 flex-shrink-0"
      style={{ background: color, boxShadow: `inset 0 -2px 4px rgba(0,0,0,0.3)` }}
    />
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<{ username: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('nebular_user');
    if (stored) setUser(JSON.parse(stored));
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem('nebular_user');
    setUser(null);
    window.location.href = '/';
  };

  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/upload', label: 'Build' },
    { href: '/chat', label: 'Community' },
    { href: '/profile', label: 'Profile' },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-lego-yellow border-b-[3px] border-lego-black">
      {/* Top stud row */}
      <div className="flex gap-2 px-6 pt-2 pb-1">
        {LEGO_COLORS.map((c, i) => (
          <LegoStud key={i} color={c} />
        ))}
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-9 h-9 bg-lego-black rounded-md flex items-center justify-center border-2 border-lego-black shadow-[2px_2px_0_#C9A800]">
            <span className="text-lego-yellow font-black text-lg leading-none">N</span>
          </div>
          <span className="font-black text-xl text-lego-black tracking-tight hidden sm:block">
            NEBULAR DESIGN
          </span>
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-1">
          {navLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all border-2 ${
                pathname === href
                  ? 'bg-lego-black text-lego-yellow border-lego-black'
                  : 'text-lego-black border-transparent hover:bg-lego-black/10 hover:border-lego-black'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Auth area */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <span className="hidden sm:flex items-center gap-2 font-bold text-sm bg-white/60 px-3 py-1.5 rounded-md border-2 border-lego-black">
                <span className="w-6 h-6 bg-lego-black rounded-full flex items-center justify-center text-lego-yellow text-xs font-black">
                  {user.username[0].toUpperCase()}
                </span>
                {user.username}
              </span>
              <button
                onClick={handleLogout}
                className="btn-lego-outline text-sm px-3 py-1.5 !text-xs font-bold"
                style={{ padding: '6px 14px', fontSize: '13px' }}
              >
                Logout
              </button>
            </div>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden sm:block font-bold text-sm text-lego-black hover:underline"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="btn-lego"
                style={{ padding: '8px 18px', fontSize: '13px' }}
              >
                Sign up free
              </Link>
            </>
          )}

          {/* Mobile menu toggle */}
          <button
            className="md:hidden p-2 border-2 border-lego-black rounded-md bg-white/50"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <div className="w-4 h-0.5 bg-lego-black mb-1" />
            <div className="w-4 h-0.5 bg-lego-black mb-1" />
            <div className="w-4 h-0.5 bg-lego-black" />
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="md:hidden border-t-2 border-lego-black bg-lego-yellow px-4 pb-4">
          {navLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="block py-2.5 font-bold text-lego-black border-b border-lego-black/20"
              onClick={() => setMenuOpen(false)}
            >
              {label}
            </Link>
          ))}
          {!user && (
            <div className="flex gap-2 mt-3">
              <Link href="/login" className="btn-lego-outline flex-1 text-center" style={{ padding: '8px', fontSize: '13px' }}>
                Log in
              </Link>
              <Link href="/register" className="btn-lego flex-1 text-center" style={{ padding: '8px', fontSize: '13px' }}>
                Sign up
              </Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
