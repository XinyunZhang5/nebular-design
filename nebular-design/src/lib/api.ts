const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('nebular_token');
}

/** Endpoints where a 401 is the answer, not a stale session. */
const AUTH_PATHS = ['/api/auth/login', '/api/auth/register'];

/**
 * A token lasts seven days and nothing renews it, so every session ends in a
 * 401 eventually. That used to surface as the backend's own words in a red bar
 * on whatever page you were on — "Invalid or expired token", over a photo that
 * was ready to go, with no way to tell that signing in again would fix it.
 *
 * Signing out here rather than at each call site because there is no auth
 * context to put it in: the token is read straight from localStorage in eight
 * places, and every one of them would have to remember to do this.
 */
function sessionExpired(path: string): boolean {
  if (typeof window === 'undefined') return false;
  if (AUTH_PATHS.some((p) => path.startsWith(p))) return false;
  localStorage.removeItem('nebular_token');
  localStorage.removeItem('nebular_user');
  window.location.href = '/login?expired=1';
  return true;
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
    if (res.status === 401 && sessionExpired(path)) {
      // The redirect is already under way; this only stops the caller from
      // painting an error over a page that is about to be replaced.
      throw new Error('Your session has expired. Please sign in again.');
    }
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Same auth and error handling, for endpoints that answer with text. */
async function requestText(path: string): Promise<string> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    if (res.status === 401 && sessionExpired(path)) {
      throw new Error('Your session has expired. Please sign in again.');
    }
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.text();
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

    /** One project by id. Owner-only; 404 for anyone else, so a leaked id
     *  discloses nothing. The path is `/status/` for historical reasons — it was
     *  written for polling an in-flight analysis. */
    get: (projectId: string) => request<Project>(`/api/images/status/${projectId}`),

    rename: (projectId: string, name: string) =>
      request<Project>(`/api/images/${projectId}`, {
        method: 'PATCH',
        body: JSON.stringify({ name }),
      }),

    /** The LDraw model, fetched separately from the plan.
     *
     *  It is 80 KB — most of a plan — and only the viewer and the download button
     *  want it. Inlined, it made /history a four-megabyte response for a page of
     *  thumbnails. Ask for it when something is actually going to render it. */
    ldraw: (projectId: string) => requestText(`/api/images/${projectId}/ldraw`),
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

    // Declines a request. The row is kept but hidden from both sides — the sender is
    // never told. They can send a new request later. Use `remove` to drop an existing
    // friendship instead.
    reject: (friendshipId: string) =>
      request<FriendshipOut>(`/api/friends/reject/${friendshipId}`, { method: 'POST' }),

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
  /** The builder's own title. Null until they rename it; fall back to
   *  `result_json.buildingName`, which is what Claude called the build. */
  name: string | null;
  result_json: AnalysisResult | null;
  depth_data: Record<string, unknown> | null;
  created_at: string;
}

