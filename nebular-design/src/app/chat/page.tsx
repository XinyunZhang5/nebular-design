'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { api, chatroomWsUrl, MessageOut, UserOut, FriendshipOut } from '@/lib/api';
import {
  Send, Wifi, WifiOff, UserPlus, Check, Users,
  PanelRightClose, PanelRightOpen, Loader2,
} from 'lucide-react';

const ONLINE_MEMBERS = [
  { name: 'BrickMaster99', avatar: '🟡', status: 'Building...' },
  { name: 'NebularFan', avatar: '🔵', status: 'Online' },
  { name: 'LegoLover', avatar: '🟢', status: 'Online' },
  { name: 'TowerBuilder', avatar: '🔴', status: 'Away' },
  { name: 'MicroBuilder', avatar: '🟠', status: 'Online' },
];

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function Avatar({ emoji, size = 36 }: { emoji: string; size?: number }) {
  return (
    <span
      className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, fontSize: size * 0.5, background: 'rgba(247,209,23,0.24)' }}
    >
      {emoji}
    </span>
  );
}

function MessageBubble({ msg, isOwn }: { msg: MessageOut; isOwn: boolean }) {
  return (
    <div className={`flex gap-3 ${isOwn ? 'flex-row-reverse' : ''}`}>
      <Avatar emoji={msg.sender_avatar} />
      <div className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} max-w-[75%]`}>
        <div className="flex items-center gap-2 mb-1.5 px-1">
          <span className="font-bold text-xs text-lego-dark-gray">{msg.sender_username}</span>
          <span className="text-xs text-lego-gray">{formatTime(msg.created_at)}</span>
        </div>
        <div
          className="px-4 py-2.5 font-medium text-sm leading-relaxed"
          style={{
            background: isOwn ? '#1C1C1C' : '#FFFFFF',
            color: isOwn ? '#FFFFFF' : '#1C1C1C',
            borderRadius: isOwn ? '18px 6px 18px 18px' : '6px 18px 18px 18px',
            boxShadow: isOwn ? 'none' : '0 4px 14px rgba(28,28,28,0.07)',
          }}
        >
          {msg.content}
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [input, setInput] = useState('');
  const [user, setUser] = useState<UserOut | null>(null);
  const [connected, setConnected] = useState(false);
  const [showMemberList, setShowMemberList] = useState(true);
  const [addStatus, setAddStatus] = useState<Record<string, string>>({});
  const [friendships, setFriendships] = useState<FriendshipOut[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load user from localStorage and connect WebSocket
  useEffect(() => {
    const stored = localStorage.getItem('nebular_user');
    const u = stored ? JSON.parse(stored) : null;
    setUser(u);

    const url = chatroomWsUrl();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
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
  }, []);

  // Load friend list for "add friend" context
  useEffect(() => {
    const token = localStorage.getItem('nebular_token');
    if (!token) return;
    api.friends.list().then(setFriendships).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({
      content: input.trim(),
      username: user?.username || 'Guest',
      avatar: user?.avatar || '⚪',
    }));
    setInput('');
    inputRef.current?.focus();
  }, [input, user]);

  const sendFriendRequest = async (targetUsername: string) => {
    if (!user) return;
    setAddStatus(prev => ({ ...prev, [targetUsername]: 'pending' }));
    try {
      await api.friends.request(targetUsername);
      setAddStatus(prev => ({ ...prev, [targetUsername]: 'sent' }));
    } catch (err) {
      setAddStatus(prev => ({ ...prev, [targetUsername]: `err:${err instanceof Error ? err.message : '失败'}` }));
    }
  };

  const alreadyFriend = (name: string) =>
    friendships.some(f => f.friend.username === name);

  return (
    <div className="flex-1 bg-lego-bg flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b hairline bg-lego-bg/80 backdrop-blur-sm py-6 px-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div>
            <div className="eyebrow-min mb-1.5">Community</div>
            <h1 className="font-extrabold text-2xl sm:text-3xl text-lego-black tracking-tight">Builder&apos;s chat room</h1>
            <div className="flex items-center gap-1.5 mt-2 text-sm font-medium"
              style={{ color: connected ? '#007934' : '#9A9A9A' }}>
              {connected ? <Wifi size={15} strokeWidth={2.4} /> : <WifiOff size={15} strokeWidth={2.4} />}
              {connected ? 'Connected' : 'Connecting…'}
            </div>
          </div>
          {!user && (
            <div className="hidden sm:block card-soft px-5 py-4 text-sm font-medium text-lego-dark-gray max-w-xs">
              <span className="font-bold text-lego-black">Chatting as guest.</span>{' '}
              <Link href="/register" className="font-bold text-lego-black underline decoration-lego-yellow decoration-2 underline-offset-2">Sign up</Link> to keep your name.
            </div>
          )}
        </div>
      </div>

      {/* Chat layout */}
      <div className="flex-1 flex min-h-0 w-full max-w-6xl mx-auto">
        {/* Messages */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
            <div className="mx-auto w-fit max-w-md text-center badge-soft badge-yellow !px-4 !py-2 !text-[13px] leading-snug">
              Real-time via WebSocket. Be kind, build together.
            </div>
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} isOwn={msg.sender_username === (user?.username || '')} />
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="border-t hairline bg-white/70 backdrop-blur-sm px-4 sm:px-6 py-4">
            <form onSubmit={sendMessage} className="flex gap-3 items-center">
              <Avatar emoji={user?.avatar || '⚪'} size={38} />
              <input ref={inputRef} type="text" value={input} onChange={e => setInput(e.target.value)}
                placeholder={`Message as ${user?.username || 'Guest'}…`}
                className="input-soft flex-1" maxLength={500} autoComplete="off" />
              <button type="submit" disabled={!input.trim() || !connected}
                className="btn-pill btn-pill-sm flex-shrink-0 disabled:opacity-40 disabled:pointer-events-none"
                aria-label="Send message">
                <Send size={16} strokeWidth={2.4} />
                <span className="hidden sm:inline">Send</span>
              </button>
            </form>
            <p className="text-xs text-lego-gray font-medium mt-2 ml-[50px]">
              {input.length}/500
              {!user && <> · <Link href="/register" className="text-lego-black font-semibold underline">Register</Link> to keep your name</>}
            </p>
          </div>
        </div>

        {/* Members sidebar */}
        <div className={`border-l hairline bg-white/60 transition-all duration-300 ${showMemberList ? 'w-64' : 'w-14'} hidden lg:flex flex-col min-h-0`}>
          <div className="flex items-center justify-between px-4 h-14 border-b hairline">
            {showMemberList && (
              <span className="inline-flex items-center gap-2 font-extrabold text-sm text-lego-black">
                <Users size={16} strokeWidth={2.4} /> Online
              </span>
            )}
            <button onClick={() => setShowMemberList(!showMemberList)}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-lego-dark-gray hover:bg-black/5 ml-auto transition-colors"
              aria-label={showMemberList ? 'Collapse members' : 'Expand members'}>
              {showMemberList ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
            </button>
          </div>

          {showMemberList && (
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {/* Current user */}
              {user && (
                <div className="flex items-center gap-2.5 p-2 rounded-xl" style={{ background: 'rgba(247,209,23,0.16)' }}>
                  <Avatar emoji={user.avatar} size={32} />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm text-lego-black truncate">{user.username}</p>
                    <p className="text-xs text-lego-green font-semibold">You · Online</p>
                  </div>
                </div>
              )}

              {ONLINE_MEMBERS.map(m => {
                const away = m.status === 'Away';
                const status = addStatus[m.name];
                return (
                  <div key={m.name} className="p-2 rounded-xl hover:bg-black/[0.03] transition-colors">
                    <div className="flex items-center gap-2.5">
                      <Avatar emoji={m.avatar} size={32} />
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm text-lego-black truncate">{m.name}</p>
                        <p className="text-xs font-semibold inline-flex items-center gap-1.5"
                          style={{ color: away ? '#9A9A9A' : '#007934' }}>
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: away ? '#9A9A9A' : '#007934' }} />
                          {m.status}
                        </p>
                      </div>
                    </div>
                    {user && !alreadyFriend(m.name) && m.name !== user.username && (
                      <div className="mt-1.5 ml-[42px]">
                        {status === 'sent' ? (
                          <span className="text-xs font-semibold text-lego-green inline-flex items-center gap-1">
                            <Check size={12} strokeWidth={3} /> Request sent
                          </span>
                        ) : status?.startsWith('err:') ? (
                          <span className="text-xs font-semibold text-lego-red">{status.slice(4)}</span>
                        ) : status === 'pending' ? (
                          <span className="text-xs font-semibold text-lego-gray inline-flex items-center gap-1">
                            <Loader2 size={12} className="animate-spin" /> Sending…
                          </span>
                        ) : (
                          <button onClick={() => sendFriendRequest(m.name)}
                            className="text-xs font-bold text-lego-black inline-flex items-center gap-1 hover:opacity-70 transition-opacity">
                            <UserPlus size={13} strokeWidth={2.4} /> Add friend
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
