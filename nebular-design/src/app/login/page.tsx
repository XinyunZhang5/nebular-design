'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { BrickStack, G } from '@/components/Bricks';
import { CircleAlert, Eye, EyeOff, Loader2, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.auth.login(form);
      localStorage.setItem('nebular_token', data.access_token);
      localStorage.setItem('nebular_user', JSON.stringify(data.user));
      router.push('/upload');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
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
              ns="login-mark"
              bricks={[{ ox: 0, oy: 0, oz: 0, w: 2, d: 1, ...G.yellow }]}
              unit={30}
              className="w-16 h-auto mx-auto mb-6 brick-shadow"
            />
            <h1 className="display-xl text-lego-black" style={{ fontSize: 'clamp(1.9rem, 4vw, 2.4rem)' }}>
              Welcome back.
            </h1>
            <p className="text-lego-dark-gray font-medium mt-2">Log in to keep building.</p>
          </div>

          {error && (
            <div className="mb-6 flex items-center gap-2.5 px-4 py-3 rounded-2xl font-semibold text-sm"
              style={{ background: 'rgba(227,0,11,0.08)', color: '#E3000B' }}>
              <CircleAlert size={16} strokeWidth={2.2} className="flex-shrink-0" /> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex flex-col gap-2">
              <label htmlFor="email" className="font-bold text-sm text-lego-black">Email</label>
              <input id="email" type="email" required className="input-soft" placeholder="you@example.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="password" className="font-bold text-sm text-lego-black">Password</label>
              <div className="relative">
                <input id="password" type={showPw ? 'text' : 'password'} required className="input-soft pr-12"
                  placeholder="••••••••" value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })} />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg text-lego-gray hover:text-lego-black hover:bg-black/5 transition-colors"
                  aria-label={showPw ? 'Hide password' : 'Show password'}>
                  {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-pill w-full justify-center !py-3.5 disabled:opacity-50 disabled:pointer-events-none">
              {loading ? <><Loader2 size={17} className="animate-spin" /> Logging in…</> : <>Log in <ArrowRight size={17} strokeWidth={2.4} /></>}
            </button>
          </form>

          <p className="text-center text-lego-dark-gray font-medium mt-7 text-sm">
            No account?{' '}
            <Link href="/register" className="text-lego-black font-bold underline decoration-lego-yellow decoration-2 underline-offset-2 hover:decoration-lego-black transition-colors">
              Sign up free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
