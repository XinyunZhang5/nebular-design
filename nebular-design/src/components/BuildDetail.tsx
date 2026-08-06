'use client';

/**
 * Everything there is to see about one build: the model in 3D, the parts, the
 * steps.
 *
 * This lives in a component rather than on the upload page because it is wanted
 * in two places. A build used to be fully visible exactly once — on the screen
 * that produced it — and every later visit from the profile got a thumbnail, a
 * piece count and a paragraph. The thing a builder actually comes back for is the
 * viewer and the step list, and those were unreachable after the tab was closed.
 */

import { useEffect, useState, ReactNode } from 'react';
import { api, AnalysisResult, normalisePalette } from '@/lib/api';
import LegoViewer from '@/components/LegoViewer';
import { Boxes, Clock, Lightbulb, Pencil, Loader2 } from 'lucide-react';

const DIFFICULTY_COLORS: Record<string, string> = {
  Beginner: '#007934', Intermediate: '#FF6B00', Expert: '#E3000B',
  Medium: '#FF6B00', Hard: '#E3000B',
};

export function hexToRgba(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

export function DifficultyBadge({ level, className = '' }: { level: string; className?: string }) {
  const c = DIFFICULTY_COLORS[level] || '#4A4A4A';
  return (
    <span className={`badge-soft ${className}`} style={{ background: hexToRgba(c, 0.14), color: c }}>
      {level}
    </span>
  );
}

/** A palette chip. The swatch is a stud, not a dot — same light angle as every
 *  other brick on the site, so the colour reads as plastic rather than as ink. */
export function ColorSwatch({ name, hex, share }: { name: string; hex: string | null; share?: number }) {
  return (
    <span
      className="inline-flex items-center gap-2 pl-1.5 pr-3 py-1 rounded-full text-xs font-bold text-lego-black"
      style={{ background: 'rgba(28,28,28,0.05)' }}
      title={share ? `${name} — ${share} pieces` : name}
    >
      {hex ? (
        <span
          className="w-4 h-4 rounded-full flex-shrink-0"
          style={{
            background: `radial-gradient(circle at 34% 30%, ${hexToRgba(hex, 1)} 0%, ${hex} 55%, ${hex} 100%)`,
            boxShadow: `inset 0 1.5px 2px rgba(255,255,255,0.45), inset 0 -1.5px 2px rgba(0,0,0,0.30), 0 0 0 1px rgba(28,28,28,0.12)`,
          }}
        />
      ) : (
        // Only reachable on projects analysed before the backend sent hex codes.
        <span className="w-4 h-4 rounded-full flex-shrink-0 border border-dashed border-black/25" />
      )}
      {name}
    </span>
  );
}

/** Click-to-edit build title. Falls back to plain text when there is no handler,
 *  so a read-only context does not offer an edit that would fail. */
export function BuildTitle({
  value,
  placeholder,
  onSave,
}: {
  value: string | null;
  placeholder: string;
  onSave?: (name: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? '');
  const [saving, setSaving] = useState(false);

  if (!onSave) {
    return (
      <h1 className={`font-extrabold text-3xl tracking-tight ${value ? 'text-lego-black' : 'text-lego-black/30'}`}>
        {value || placeholder}
      </h1>
    );
  }

  const commit = async () => {
    const next = draft.trim();
    setEditing(false);
    if (!next || next === value) { setDraft(value ?? ''); return; }
    setSaving(true);
    try { await onSave(next); } finally { setSaving(false); }
  };

  if (editing) {
    return (
      <input
        autoFocus
        maxLength={120}
        value={draft}
        placeholder={placeholder}
        onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={e => {
          if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur(); }
          if (e.key === 'Escape') { setDraft(value ?? ''); setEditing(false); }
        }}
        className="font-extrabold text-3xl tracking-tight bg-transparent outline-none w-full max-w-lg
                   border-b-2 border-lego-yellow pb-0.5 text-lego-black placeholder:text-lego-black/25"
      />
    );
  }

  return (
    <button
      type="button"
      onClick={() => { setDraft(value ?? ''); setEditing(true); }}
      // The pencil only appears on hover: an always-visible icon next to a
      // heading reads as chrome, and the whole heading is the hit target anyway.
      className="group inline-flex items-center gap-2 text-left font-extrabold text-3xl tracking-tight
                 border-b-2 border-transparent hover:border-black/10 transition-colors pb-0.5"
      title="Click to rename"
    >
      <span className={value ? 'text-lego-black' : 'text-lego-black/30'}>
        {value || placeholder}
      </span>
      <Pencil
        size={16}
        strokeWidth={2.4}
        className="flex-shrink-0 opacity-0 group-hover:opacity-45 transition-opacity"
      />
      {saving && <Loader2 size={15} className="animate-spin opacity-45" />}
    </button>
  );
}

export default function BuildDetail({
  result,
  projectId,
  title,
  photoUrl,
  onRename,
  eyebrow = 'Your build',
  footer,
}: {
  result: AnalysisResult;
  /** Which build to fetch the LDraw model from. */
  projectId: string;
  title: string | null;
  photoUrl?: string | null;
  /** Omit to render the title read-only. */
  onRename?: (name: string) => Promise<void>;
  eyebrow?: string;
  footer?: ReactNode;
}) {
  const [activeTab, setActiveTab] = useState<'bricks' | 'steps'>('bricks');
  const [ldraw, setLdraw] = useState<string | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);

  // The model is no longer part of the plan — it is 80 KB and only this screen
  // wants it. Fetched here rather than by each caller so that both the upload
  // page and the saved-build page get it without knowing they had to ask.
  useEffect(() => {
    if (!result.hasLdraw || !projectId) return;
    let live = true;
    setLdraw(null);
    setModelError(null);
    api.images
      .ldraw(projectId)
      .then(text => { if (live) setLdraw(text); })
      .catch(e => {
        if (live) setModelError(e instanceof Error ? e.message : 'Could not load the model');
      });
    return () => { live = false; };
  }, [projectId, result.hasLdraw]);

  const download = () => {
    if (!ldraw) return;
    const url = URL.createObjectURL(new Blob([ldraw], { type: 'text/plain' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(title || 'nebular-build').replace(/[^\w-]+/g, '_')}.ldr`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="card-soft p-7">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="min-w-0">
            <div className="eyebrow-min mb-2">{eyebrow}</div>
            {/* Claude's "Untitled Structure" is a non-answer, so it is shown as an
                empty placeholder rather than as a title the builder has to notice
                is wrong. */}
            <BuildTitle value={title} placeholder="Name your build" onSave={onRename} />
            <div className="flex flex-wrap gap-2 mt-4">
              <DifficultyBadge level={result.difficulty} />
              <span className="badge-soft"><Boxes size={14} strokeWidth={2.2} /> {result.estimatedPieceCount} pieces</span>
              <span className="badge-soft"><Clock size={14} strokeWidth={2.2} /> {result.estimatedTime}</span>
            </div>
          </div>
          {photoUrl && (
            <div className="w-full sm:w-32 h-24 rounded-2xl overflow-hidden flex-shrink-0"
              style={{ boxShadow: '0 12px 24px rgba(28,28,28,0.10)' }}>
              <img src={photoUrl} alt="Your building" className="w-full h-full object-cover" />
            </div>
          )}
        </div>
        {result.description && (
          <p className="mt-5 text-[15px] leading-relaxed text-lego-black/70 max-w-2xl">
            {result.description}
          </p>
        )}
        {result.colorPalette?.length > 0 && (
          <div className="mt-6 pt-6 border-t hairline">
            <p className="font-bold text-sm text-lego-black mb-3">Colour palette</p>
            <div className="flex flex-wrap gap-2">
              {normalisePalette(result.colorPalette, result.bricks).map(c => (
                <ColorSwatch key={c.name} name={c.name} hex={c.hex} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Finished build, in 3D. Real part geometry via LDraw. */}
      {result.hasLdraw && (
        <div className="card-soft p-7">
          <div className="flex flex-wrap items-baseline justify-between gap-3 mb-5">
            <div>
              <div className="eyebrow-min mb-2">Finished build</div>
              <p className="text-sm text-lego-black/60">
                Drag to move, scroll to zoom, right-drag to turn it. The slider
                replays it course by course.
                {result.grid && (
                  <>
                    {' '}Built, it stands{' '}
                    <strong className="text-lego-black">
                      {result.grid.sizeCm.width} × {result.grid.sizeCm.height} ×{' '}
                      {result.grid.sizeCm.depth} cm
                    </strong>
                    .
                  </>
                )}
              </p>
            </div>
            <button
              onClick={download}
              disabled={!ldraw}
              className="btn-ghost text-sm disabled:opacity-40"
            >
              Download .ldr
            </button>
          </div>
          {/* Three states, all of them said out loud. The viewer used to appear
              with the plan; now it waits on a second request, and a panel that is
              silently blank for a second reads as broken. */}
          {ldraw ? (
            <LegoViewer ldraw={ldraw} />
          ) : (
            <div
              className="flex items-center justify-center gap-2.5 rounded-2xl text-sm font-semibold text-lego-dark-gray"
              style={{ background: 'rgba(28,28,28,0.04)', minHeight: 320 }}
            >
              {modelError ? (
                <span style={{ color: '#B45309' }}>{modelError}</span>
              ) : (
                <>
                  <Loader2 size={16} className="animate-spin" /> Loading the model…
                </>
              )}
            </div>
          )}
          {/* Said plainly rather than hidden: a model with a long span that needs
              reinforcing is still worth building, but you want to know before you
              buy the parts. */}
          {result.structure && !result.structure.sound && (
            <p className="mt-4 text-xs font-semibold" style={{ color: '#B45309' }}>
              {result.structure.spansNeedingSupport} span
              {result.structure.spansNeedingSupport === 1 ? '' : 's'} in this model have
              nothing beneath them — the longest runs {result.structure.longestFloatingStuds}{' '}
              studs. Bricks alone will sag there; back them with a plate across the joint
              or a beam behind.
            </p>
          )}
          <p className="mt-4 text-xs text-lego-black/50">
            The .ldr file opens in BrickLink Studio 2.0, LeoCAD or LDView — Studio also
            generates printable instructions and can order every part in one click.
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-7 border-b hairline">
        <button onClick={() => setActiveTab('bricks')} data-active={activeTab === 'bricks'} className="tab-underline">
          Brick list ({result.bricks.length})
        </button>
        <button onClick={() => setActiveTab('steps')} data-active={activeTab === 'steps'} className="tab-underline">
          Assembly steps ({result.steps.length})
        </button>
      </div>

      {activeTab === 'bricks' && (
        <div className="card-soft overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-lego-gray">
                  <th className="px-5 py-3.5 font-bold text-xs uppercase tracking-wider">#</th>
                  <th className="px-5 py-3.5 font-bold text-xs uppercase tracking-wider">Brick</th>
                  <th className="px-5 py-3.5 font-bold text-xs uppercase tracking-wider hidden sm:table-cell">Part ID</th>
                  <th className="px-5 py-3.5 font-bold text-xs uppercase tracking-wider">Colour</th>
                  <th className="px-5 py-3.5 font-bold text-xs uppercase tracking-wider text-right">Qty</th>
                </tr>
              </thead>
              <tbody className="divide-y hairline">
                {result.bricks.map((brick, i) => (
                  <tr key={i} className="transition-colors hover:bg-lego-yellow/[0.07]">
                    <td className="px-5 py-4 font-semibold text-lego-gray">{i + 1}</td>
                    <td className="px-5 py-4">
                      <div className="font-bold text-lego-black">{brick.name}</div>
                      <div className="text-xs text-lego-gray font-medium hidden sm:block">{brick.description}</div>
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-lego-dark-gray hidden sm:table-cell">{brick.partId}</td>
                    <td className="px-5 py-4">
                      <ColorSwatch name={brick.color} hex={brick.colorHex ?? null} />
                    </td>
                    <td className="px-5 py-4 text-right font-extrabold text-lego-black tabular-nums">{brick.quantity}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t hairline bg-lego-yellow/[0.14]">
                  <td colSpan={4} className="px-5 py-4 font-bold text-lego-black">Total pieces</td>
                  <td className="px-5 py-4 text-right font-extrabold text-lg text-lego-black tabular-nums">
                    {result.bricks.reduce((s, b) => s + b.quantity, 0)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'steps' && (
        <div className="space-y-4">
          {result.steps.map((s, i) => (
            <div key={i} className="card-soft p-6">
              <div className="flex gap-4 items-start">
                <div className="w-10 h-10 rounded-2xl flex items-center justify-center font-extrabold text-lego-black text-lg flex-shrink-0"
                  style={{ background: hexToRgba('#F7D117', 0.9) }}>
                  {s.step}
                </div>
                <div className="flex-1">
                  <h3 className="font-extrabold text-lego-black text-lg">{s.title}</h3>
                  <p className="text-lego-dark-gray font-medium mt-1 leading-relaxed">{s.description}</p>
                  {s.bricksUsed?.length > 0 && (
                    <div className="mt-3.5 flex flex-wrap gap-2">
                      {s.bricksUsed.map((b, j) => (
                        <span key={j} className="badge-soft"><Boxes size={13} strokeWidth={2.2} /> {b}</span>
                      ))}
                    </div>
                  )}
                  {s.tip && (
                    <div className="mt-4 flex items-start gap-2.5 px-4 py-3 rounded-2xl"
                      style={{ background: hexToRgba('#F7D117', 0.14) }}>
                      <Lightbulb size={16} strokeWidth={2.2} className="text-lego-black mt-0.5 flex-shrink-0" />
                      <p className="text-sm font-semibold text-lego-black leading-relaxed">{s.tip}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {footer}
    </div>
  );
}
