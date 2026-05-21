'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
    <div className="min-h-screen lego-stud-bg flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-md">
        <div className="lego-card p-8 bg-white">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-lego-yellow border-[3px] border-lego-black shadow-[4px_4px_0_#1C1C1C] mb-4">
              <span className="text-2xl">🧱</span>
            </div>
            <h1 className="font-black text-3xl text-lego-black">Welcome back!</h1>
            <p className="text-lego-dark-gray font-semibold mt-1">Log in to continue building</p>
          </div>

          {error && (
            <div className="mb-6 p-3 rounded-md font-bold text-sm border-2 bg-red-50"
              style={{ borderColor: '#E3000B', color: '#E3000B' }}>
              ⚠️ {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block font-black text-sm text-lego-black mb-1.5">Email</label>
              <input type="email" required className="lego-input" placeholder="you@example.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="block font-black text-sm text-lego-black mb-1.5">Password</label>
              <input type="password" required className="lego-input" placeholder="••••••••"
                value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
            </div>
            <button type="submit" disabled={loading} className="btn-lego w-full text-base py-3">
              {loading ? '⏳ Logging in...' : '🚀 Log In'}
            </button>
          </form>

          <p className="text-center text-lego-dark-gray font-semibold mt-6 text-sm">
            No account?{' '}
            <Link href="/register" className="text-lego-black font-black hover:underline">Sign up free →</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
