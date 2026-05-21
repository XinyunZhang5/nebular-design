'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { api, chatroomWsUrl, MessageOut, UserOut, FriendshipOut } from '@/lib/api';

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

function MessageBubble({ msg, isOwn }: { msg: MessageOut; isOwn: boolean }) {
  return (
    <div className={`flex gap-3 ${isOwn ? 'flex-row-reverse' : ''}`}>
      <div className="w-9 h-9 rounded-full border-2 border-lego-black flex items-center justify-center text-lg flex-shrink-0"
        style={{ background: '#F7D117', boxShadow: '2px 2px 0 #1C1C1C' }}>
        {msg.sender_avatar}
      </div>
      <div className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} max-w-[75%]`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="font-black text-xs text-lego-dark-gray">{msg.sender_username}</span>
          <span className="text-xs text-lego-gray">{formatTime(msg.created_at)}</span>
        </div>
        <div className="px-4 py-2.5 font-semibold text-sm leading-relaxed"
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
    setAddStatus(prev => ({ ...prev, [targetUsername]: '⏳' }));
    try {
      await api.friends.request(targetUsername);
      setAddStatus(prev => ({ ...prev, [targetUsername]: '✅ 已发送' }));
    } catch (err) {
      setAddStatus(prev => ({ ...prev, [targetUsername]: `⚠️ ${err instanceof Error ? err.message : '失败'}` }));
    }
  };

  const alreadyFriend = (name: string) =>
    friendships.some(f => f.friend.username === name);

  return (
    <div className="min-h-screen bg-lego-bg flex flex-col">
      {/* Header */}
      <div className="lego-stud-bg border-b-[3px] border-lego-black py-6 px-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <span className="lego-badge mb-2">Community Chat</span>
            <h1 className="font-black text-3xl text-lego-black mt-2">Builder&apos;s Chat Room</h1>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-2 h-2 rounded-full" style={{ background: connected ? '#007934' : '#E3000B' }} />
              <p className="text-lego-dark-gray font-semibold text-sm">
                {connected ? 'WebSocket connected' : 'Connecting...'}
              </p>
            </div>
          </div>
          {!user && (
            <div className="hidden sm:block lego-card p-4 bg-white text-sm font-semibold text-lego-dark-gray max-w-xs">
              <strong className="text-lego-black">Chatting as guest.</strong><br />
              <Link href="/register" className="text-lego-blue underline font-black">Sign up</Link> to keep your username!
            </div>
          )}
        </div>
      </div>

      {/* Chat layout */}
      <div className="flex-1 flex max-w-6xl w-full mx-auto">
        {/* Messages */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-4 space-y-5"
            style={{ minHeight: '400px', maxHeight: 'calc(100vh - 340px)' }}>
            <div className="text-center py-3 px-6 rounded-xl border-2 border-lego-black inline-flex mx-auto items-center gap-2 text-sm font-bold"
              style={{ background: '#FFF9D6', display: 'flex', maxWidth: 'fit-content', margin: '0 auto' }}>
              👋 Welcome! Real-time via WebSocket · Be kind, build together.
            </div>
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} isOwn={msg.sender_username === (user?.username || '')} />
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="border-t-[3px] border-lego-black bg-white p-4">
            <form onSubmit={sendMessage} className="flex gap-3 items-center">
              <div className="w-8 h-8 rounded-full border-2 border-lego-black flex items-center justify-center text-base flex-shrink-0"
                style={{ background: '#F7D117' }}>
                {user?.avatar || '⚪'}
              </div>
              <input ref={inputRef} type="text" value={input} onChange={e => setInput(e.target.value)}
                placeholder={`Message as ${user?.username || 'Guest'}...`}
                className="lego-input flex-1" maxLength={500} autoComplete="off" />
              <button type="submit" disabled={!input.trim() || !connected}
                className="btn-lego flex-shrink-0" style={{ padding: '10px 20px' }}>
                Send →
              </button>
            </form>
            <p className="text-xs text-lego-gray font-semibold mt-2 ml-11">
              {input.length}/500
              {!user && <span> · <Link href="/register" className="text-lego-blue underline">Register</Link> to keep your username</span>}
            </p>
          </div>
        </div>

        {/* Members sidebar */}
        <div className={`border-l-[3px] border-lego-black bg-white transition-all ${showMemberList ? 'w-64' : 'w-12'} hidden lg:flex flex-col`}>
          <div className="flex items-center justify-between p-3 border-b-2 border-lego-black bg-lego-yellow">
            {showMemberList && <span className="font-black text-sm text-lego-black">Online Builders</span>}
            <button onClick={() => setShowMemberList(!showMemberList)}
              className="p-1 rounded border border-lego-black bg-white text-xs font-black ml-auto">
              {showMemberList ? '→' : '←'}
            </button>
          </div>

          {showMemberList && (
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {/* Current user */}
              {user && (
                <div className="flex items-center gap-2 p-2 rounded-md bg-lego-yellow/30 border border-lego-yellow">
                  <div className="w-7 h-7 rounded-full border-2 border-lego-black bg-lego-yellow flex items-center justify-center text-sm">
                    {user.avatar}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-black text-xs text-lego-black truncate">{user.username}</p>
                    <p className="text-xs text-lego-green font-semibold">You · Online</p>
                  </div>
                </div>
              )}

              {ONLINE_MEMBERS.map(m => (
                <div key={m.name} className="p-2 rounded-md hover:bg-lego-light-gray">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full border-2 border-lego-black bg-lego-yellow flex items-center justify-center text-sm flex-shrink-0">
                      {m.avatar}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-black text-xs text-lego-black truncate">{m.name}</p>
                      <p className="text-xs font-semibold"
                        style={{ color: m.status !== 'Away' ? '#007934' : '#9A9A9A' }}>
                        {m.status}
                      </p>
                    </div>
                  </div>
                  {user && !alreadyFriend(m.name) && m.name !== user.username && (
                    <div className="mt-1">
                      {addStatus[m.name] ? (
                        <span className="text-xs font-bold"
                          style={{ color: addStatus[m.name].startsWith('✅') ? '#007934' : '#E3000B' }}>
                          {addStatus[m.name]}
                        </span>
                      ) : (
                        <button onClick={() => sendFriendRequest(m.name)}
                          className="text-xs font-black text-lego-blue hover:underline">
                          + 加好友
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
