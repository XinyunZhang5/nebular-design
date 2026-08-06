'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<{ username: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('nebular_user');
    if (stored) setUser(JSON.parse(stored));
  }, [pathname]);

  const handleLogout = () => {
    // Both keys. Removing only the profile made the UI look logged out while the
    // bearer token stayed in localStorage — so on a shared machine the next
    // person could read it out of devtools and keep using the account for the
    // remaining seven days, and every API call this tab made afterwards was
    // still authenticated.
    localStorage.removeItem('nebular_user');
    localStorage.removeItem('nebular_token');
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
    <nav className="sticky top-0 z-50 bg-[#F3F2EE]/75 backdrop-blur-md border-b hairline">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo — kept: yellow N brick + wordmark */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <span
            className="w-7 h-7 rounded-[7px] bg-lego-yellow flex items-center justify-center transition-transform group-hover:-rotate-6"
            style={{ boxShadow: 'inset 0 -3px 0 rgba(0,0,0,0.14), 0 2px 6px rgba(0,0,0,0.12)' }}
          >
            <span className="font-black text-sm text-lego-black leading-none">N</span>
          </span>
          <span className="font-extrabold text-lg tracking-tight text-lego-black">nebular</span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-9 absolute left-1/2 -translate-x-1/2">
          {navLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm font-semibold transition-colors ${
                pathname === href ? 'text-lego-black' : 'text-lego-black/45 hover:text-lego-black'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Auth */}
        <div className="flex items-center gap-4">
          {user ? (
            <div className="flex items-center gap-3">
              <span className="hidden sm:flex items-center gap-2 font-semibold text-sm">
                <span className="w-7 h-7 bg-lego-black rounded-full flex items-center justify-center text-lego-yellow text-xs font-black">
                  {user.username[0].toUpperCase()}
                </span>
                {user.username}
              </span>
              <button onClick={handleLogout} className="text-sm font-semibold text-lego-black/45 hover:text-lego-black">
                Log out
              </button>
            </div>
          ) : (
            <>
              <Link href="/login" className="hidden sm:block text-sm font-semibold text-lego-black/45 hover:text-lego-black">
                Log in
              </Link>
              <Link href="/register" className="btn-pill-yellow btn-pill !py-2.5 !px-5 !text-sm">
                Sign up
              </Link>
            </>
          )}

          <button
            className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg hover:bg-black/5"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t hairline bg-[#F3F2EE] px-6 py-4">
          {navLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="block py-2.5 font-semibold text-lego-black"
              onClick={() => setMenuOpen(false)}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
