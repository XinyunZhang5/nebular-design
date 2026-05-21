'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { dmWsUrl, MessageOut, UserOut } from '@/lib/api';

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function DMContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const toId = searchParams.get('toId') || '';
  const toName = searchParams.get('toName') || 'Friend';
  const toAvatar = searchParams.get('toAvatar') || '⚪';

  const [user, setUser] = useState<UserOut | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem('nebular_user');
    if (!stored) { router.push('/login'); return; }
    const u = JSON.parse(stored);
    setUser(u);

    if (!toId) return;

    const url = dmWsUrl(toId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = (e) => {
      setConnected(false);
      // 4003 = not friends
      if (e.code === 4003) router.push('/profile');
    };
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'history') {
        setMessages(data.messages);
      } else if (data.type === 'message') {
        setMessages(prev => [...prev, data.message]);
      }
    };

    return () => ws.close();
  }, [toId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ content: input.trim() }));
    setInput('');
  }, [input]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-lego-bg flex flex-col">
      <div className="bg-lego-yellow border-b-[3px] border-lego-black px-4 py-4 flex items-center gap-4">
        <Link href="/profile" className="btn-lego-outline" style={{ padding: '6px 14px', fontSize: '13px' }}>
          ← Back
        </Link>
        <div className="w-10 h-10 rounded-full border-2 border-lego-black bg-white flex items-center justify-center text-xl"
          style={{ boxShadow: '2px 2px 0 #1C1C1C' }}>
          {toAvatar}
        </div>
        <div>
          <h2 className="font-black text-lego-black">{toName}</h2>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ background: connected ? '#007934' : '#E3000B' }} />
            <p className="text-xs text-lego-dark-gray font-semibold">
              {connected ? 'WebSocket connected' : 'Connecting...'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ maxHeight: 'calc(100vh - 200px)' }}>
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="text-5xl mb-3">💬</div>
            <p className="font-black text-lego-black mb-1">还没有消息</p>
            <p className="text-lego-dark-gray font-semibold text-sm">发送第一条消息开始聊天！</p>
          </div>
        )}
        {messages.map(msg => {
          const isOwn = msg.sender_id === user.id;
          return (
            <div key={msg.id} className={`flex gap-3 ${isOwn ? 'flex-row-reverse' : ''}`}>
              <div className="w-8 h-8 rounded-full border-2 border-lego-black flex items-center justify-center text-base flex-shrink-0"
                style={{ background: '#F7D117' }}>
                {msg.sender_avatar}
              </div>
              <div className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} max-w-[70%]`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-black text-lego-dark-gray">{msg.sender_username}</span>
                  <span className="text-xs text-lego-gray">{formatTime(msg.created_at)}</span>
                </div>
                <div className="px-4 py-2.5 text-sm font-semibold leading-relaxed"
                  style={{
                    background: isOwn ? '#F7D117' : '#FFFFFF',
                    border: '2px solid #1C1C1C',
                    boxShadow: isOwn ? '3px 3px 0 #C9A800' : '3px 3px 0 #1C1C1C',
                    borderRadius: isOwn ? '12px 2px 12px 12px' : '2px 12px 12px 12px',
                  }}>
                  {msg.content}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div className="border-t-[3px] border-lego-black bg-white p-4">
        <form onSubmit={send} className="flex gap-3">
          <input type="text" value={input} onChange={e => setInput(e.target.value)}
            placeholder={`给 ${toName} 发消息...`} className="lego-input flex-1" maxLength={500} />
          <button type="submit" disabled={!input.trim() || !connected}
            className="btn-lego flex-shrink-0" style={{ padding: '10px 20px' }}>
            发送 →
          </button>
        </form>
      </div>
    </div>
  );
}

export default function DMPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center lego-stud-bg">
        <div className="lego-card p-8 text-center">
          <div className="text-4xl mb-3">⏳</div>
          <p className="font-black text-lego-black">Loading...</p>
        </div>
      </div>
    }>
      <DMContent />
    </Suspense>
  );
}
