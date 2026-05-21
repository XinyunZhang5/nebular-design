'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, UserOut, Project, FriendshipOut } from '@/lib/api';

const DIFFICULTY_COLORS: Record<string, string> = {
  Beginner: '#007934', Intermediate: '#FF6B00', Expert: '#E3000B',
};

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
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
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
      setAddStatus('✅ 好友请求已发送！');
      setAddTarget('');
      const f = await api.friends.list();
      setFriendships(f);
    } catch (err) {
      setAddStatus(`⚠️ ${err instanceof Error ? err.message : '发送失败'}`);
    }
  };

  const accept = async (id: string) => {
    await api.friends.accept(id);
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
    <div className="min-h-screen flex items-center justify-center lego-stud-bg">
      <div className="lego-card p-8 text-center">
        <div className="text-4xl mb-3">⏳</div>
        <p className="font-black text-lego-black">Loading...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-lego-bg">
      <div className="lego-stud-bg border-b-[3px] border-lego-black py-8 px-4">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-5">
          <div className="w-20 h-20 rounded-xl border-[3px] border-lego-black flex items-center justify-center text-4xl"
            style={{ background: '#F7D117', boxShadow: '5px 5px 0 #1C1C1C' }}>
            {user.avatar}
          </div>
          <div className="flex-1">
            <h1 className="font-black text-3xl text-lego-black">{user.username}</h1>
            <p className="text-lego-dark-gray font-semibold">{user.email}</p>
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="lego-badge">🧱 {projects.length} builds</span>
              <span className="lego-badge" style={{ background: '#006DB7', color: 'white' }}>
                👥 {accepted.length} friends
              </span>
            </div>
          </div>
          <Link href="/upload" className="btn-lego">+ New Build</Link>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex border-b-[3px] border-lego-black mb-8">
          {(['builds', 'friends'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className="px-6 py-3 font-black text-sm capitalize rounded-t-md -mb-[3px] border-t-2 border-x-2"
              style={{
                borderColor: '#1C1C1C', background: activeTab === tab ? '#F7D117' : '#F2F2F2',
                borderBottomColor: activeTab === tab ? '#F7D117' : '#1C1C1C',
              }}>
              {tab === 'builds'
                ? `🏗️ My Builds (${projects.length})`
                : `👥 Friends (${accepted.length}${pendingReceived.length > 0 ? ` · ${pendingReceived.length} new` : ''})`}
            </button>
          ))}
        </div>

        {/* BUILDS */}
        {activeTab === 'builds' && (
          loading ? (
            <div className="text-center py-12 font-black text-lego-dark-gray">Loading builds...</div>
          ) : projects.length === 0 ? (
            <div className="lego-card p-12 text-center">
              <div className="text-5xl mb-4">🏗️</div>
              <h3 className="font-black text-xl text-lego-black mb-2">还没有作品</h3>
              <p className="text-lego-dark-gray font-semibold mb-6">上传你的第一张建筑照片吧！</p>
              <Link href="/upload" className="btn-lego">📸 去上传</Link>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map(p => {
                const imgSrc = p.image_url.startsWith('/static/')
                  ? `${API_URL}${p.image_url}` : p.image_url;
                const result = p.result_json;
                return (
                  <div key={p.id} className="lego-card overflow-hidden cursor-pointer"
                    onClick={() => setSelectedProject(p)}>
                    <div className="h-36 bg-lego-light-gray border-b-2 border-lego-black overflow-hidden">
                      {imgSrc
                        ? <img src={imgSrc} alt={result?.buildingName || ''} className="w-full h-full object-cover" />
                        : <div className="w-full h-full flex items-center justify-center text-4xl">🏛️</div>}
                    </div>
                    <div className="p-4">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-black text-lego-black text-sm leading-tight">
                          {result?.buildingName || 'Unnamed Build'}
                        </h4>
                        {result?.difficulty && (
                          <span className="lego-badge text-white flex-shrink-0"
                            style={{ background: DIFFICULTY_COLORS[result.difficulty] || '#888', fontSize: 10, padding: '2px 6px' }}>
                            {result.difficulty}
                          </span>
                        )}
                      </div>
                      {result && (
                        <p className="text-lego-dark-gray text-xs font-semibold mt-1">
                          🧱 {result.estimatedPieceCount} pieces · ⏱️ {result.estimatedTime}
                        </p>
                      )}
                      <p className="text-lego-gray text-xs font-semibold mt-1">{timeAgo(p.created_at)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        )}

        {/* FRIENDS */}
        {activeTab === 'friends' && (
          <div className="space-y-6">
            <div className="lego-card p-5">
              <h3 className="font-black text-lego-black mb-3">➕ 添加好友</h3>
              <div className="flex gap-3">
                <input type="text" value={addTarget} onChange={e => setAddTarget(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendRequest()}
                  placeholder="输入用户名..." className="lego-input flex-1" />
                <button onClick={sendRequest} className="btn-lego flex-shrink-0">发送请求</button>
              </div>
              {addStatus && (
                <p className="mt-2 text-sm font-bold"
                  style={{ color: addStatus.startsWith('✅') ? '#007934' : '#E3000B' }}>
                  {addStatus}
                </p>
              )}
            </div>

            {pendingReceived.length > 0 && (
              <div className="lego-card p-5">
                <h3 className="font-black text-lego-black mb-4">📬 待接受的请求 ({pendingReceived.length})</h3>
                <div className="space-y-3">
                  {pendingReceived.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-md bg-lego-yellow/20 border-2 border-lego-yellow">
                      <div className="w-10 h-10 rounded-full border-2 border-lego-black bg-lego-yellow flex items-center justify-center text-xl">
                        {f.friend.avatar}
                      </div>
                      <div className="flex-1">
                        <p className="font-black text-lego-black">{f.friend.username}</p>
                        <p className="text-xs text-lego-dark-gray font-semibold">想加你为好友</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => accept(f.id)} className="btn-lego"
                          style={{ padding: '6px 14px', fontSize: '13px' }}>✓ 接受</button>
                        <button onClick={() => remove(f.id)} className="btn-lego-outline"
                          style={{ padding: '6px 12px', fontSize: '13px' }}>✗</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {accepted.length > 0 && (
              <div className="lego-card p-5">
                <h3 className="font-black text-lego-black mb-4">👥 我的好友 ({accepted.length})</h3>
                <div className="space-y-2">
                  {accepted.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-md hover:bg-lego-light-gray">
                      <div className="w-10 h-10 rounded-full border-2 border-lego-black bg-lego-yellow flex items-center justify-center text-xl">
                        {f.friend.avatar}
                      </div>
                      <div className="flex-1">
                        <p className="font-black text-lego-black">{f.friend.username}</p>
                        <p className="text-xs text-lego-green font-semibold">● Online</p>
                      </div>
                      <div className="flex gap-2">
                        <Link href={`/dm?toId=${f.friend.id}&toName=${f.friend.username}&toAvatar=${f.friend.avatar}`}
                          className="btn-lego" style={{ padding: '6px 14px', fontSize: '13px' }}>
                          💬 私信
                        </Link>
                        <button onClick={() => remove(f.id)} className="btn-lego-outline"
                          style={{ padding: '6px 12px', fontSize: '13px', color: '#E3000B' }}>
                          删除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {pendingSent.length > 0 && (
              <div className="lego-card p-5">
                <h3 className="font-black text-lego-black mb-4">⏳ 已发出的请求 ({pendingSent.length})</h3>
                <div className="space-y-2">
                  {pendingSent.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-md bg-lego-light-gray">
                      <div className="w-10 h-10 rounded-full border-2 border-lego-black bg-lego-yellow flex items-center justify-center text-xl">
                        {f.friend.avatar}
                      </div>
                      <div className="flex-1">
                        <p className="font-black text-lego-black">{f.friend.username}</p>
                        <p className="text-xs text-lego-gray font-semibold">等待对方接受...</p>
                      </div>
                      <button onClick={() => remove(f.id)} className="btn-lego-outline"
                        style={{ padding: '6px 12px', fontSize: '13px' }}>取消</button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {accepted.length === 0 && pendingReceived.length === 0 && pendingSent.length === 0 && (
              <div className="lego-card p-10 text-center">
                <div className="text-5xl mb-3">👋</div>
                <h3 className="font-black text-xl text-lego-black mb-2">还没有好友</h3>
                <p className="text-lego-dark-gray font-semibold">去聊天室认识积木爱好者！</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Project modal */}
      {selectedProject && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedProject(null)}>
          <div className="lego-card bg-white w-full max-w-lg max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b-2 border-lego-black flex items-center justify-between bg-lego-yellow">
              <div>
                <h3 className="font-black text-xl text-lego-black">
                  {selectedProject.result_json?.buildingName || 'Build'}
                </h3>
                <p className="text-sm font-semibold text-lego-dark-gray">{timeAgo(selectedProject.created_at)}</p>
              </div>
              <button onClick={() => setSelectedProject(null)}
                className="w-8 h-8 rounded-md border-2 border-lego-black bg-white font-black flex items-center justify-center">
                ✕
              </button>
            </div>
            {selectedProject.image_url && (
              <div className="border-b-2 border-lego-black">
                <img
                  src={selectedProject.image_url.startsWith('/static/')
                    ? `${API_URL}${selectedProject.image_url}` : selectedProject.image_url}
                  alt="" className="w-full h-48 object-cover" />
              </div>
            )}
            {selectedProject.result_json && (
              <div className="p-5">
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="lego-badge">🧱 {selectedProject.result_json.estimatedPieceCount} pieces</span>
                  <span className="lego-badge bg-white">⏱️ {selectedProject.result_json.estimatedTime}</span>
                  <span className="lego-badge text-white"
                    style={{ background: DIFFICULTY_COLORS[selectedProject.result_json.difficulty] || '#888' }}>
                    {selectedProject.result_json.difficulty}
                  </span>
                </div>
                {selectedProject.depth_data && !('skipped' in selectedProject.depth_data) && (
                  <div className="p-3 rounded-md border-2 border-lego-light-gray bg-lego-light-gray/50 text-xs font-mono text-lego-dark-gray">
                    <p className="font-black text-lego-black mb-1">Depth Analysis (DepthAnything V2)</p>
                    <p>Mean depth: {String(selectedProject.depth_data.mean_depth ?? '—')} · Edge strength: {String(selectedProject.depth_data.edge_strength ?? '—')}</p>
                    <p>Zone: {String(selectedProject.depth_data.dominant_depth_zone ?? '—')} · Complexity: {String(selectedProject.depth_data.geometric_complexity ?? '—')}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
