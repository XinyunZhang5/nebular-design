'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { BrickStack, G } from '@/components/Bricks';
import BrickAvatar from '@/components/BrickAvatar';
import { AVATAR_KEYS } from '@/components/brickAvatars';
import { CircleAlert, Eye, EyeOff, Loader2, ArrowRight } from 'lucide-react';

const AVATARS = AVATAR_KEYS;

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [avatar, setAvatar] = useState('🟡');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    // Has to match schemas.py's MIN_PASSWORD. When the backend went from six to
    // eight, this stayed at six — so a seven-character password passed the form,
    // went to the server, and came back a 422 the page had no wording for.
    if (form.password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      const data = await api.auth.register({ ...form, avatar });
      localStorage.setItem('nebular_token', data.access_token);
      localStorage.setItem('nebular_user', JSON.stringify(data.user));
      router.push('/upload');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center bg-lego-bg px-6 py-16">
      <div className="w-full max-w-md animate-fade-up">
        <div className="card-soft p-8 sm:p-10">
          <div className="text-center mb-8">
            <BrickStack
              ns="register-mark"
              bricks={[
                { ox: 0, oy: 0, oz: 0, w: 2, d: 1, ...G.sky },
                { ox: 0.5, oy: 0, oz: 1.15, w: 1, d: 1, ...G.yellow },
              ]}
              unit={30}
              className="w-16 h-auto mx-auto mb-6 brick-shadow"
            />
            <h1 className="display-xl text-lego-black" style={{ fontSize: 'clamp(1.9rem, 4vw, 2.4rem)' }}>
              Join the builders.
            </h1>
            <p className="text-lego-dark-gray font-medium mt-2">Create your free account.</p>
          </div>

          {error && (
            <div className="mb-6 flex items-center gap-2.5 px-4 py-3 rounded-2xl font-semibold text-sm"
              style={{ background: 'rgba(227,0,11,0.08)', color: '#E3000B' }}>
              <CircleAlert size={16} strokeWidth={2.2} className="flex-shrink-0" /> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex flex-col gap-2.5">
              <label className="font-bold text-sm text-lego-black">Choose your avatar</label>
              <div className="flex flex-wrap gap-2.5">
                {AVATARS.map(a => {
                  const on = avatar === a;
                  return (
                    <button key={a} type="button" onClick={() => setAvatar(a)}
                      className="group relative w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-200 ease-out"
                      style={{
                        background: on ? 'rgba(247,209,23,0.92)' : 'rgba(28,28,28,0.045)',
                        boxShadow: on ? 'inset 0 0 0 2px #1C1C1C' : 'inset 0 0 0 1px rgba(28,28,28,0.06)',
                      }}
                      aria-label={`Avatar ${a}`} aria-pressed={on}>
                      <BrickAvatar
                        avatar={a}
                        size={40}
                        shadow={false}
                        // Lifting the brick rather than the tile keeps the tray
                        // still and makes the selected piece read as picked up.
                        className={`transition-transform duration-200 ease-out ${
                          on ? '-translate-y-1 scale-105' : 'group-hover:-translate-y-0.5'
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="username" className="font-bold text-sm text-lego-black">Username</label>
              <input id="username" type="text" required minLength={3} maxLength={20} className="input-soft"
                placeholder="BrickMaster99" value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })} />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="email" className="font-bold text-sm text-lego-black">Email</label>
              <input id="email" type="email" required className="input-soft" placeholder="you@example.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="password" className="font-bold text-sm text-lego-black">Password</label>
              <div className="relative">
                <input id="password" type={showPw ? 'text' : 'password'} required minLength={8} className="input-soft pr-12"
                  placeholder="At least 8 characters" value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })} />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg text-lego-gray hover:text-lego-black hover:bg-black/5 transition-colors"
                  aria-label={showPw ? 'Hide password' : 'Show password'}>
                  {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-pill w-full justify-center !py-3.5 disabled:opacity-50 disabled:pointer-events-none">
              {loading ? <><Loader2 size={17} className="animate-spin" /> Creating account…</> : <>Create account <ArrowRight size={17} strokeWidth={2.4} /></>}
            </button>
          </form>

          <p className="text-center text-lego-dark-gray font-medium mt-7 text-sm">
            Already have an account?{' '}
            <Link href="/login" className="text-lego-black font-bold underline decoration-lego-yellow decoration-2 underline-offset-2 hover:decoration-lego-black transition-colors">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
