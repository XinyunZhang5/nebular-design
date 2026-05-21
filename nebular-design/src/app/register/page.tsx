'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

const AVATARS = ['🟡', '🔵', '🟢', '🔴', '🟠', '🟣', '⚫', '🟤'];

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [avatar, setAvatar] = useState('🟡');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) { setError('Password must be at least 6 characters'); return; }
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
    <div className="min-h-screen lego-stud-bg flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-md">
        <div className="lego-card p-8 bg-white">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-lego-yellow border-[3px] border-lego-black shadow-[4px_4px_0_#1C1C1C] mb-4">
              <span className="text-2xl">✨</span>
            </div>
            <h1 className="font-black text-3xl text-lego-black">Join the builders!</h1>
            <p className="text-lego-dark-gray font-semibold mt-1">Create your free account</p>
          </div>

          {error && (
            <div className="mb-6 p-3 rounded-md font-bold text-sm border-2 bg-red-50"
              style={{ borderColor: '#E3000B', color: '#E3000B' }}>⚠️ {error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block font-black text-sm text-lego-black mb-2">Choose your avatar</label>
              <div className="flex flex-wrap gap-2">
                {AVATARS.map(a => (
                  <button key={a} type="button" onClick={() => setAvatar(a)}
                    className="w-10 h-10 rounded-md text-xl flex items-center justify-center border-2 transition-all"
                    style={{
                      borderColor: avatar === a ? '#1C1C1C' : '#D0D0D0',
                      background: avatar === a ? '#F7D117' : '#F2F2F2',
                      boxShadow: avatar === a ? '3px 3px 0 #1C1C1C' : 'none',
                      transform: avatar === a ? 'translate(-1px,-1px)' : 'none',
                    }}>
                    {a}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block font-black text-sm text-lego-black mb-1.5">Username</label>
              <input type="text" required minLength={3} maxLength={20} className="lego-input"
                placeholder="BrickMaster99" value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })} />
            </div>
            <div>
              <label className="block font-black text-sm text-lego-black mb-1.5">Email</label>
              <input type="email" required className="lego-input" placeholder="you@example.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="block font-black text-sm text-lego-black mb-1.5">Password</label>
              <input type="password" required minLength={6} className="lego-input"
                placeholder="At least 6 characters" value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })} />
            </div>
            <button type="submit" disabled={loading} className="btn-lego w-full text-base py-3">
              {loading ? '⏳ Creating account...' : '🧱 Create My Account'}
            </button>
          </form>

          <p className="text-center text-lego-dark-gray font-semibold mt-6 text-sm">
            Already have an account?{' '}
            <Link href="/login" className="text-lego-black font-black hover:underline">Log in →</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
