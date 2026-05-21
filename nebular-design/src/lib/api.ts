const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('nebular_token');
}

async function request<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const isFormData = options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(!isFormData ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---- Auth ----
export const api = {
  auth: {
    register: (body: { username: string; email: string; password: string; avatar: string }) =>
      request<TokenResponse>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }),

    login: (body: { email: string; password: string }) =>
      request<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  },

  // ---- Images ----
  images: {
    upload: (formData: FormData) =>
      request<Project>('/api/images/upload', { method: 'POST', body: formData }),

    history: () => request<Project[]>('/api/images/history'),
  },

  // ---- Friends ----
  friends: {
    list: () => request<FriendshipOut[]>('/api/friends/list'),

    request: (targetUsername: string) =>
      request<FriendshipOut>('/api/friends/request', {
        method: 'POST',
        body: JSON.stringify({ target_username: targetUsername }),
      }),

    accept: (friendshipId: string) =>
      request<FriendshipOut>(`/api/friends/accept/${friendshipId}`, { method: 'POST' }),

    remove: (friendshipId: string) =>
      request<void>(`/api/friends/${friendshipId}`, { method: 'DELETE' }),
  },

  // ---- Chat history (REST fallback) ----
  chat: {
    messages: (limit = 60) => request<MessageOut[]>(`/api/chat/messages?limit=${limit}`),
  },

  // ---- DM history (REST fallback) ----
  dm: {
    history: (friendId: string) => request<MessageOut[]>(`/api/dm/history/${friendId}`),
  },
};

// ---- WebSocket helpers ----
export function chatroomWsUrl(): string {
  const token = getToken();
  const base = API_URL.replace(/^http/, 'ws');
  return `${base}/api/chat/ws/chatroom${token ? `?token=${token}` : ''}`;
}

export function dmWsUrl(friendId: string): string {
  const token = getToken();
  const base = API_URL.replace(/^http/, 'ws');
  return `${base}/api/dm/ws/dm/${friendId}${token ? `?token=${token}` : ''}`;
}

// ---- Types ----
export interface UserOut {
  id: string;
  username: string;
  email: string;
  avatar: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface Project {
  id: string;
  user_id: string;
  image_url: string;
  result_json: AnalysisResult | null;
  depth_data: Record<string, unknown> | null;
  created_at: string;
}

export interface AnalysisResult {
  buildingName: string;
  difficulty: string;
  estimatedPieceCount: number;
  estimatedTime: string;
  colorPalette: string[];
  bricks: Brick[];
  steps: Step[];
}

export interface Brick {
  name: string;
  partId: string;
  color: string;
  quantity: number;
  description: string;
}

export interface Step {
  step: number;
  title: string;
  description: string;
  bricksUsed: string[];
  tip?: string;
}

export interface FriendshipOut {
  id: string;
  status: 'pending' | 'accepted';
  is_requester: boolean;
  friend: UserOut;
}

export interface MessageOut {
  id: string;
  sender_id: string;
  sender_username: string;
  sender_avatar: string;
  receiver_id: string | null;
  content: string;
  msg_type: string;
  created_at: string;
}