export interface AnalysisResult {
  buildingName: string;
  difficulty: string;
  estimatedPieceCount: number;
  estimatedTime: string;
  /** Colours used on visible surfaces, most-used first. Projects analysed before
   *  the catalogue shipped hex values stored bare name strings — see
   *  `normalisePalette` for the reader that copes with both. */
  colorPalette: (PaletteEntry | string)[];
  bricks: Brick[];
  steps: Step[];
  // Everything below is produced by the geometry pipeline, so it is absent on
  // projects created before it landed — treat it all as optional.
  visiblePieceCount?: number;
  hiddenPieceCount?: number;
  /** The model's size. `width` is studs across the facade, `courses` is bricks
   *  tall, `depth` is studs from the back plane to the nearest point of the front. */
  grid?: {
    width: number;
    courses: number;
    depth: number;
    sizeCm: { width: number; height: number; depth: number };
    cells: number;
    buildingCells: number;
    coverage: number;
  };
  base?: { name: string; quantity: number; widthStuds: number; depthStuds: number };
  /** How much the build looks like the photo it came from — see backend score.py.
   *  `colourDeltaE` is CIEDE2000: under ~3 reads as the same colour, over ~10 as a
   *  plainly different one. `silhouette` is how much of the intended shape survived
   *  the build, not how well the photo was segmented — it sits near 1.0 on a good
   *  run and only drops when the pipeline discarded something. */
  fidelity?: {
    silhouette: number;
    colourDeltaE: number;
    detail: number;
    /** How well the built depth follows the depth the photo implies. */
    relief: number;
    overall: number;
  };
  /** Which settings the backend searched, and what it picked. Two photos rarely
   *  want the same ones, which is why there is a search and not a default. */
  search?: {
    tried: number;
    chosen: { studs: number; relief: number; colours: number };
    ranking: { studs: number; relief: number; colours: number; overall: number; pieces: number }[];
  };
  /** Each pass of the refinement loop and whether it was kept. A round that was
   *  discarded is still listed — it is the only way to tell a loop that helped
   *  from one that merely ran. */
  refine?: {
    rounds: { round: number; overall: number; worstTileDeltaE?: number; kept?: boolean }[];
    improved: number;
  };
  /** What will and will not hold itself up — see the backend's _support(). */
  structure?: {
    overhangs: number;
    lintels: number;
    longestLintelStuds: number;
    floatingRuns: number;
    longestFloatingStuds: number;
    spansNeedingSupport: number;
    sound: boolean;
  };
  /** Whether there is an LDraw model to fetch — see `api.images.ldraw`. The
   *  source itself is never inlined here; it is 80 KB and wanted on one screen. */
  hasLdraw?: boolean;
  previewUrl?: string;
  isometricUrl?: string;
  /** Written by Claude from the computed plan — prose only, never numbers.
   *  The only prose fields are this, `buildingName`, and the per-step titles.
   *  Projects analysed earlier also carry architecturalStyle / recognised / tips;
   *  nothing ever rendered them, so they are no longer requested or typed. */
  description?: string;
  segmentation?: { buildingShare: number; composition: Record<string, number> };
}

/**
 * What to call a build, or null if it still has no real name.
 *
 * "Untitled Structure" is the backend's fallback for when Claude could not
 * recognise the subject. It is not a title — surfacing it as one leaves the
 * builder with a name they did not choose and no hint that they can change it.
 */
export function buildTitle(project: Pick<Project, 'name' | 'result_json'>): string | null {
  if (project.name) return project.name;
  const claude = project.result_json?.buildingName;
  return claude && claude !== 'Untitled Structure' ? claude : null;
}

export interface PaletteEntry {
  name: string;
  /** `#RRGGBB`, straight from the Rebrickable catalogue on the backend. */
  hex: string;
  colorId: number;
  quantity: number;
}

export interface Brick {
  name: string;
  partId: string;
  color: string;
  colorId?: number;
  colorHex?: string;
  quantity: number;
  description: string;
}

/**
 * Read a palette in either shape.
 *
 * The backend used to send `["Black", "Sand Blue", …]` and the page carried its
 * own name→hex table to draw the swatches. That table only knew the fifteen
 * colours of the original hand-written catalogue, so every colour added since —
 * Medium Nougat, Dark Orange, Reddish Brown — silently rendered grey. The hex now
 * comes from the backend, but projects analysed before that still hold plain
 * strings, so both shapes have to read.
 */
export function normalisePalette(
  palette: AnalysisResult['colorPalette'] | undefined,
  bricks: Brick[] = [],
): { name: string; hex: string | null }[] {
  if (!palette?.length) return [];
  // Older rows have no hex on the palette but may have one on the brick rows.
  const fromBricks = new Map(
    bricks.filter((b) => b.colorHex).map((b) => [b.color, b.colorHex!]),
  );
  return palette.map((entry) =>
    typeof entry === 'string'
      ? { name: entry, hex: fromBricks.get(entry) ?? null }
      : { name: entry.name, hex: entry.hex },
  );
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
  // 'rejected' is only ever seen on the response to a reject call — the list endpoint
  // filters those rows out for both parties.
  status: 'pending' | 'accepted' | 'rejected';
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
