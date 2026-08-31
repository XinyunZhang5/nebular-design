'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, buildTitle, UserOut, Project, FriendshipOut } from '@/lib/api';
import { BrickStack, G, WALL } from '@/components/Bricks';
import BrickAvatar from '@/components/BrickAvatar';
import {
  Plus, Boxes, Users, UserPlus, MessageCircle, Trash2, X, Clock,
  Check, Loader2, Building2, Inbox, Send,
} from 'lucide-react';

const DIFFICULTY_COLORS: Record<string, string> = {
  Beginner: '#007934', Intermediate: '#FF6B00', Expert: '#E3000B',
  Medium: '#FF6B00', Hard: '#E3000B',
};

function hexToRgba(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function DifficultyBadge({ level, className = '' }: { level: string; className?: string }) {
  const c = DIFFICULTY_COLORS[level] || '#4A4A4A';
  return (
    <span className={`badge-soft ${className}`} style={{ background: hexToRgba(c, 0.14), color: c }}>
      {level}
    </span>
  );
}

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [friendships, setFriendships] = useState<FriendshipOut[]>([]);
  const [addTarget, setAddTarget] = useState('');
  const [addStatus, setAddStatus] = useState('');
  const [activeTab, setActiveTab] = useState<'builds' | 'friends'>('builds');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('nebular_user');
    if (!stored) { router.push('/login'); return; }
    setUser(JSON.parse(stored));

    Promise.all([api.images.history(), api.friends.list()])
      .then(([p, f]) => { setProjects(p); setFriendships(f); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [router]);

  const sendRequest = async () => {
    if (!addTarget.trim()) return;
    setAddStatus('');
    try {
      await api.friends.request(addTarget.trim());
      setAddStatus('ok:Friend request sent');
      setAddTarget('');
      const f = await api.friends.list();
      setFriendships(f);
    } catch (err) {
      setAddStatus(`err:${err instanceof Error ? err.message : 'Could not send request'}`);
    }
  };

  const accept = async (id: string) => {
    await api.friends.accept(id);
    const f = await api.friends.list();
    setFriendships(f);
  };

  const reject = async (id: string) => {
    await api.friends.reject(id);
    const f = await api.friends.list();
    setFriendships(f);
  };

  const remove = async (id: string) => {
    await api.friends.remove(id);
    const f = await api.friends.list();
    setFriendships(f);
  };

  const accepted = friendships.filter(f => f.status === 'accepted');
  const pendingReceived = friendships.filter(f => f.status === 'pending' && !f.is_requester);
  const pendingSent = friendships.filter(f => f.status === 'pending' && f.is_requester);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  if (!user) return (
    <div className="flex-1 flex items-center justify-center bg-lego-bg">
      <div className="card-soft px-10 py-8 text-center">
        <Loader2 size={28} className="animate-spin mx-auto mb-3 text-lego-black" />
        <p className="font-bold text-lego-black">Loading…</p>
      </div>
    </div>
  );

  return (
    <div className="bg-lego-bg">
      {/* Header */}
      <div className="border-b hairline">
        <div className="max-w-5xl mx-auto px-6 py-10 flex flex-col sm:flex-row items-start sm:items-center gap-5">
          <div className="w-20 h-20 rounded-3xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(247,209,23,0.9)', boxShadow: 'inset 0 0 0 1px rgba(28,28,28,0.08)' }}>
            <BrickAvatar avatar={user.avatar} size={58} />
          </div>
          <div className="flex-1">
            <div className="eyebrow-min mb-1.5">Profile</div>
            <h1 className="font-extrabold text-3xl text-lego-black tracking-tight">{user.username}</h1>
            <p className="text-lego-dark-gray font-medium mt-0.5">{user.email}</p>
            <div className="flex flex-wrap gap-2 mt-3.5">
              <span className="badge-soft"><Boxes size={14} strokeWidth={2.2} /> {projects.length} builds</span>
              <span className="badge-soft"><Users size={14} strokeWidth={2.2} /> {accepted.length} friends</span>
            </div>
          </div>
          <Link href="/upload" className="btn-pill btn-pill-sm">
            <Plus size={16} strokeWidth={2.6} /> New build
          </Link>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10">
        {/* Tabs */}
        <div className="flex items-center gap-7 border-b hairline mb-8">
          <button onClick={() => setActiveTab('builds')} data-active={activeTab === 'builds'} className="tab-underline">
            My builds ({projects.length})
          </button>
          <button onClick={() => setActiveTab('friends')} data-active={activeTab === 'friends'} className="tab-underline">
            Friends ({accepted.length}{pendingReceived.length > 0 ? ` · ${pendingReceived.length} new` : ''})
          </button>
        </div>

        {/* BUILDS */}
        {activeTab === 'builds' && (
          loading ? (
            <div className="text-center py-16 font-semibold text-lego-gray inline-flex items-center gap-2 w-full justify-center">
              <Loader2 size={18} className="animate-spin" /> Loading builds…
            </div>
          ) : projects.length === 0 ? (
            <div className="card-soft px-8 py-16 text-center max-w-md mx-auto">
              <BrickStack
                ns="empty-builds"
                bricks={[
                  { ox: 0, oy: 0, oz: 0, w: 3, d: 2, ...G.sky },
                  { ox: 0.5, oy: 0.5, oz: WALL, w: 2, d: 1, ...G.coral },
                ]}
                unit={28}
                className="w-28 h-auto mx-auto mb-6 brick-shadow"
              />
              <h3 className="font-extrabold text-xl text-lego-black mb-2">No builds yet</h3>
              <p className="text-lego-dark-gray font-medium mb-7">Upload your first building photo to start a build.</p>
              <Link href="/upload" className="btn-pill btn-pill-sm mx-auto w-fit">
                <Plus size={16} strokeWidth={2.6} /> Start a build
              </Link>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map(p => {
                const imgSrc = p.image_url.startsWith('/static/')
                  ? `${API_URL}${p.image_url}` : p.image_url;
                const result = p.result_json;
                return (
                  <Link key={p.id} href={`/build/${p.id}`} className="card-soft card-hover overflow-hidden block">
                    <div className="h-40 bg-lego-light-gray overflow-hidden">
                      {imgSrc
                        ? <img src={imgSrc} alt={buildTitle(p) || ''} className="w-full h-full object-cover" />
                        : <div className="w-full h-full flex items-center justify-center text-lego-gray"><Building2 size={32} /></div>}
                    </div>
                    <div className="p-4">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-extrabold text-lego-black leading-tight">
                          {buildTitle(p) || 'Untitled build'}
                        </h4>
                        {result?.difficulty && <DifficultyBadge level={result.difficulty} className="flex-shrink-0 !text-[11px] !px-2.5 !py-1" />}
                      </div>
                      {result && (
                        <p className="text-lego-dark-gray text-xs font-semibold mt-2 inline-flex items-center gap-3">
                          <span className="inline-flex items-center gap-1"><Boxes size={13} strokeWidth={2.2} /> {result.estimatedPieceCount}</span>
                          <span className="inline-flex items-center gap-1"><Clock size={13} strokeWidth={2.2} /> {result.estimatedTime}</span>
                        </p>
                      )}
                      <p className="text-lego-gray text-xs font-medium mt-1.5">{timeAgo(p.created_at)}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          )
        )}

        {/* FRIENDS */}
        {activeTab === 'friends' && (
          <div className="space-y-6 max-w-2xl">
            {/* Add friend */}
            <div className="card-soft p-6">
              <h3 className="font-extrabold text-lego-black mb-3.5 inline-flex items-center gap-2">
                <UserPlus size={18} strokeWidth={2.2} /> Add a friend
              </h3>
              <div className="flex gap-3">
                <input type="text" value={addTarget} onChange={e => setAddTarget(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendRequest()}
                  placeholder="Enter a username…" className="input-soft flex-1" />
                <button onClick={sendRequest} className="btn-pill btn-pill-sm flex-shrink-0">
                  <Send size={15} strokeWidth={2.4} /> Send
                </button>
              </div>
              {addStatus && (
                <p className="mt-3 text-sm font-semibold inline-flex items-center gap-1.5"
                  style={{ color: addStatus.startsWith('ok:') ? '#007934' : '#E3000B' }}>
                  {addStatus.startsWith('ok:') ? <Check size={14} strokeWidth={3} /> : null}
                  {addStatus.slice(addStatus.indexOf(':') + 1)}
                </p>
              )}
            </div>

            {/* Pending received */}
            {pendingReceived.length > 0 && (
              <div className="card-soft p-6">
                <h3 className="font-extrabold text-lego-black mb-4 inline-flex items-center gap-2">
                  <Inbox size={18} strokeWidth={2.2} /> Requests ({pendingReceived.length})
                </h3>
                <div className="space-y-2">
                  {pendingReceived.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-2xl" style={{ background: 'rgba(247,209,23,0.12)' }}>
                      <BrickAvatar avatar={f.friend.avatar} />
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-lego-black truncate">{f.friend.username}</p>
                        <p className="text-xs text-lego-dark-gray font-medium">wants to be your friend</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => accept(f.id)} className="btn-pill" style={{ padding: '8px 16px', fontSize: 13 }}>
                          <Check size={14} strokeWidth={3} /> Accept
                        </button>
                        <button onClick={() => reject(f.id)}
                          className="w-9 h-9 flex items-center justify-center rounded-full border border-black/10 text-lego-dark-gray hover:bg-black/5 transition-colors"
                          aria-label="Decline">
                          <X size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Accepted */}
            {accepted.length > 0 && (
              <div className="card-soft p-6">
                <h3 className="font-extrabold text-lego-black mb-4 inline-flex items-center gap-2">
                  <Users size={18} strokeWidth={2.2} /> Friends ({accepted.length})
                </h3>
                <div className="space-y-1">
                  {accepted.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-2xl hover:bg-black/[0.03] transition-colors">
                      <BrickAvatar avatar={f.friend.avatar} />
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-lego-black truncate">{f.friend.username}</p>
                        <p className="text-xs text-lego-green font-semibold inline-flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-lego-green" /> Online
                        </p>
                      </div>
                      <div className="flex gap-2 items-center">
                        <Link href={`/dm?toId=${f.friend.id}&toName=${f.friend.username}&toAvatar=${f.friend.avatar}`}
                          className="btn-pill" style={{ padding: '8px 16px', fontSize: 13 }}>
                          <MessageCircle size={14} strokeWidth={2.4} /> Message
                        </Link>
                        <button onClick={() => remove(f.id)}
                          className="w-9 h-9 flex items-center justify-center rounded-full border border-black/10 text-lego-gray hover:text-lego-red hover:border-lego-red/30 transition-colors"
                          aria-label="Remove friend">
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pending sent */}
            {pendingSent.length > 0 && (
              <div className="card-soft p-6">
                <h3 className="font-extrabold text-lego-black mb-4 inline-flex items-center gap-2">
                  <Clock size={18} strokeWidth={2.2} /> Sent ({pendingSent.length})
                </h3>
                <div className="space-y-1">
                  {pendingSent.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-2xl bg-black/[0.02]">
                      <BrickAvatar avatar={f.friend.avatar} />
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-lego-black truncate">{f.friend.username}</p>
                        <p className="text-xs text-lego-gray font-medium">Waiting for them to accept…</p>
                      </div>
                      <button onClick={() => remove(f.id)} className="btn-pill-outline" style={{ padding: '7px 15px', fontSize: 13 }}>
                        Cancel
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {accepted.length === 0 && pendingReceived.length === 0 && pendingSent.length === 0 && (
              <div className="card-soft px-8 py-14 text-center">
                <BrickStack
                  ns="empty-friends"
                  bricks={[{ ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...G.lilac }, { ox: 0.5, oy: 0.5, oz: WALL, w: 1, d: 1, ...G.yellow }]}
                  unit={26}
                  className="w-24 h-auto mx-auto mb-5 brick-shadow"
                />
                <h3 className="font-extrabold text-xl text-lego-black mb-2">No friends yet</h3>
                <p className="text-lego-dark-gray font-medium">Head to the Community chat room to meet fellow builders.</p>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
