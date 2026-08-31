'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { dmWsUrl, MessageOut, UserOut } from '@/lib/api';
import { BrickStack, G, WALL } from '@/components/Bricks';
import BrickAvatar from '@/components/BrickAvatar';
import { ChevronLeft, Wifi, WifiOff, Send, Loader2 } from 'lucide-react';

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
    <div className="flex-1 bg-lego-bg flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b hairline bg-lego-bg/80 backdrop-blur-sm px-4 sm:px-6 py-4 flex items-center gap-3.5">
        <Link href="/profile"
          className="w-9 h-9 flex items-center justify-center rounded-full border border-black/10 text-lego-dark-gray hover:bg-black/5 transition-colors flex-shrink-0"
          aria-label="Back to profile">
          <ChevronLeft size={18} />
        </Link>
        <BrickAvatar avatar={toAvatar} size={42} />
        <div>
          <h2 className="font-extrabold text-lg text-lego-black tracking-tight">{toName}</h2>
          <div className="flex items-center gap-1.5 text-xs font-medium"
            style={{ color: connected ? '#007934' : '#9A9A9A' }}>
            {connected ? <Wifi size={13} strokeWidth={2.4} /> : <WifiOff size={13} strokeWidth={2.4} />}
            {connected ? 'Connected' : 'Connecting…'}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6 min-h-0 max-w-3xl w-full mx-auto">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <BrickStack
              ns="dm-empty"
              bricks={[{ ox: 0, oy: 0, oz: 0, w: 2, d: 1, ...G.sky }, { ox: 0.5, oy: 0, oz: WALL, w: 1, d: 1, ...G.coral }]}
              unit={26}
              className="w-24 h-auto mx-auto mb-5 brick-shadow"
            />
            <p className="font-extrabold text-lego-black mb-1">No messages yet</p>
            <p className="text-lego-dark-gray font-medium text-sm">Send the first message to start the conversation.</p>
          </div>
        )}
        {messages.map(msg => {
          const isOwn = msg.sender_id === user.id;
          return (
            <div key={msg.id} className={`flex gap-3 ${isOwn ? 'flex-row-reverse' : ''}`}>
              <BrickAvatar avatar={msg.sender_avatar} size={34} />
              <div className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} max-w-[72%]`}>
                <div className="flex items-center gap-2 mb-1.5 px-1">
                  <span className="text-xs font-bold text-lego-dark-gray">{msg.sender_username}</span>
                  <span className="text-xs text-lego-gray">{formatTime(msg.created_at)}</span>
                </div>
                <div className="px-4 py-2.5 text-sm font-medium leading-relaxed"
                  style={{
                    background: isOwn ? '#1C1C1C' : '#FFFFFF',
                    color: isOwn ? '#FFFFFF' : '#1C1C1C',
                    borderRadius: isOwn ? '18px 6px 18px 18px' : '6px 18px 18px 18px',
                    boxShadow: isOwn ? 'none' : '0 4px 14px rgba(28,28,28,0.07)',
                  }}>
                  {msg.content}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="border-t hairline bg-white/70 backdrop-blur-sm px-4 sm:px-6 py-4">
        <form onSubmit={send} className="flex gap-3 max-w-3xl mx-auto">
          <input type="text" value={input} onChange={e => setInput(e.target.value)}
            placeholder={`Message ${toName}…`} className="input-soft flex-1" maxLength={500} />
          <button type="submit" disabled={!input.trim() || !connected}
            className="btn-pill btn-pill-sm flex-shrink-0 disabled:opacity-40 disabled:pointer-events-none"
            aria-label="Send message">
            <Send size={16} strokeWidth={2.4} />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}

export default function DMPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex items-center justify-center bg-lego-bg">
        <div className="card-soft px-10 py-8 text-center">
          <Loader2 size={28} className="animate-spin mx-auto mb-3 text-lego-black" />
          <p className="font-bold text-lego-black">Loading…</p>
        </div>
      </div>
    }>
      <DMContent />
    </Suspense>
  );
}
