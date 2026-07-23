'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { api, AnalysisResult } from '@/lib/api';
import { BrickStack, G, WALL } from '@/components/Bricks';
import {
  ImageUp, Check, RefreshCw, Sparkles, Printer, ScanLine, Cpu, Cloud,
  Layers, Lightbulb, Boxes, Clock,
} from 'lucide-react';

const DIFFICULTY_COLORS: Record<string, string> = {
  Beginner: '#007934', Intermediate: '#FF6B00', Expert: '#E3000B',
  Medium: '#FF6B00', Hard: '#E3000B',
};

const LEGO_COLOR_HEX: Record<string, string> = {
  White: '#FFFFFF', 'Light Bluish Gray': '#AFB5C7', 'Dark Bluish Gray': '#595D6E',
  Black: '#1C1C1C', Red: '#E3000B', Blue: '#006DB7', Yellow: '#F7D117',
  Green: '#007934', Orange: '#FF6B00', Transparent: '#E8F4FD', 'Trans-Clear': '#E8F4FD',
  Tan: '#E6C99A', Brown: '#4B2E1A', 'Light Gray': '#D0D0D0', 'Dark Gray': '#595D6E',
};

function hexToRgba(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function DifficultyBadge({ level }: { level: string }) {
  const c = DIFFICULTY_COLORS[level] || '#4A4A4A';
  return (
    <span className="badge-soft" style={{ background: hexToRgba(c, 0.14), color: c }}>
      {level}
    </span>
  );
}

function ColorSwatch({ color }: { color: string }) {
  const hex = LEGO_COLOR_HEX[color] || '#CCCCCC';
  return (
    <span className="inline-flex items-center gap-2 pl-2 pr-3 py-1 rounded-full text-xs font-bold text-lego-black"
      style={{ background: 'rgba(28,28,28,0.05)' }}>
      <span className="w-3.5 h-3.5 rounded-full border border-black/15" style={{ background: hex }} />
      {color}
    </span>
  );
}

const STEP_LABELS = ['Upload', 'Analyzing', 'Results'];

function ProgressSteps({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-12">
      {STEP_LABELS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <div key={label} className="flex items-center gap-2">
            <div className="flex items-center gap-2.5">
              <span
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-black transition-colors"
                style={{
                  background: done ? '#1C1C1C' : active ? '#F7D117' : 'rgba(28,28,28,0.07)',
                  color: done ? '#fff' : active ? '#1C1C1C' : '#9A9A9A',
                }}
              >
                {done ? <Check size={14} strokeWidth={3} /> : i + 1}
              </span>
              <span className="text-sm font-bold hidden sm:block"
                style={{ color: done || active ? '#1C1C1C' : '#9A9A9A' }}>
                {label}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <span className="w-8 h-px mx-1" style={{ background: done ? '#1C1C1C' : 'rgba(28,28,28,0.12)' }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function UploadPage() {
  const [step, setStep] = useState<0 | 1 | 2>(0);
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'bricks' | 'steps'>('bricks');

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]; if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError('');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.gif'] },
    maxSize: 15 * 1024 * 1024,
    multiple: false,
  });

  const handleAnalyze = async () => {
    if (!file) return;
    const token = localStorage.getItem('nebular_token');
    if (!token) { setError('请先登录再上传'); return; }

    setStep(1); setError('');

    let p = 0;
    const interval = setInterval(() => {
      p += Math.random() * 8;
      if (p >= 85) { p = 85; clearInterval(interval); }
      setProgress(Math.min(p, 85));
    }, 500);

    try {
      const formData = new FormData();
      formData.append('image', file);

      // POST to Python FastAPI backend — runs S3 upload + DepthAnything + Claude in parallel
      const project = await api.images.upload(formData);

      clearInterval(interval);
      setProgress(100);

      if (project.image_url) setImageUrl(project.image_url);
      if (project.result_json) setResult(project.result_json);

      setTimeout(() => setStep(2), 400);
    } catch (err) {
      clearInterval(interval);
      setError(err instanceof Error ? err.message : '分析失败，请重试');
      setStep(0); setProgress(0);
    }
  };

  const handleReset = () => {
    setStep(0); setPreview(null); setFile(null);
    setProgress(0); setResult(null); setImageUrl(null); setError('');
  };

  const displayImage = imageUrl
    ? (imageUrl.startsWith('/static/') ? `http://localhost:8000${imageUrl}` : imageUrl)
    : preview;

  return (
    <div className="bg-lego-bg">
      <div className="max-w-4xl mx-auto px-6 py-14 sm:py-20">
        {/* Header */}
        <div className="text-center max-w-xl mx-auto mb-12 animate-fade-up">
          <div className="eyebrow-min mb-5">AI LEGO studio</div>
          <h1 className="display-xl text-lego-black mb-5" style={{ fontSize: 'clamp(2.2rem, 5vw, 3.4rem)' }}>
            Build it in bricks.
          </h1>
          <p className="text-lego-dark-gray text-lg font-medium leading-relaxed">
            Upload a photo. Depth analysis reads the geometry, then the AI matches every real LEGO part.
          </p>
        </div>

        <ProgressSteps current={step} />

        {/* STEP 0 — upload */}
        {step === 0 && (
          <div className="space-y-6 animate-fade-up">
            {error && (
              <div className="rounded-2xl px-5 py-4 font-semibold text-sm"
                style={{ background: hexToRgba('#E3000B', 0.08), color: '#E3000B' }}>
                {error}
              </div>
            )}

            {!preview ? (
              <div {...getRootProps()}
                className="card-soft card-hover cursor-pointer text-center px-8 py-16 transition-colors"
                style={{
                  background: isDragActive ? hexToRgba('#F7D117', 0.12) : '#FFFFFF',
                  outline: isDragActive ? '2px dashed #F7D117' : '1px dashed rgba(28,28,28,0.14)',
                  outlineOffset: '-10px',
                }}>
                <input {...getInputProps()} />
                <BrickStack
                  ns="upload-hero"
                  bricks={[
                    { ox: 0, oy: 0, oz: 0, w: 3, d: 2, ...G.sky },
                    { ox: 0.5, oy: 0.5, oz: WALL, w: 2, d: 1, ...G.yellow },
                  ]}
                  unit={30}
                  className={`w-28 h-auto mx-auto mb-7 brick-shadow ${isDragActive ? 'animate-drift' : ''}`}
                />
                <div className="inline-flex items-center gap-2 mb-2 text-lego-black">
                  <ImageUp size={20} strokeWidth={2.2} />
                  <h3 className="font-extrabold text-xl">
                    {isDragActive ? 'Drop it right here' : 'Upload your building photo'}
                  </h3>
                </div>
                <p className="text-lego-dark-gray font-medium mb-7">Drag and drop, or click to browse</p>
                <span className="btn-pill btn-pill-sm mx-auto">Browse files</span>
                <p className="text-lego-gray text-sm font-medium mt-5">JPG, PNG, WebP · up to 15 MB</p>
              </div>
            ) : (
              <div className="card-soft p-6">
                <div className="flex flex-col sm:flex-row gap-6 items-start">
                  <div className="w-full sm:w-52 h-40 rounded-2xl overflow-hidden flex-shrink-0"
                    style={{ boxShadow: '0 12px 24px rgba(28,28,28,0.10)' }}>
                    <img src={preview} alt="Preview" className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1">
                    <div className="inline-flex items-center gap-2 mb-3 text-lego-green font-extrabold">
                      <span className="w-6 h-6 rounded-full bg-lego-green flex items-center justify-center text-white">
                        <Check size={14} strokeWidth={3} />
                      </span>
                      Photo ready
                    </div>
                    <p className="text-lego-black font-bold text-sm mb-1 truncate">{file?.name}</p>
                    <p className="text-lego-gray text-xs font-medium mb-7">
                      {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : ''}
                    </p>
                    <div className="flex gap-3 flex-wrap">
                      <button onClick={handleAnalyze} className="btn-pill btn-pill-sm">
                        <Sparkles size={16} strokeWidth={2.4} /> Analyze with AI
                      </button>
                      <button onClick={handleReset} className="btn-pill-outline btn-pill-sm">
                        Change photo
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="grid sm:grid-cols-3 gap-4 pt-2">
              {[
                { Icon: Layers, tip: 'DepthAnything V2 extracts 3D structure' },
                { Icon: Cpu, tip: 'Claude matches real LEGO parts to depth data' },
                { Icon: Cloud, tip: 'Images stored securely on S3 or local' },
              ].map(({ Icon, tip }) => (
                <div key={tip} className="flex items-start gap-3 rounded-2xl px-4 py-4 bg-white/60">
                  <span className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: hexToRgba('#F7D117', 0.22), color: '#1C1C1C' }}>
                    <Icon size={18} strokeWidth={2.2} />
                  </span>
                  <span className="text-sm font-semibold text-lego-dark-gray leading-snug">{tip}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 1 — analyzing */}
        {step === 1 && (
          <div className="card-soft px-8 py-14 text-center max-w-xl mx-auto">
            <BrickStack
              ns="analyzing"
              bricks={[
                { ox: 0, oy: 0, oz: 0, w: 2, d: 2, ...G.lilac },
                { ox: 0, oy: 0.5, oz: WALL, w: 2, d: 1, ...G.coral },
                { ox: 0.5, oy: 0.5, oz: WALL * 2, w: 1, d: 1, ...G.yellow },
              ]}
              unit={30}
              className="w-32 h-auto mx-auto mb-8 brick-shadow animate-drift"
            />
            <h2 className="font-extrabold text-2xl text-lego-black mb-3">Analyzing your building</h2>
            <p className="text-lego-dark-gray font-medium mb-9 max-w-sm mx-auto leading-relaxed">
              Estimating 3D depth, then matching LEGO bricks to the geometry.
            </p>
            <div className="max-w-sm mx-auto">
              <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(28,28,28,0.08)' }}>
                <div className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${progress}%`, background: '#F7D117' }} />
              </div>
              <p className="text-lego-dark-gray font-bold text-sm mt-3">{Math.round(progress)}%</p>
            </div>
            <div className="mt-9 flex flex-wrap justify-center gap-2.5 text-sm font-semibold">
              {[
                { label: 'Uploading', Icon: Cloud },
                { label: 'Depth mapping', Icon: ScanLine },
                { label: 'Brick matching', Icon: Cpu },
              ].map(({ label, Icon }, i) => {
                const on = progress > i * 30;
                return (
                  <span key={label} className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full transition-colors"
                    style={{
                      background: on ? hexToRgba('#007934', 0.1) : 'rgba(28,28,28,0.05)',
                      color: on ? '#007934' : '#9A9A9A',
                    }}>
                    {on ? <Check size={13} strokeWidth={3} /> : <Icon size={13} strokeWidth={2.2} />}
                    {label}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 2 — results */}
        {step === 2 && result && (
          <div className="space-y-6 animate-fade-up">
            {/* Summary */}
            <div className="card-soft p-7">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
                <div>
                  <div className="eyebrow-min mb-2">Your build</div>
                  <h2 className="font-extrabold text-3xl text-lego-black tracking-tight">{result.buildingName}</h2>
                  <div className="flex flex-wrap gap-2 mt-4">
                    <DifficultyBadge level={result.difficulty} />
                    <span className="badge-soft"><Boxes size={14} strokeWidth={2.2} /> {result.estimatedPieceCount} pieces</span>
                    <span className="badge-soft"><Clock size={14} strokeWidth={2.2} /> {result.estimatedTime}</span>
                  </div>
                </div>
                {displayImage && (
                  <div className="w-full sm:w-32 h-24 rounded-2xl overflow-hidden flex-shrink-0"
                    style={{ boxShadow: '0 12px 24px rgba(28,28,28,0.10)' }}>
                    <img src={displayImage} alt="Your building" className="w-full h-full object-cover" />
                  </div>
                )}
              </div>
              {result.colorPalette?.length > 0 && (
                <div className="mt-6 pt-6 border-t hairline">
                  <p className="font-bold text-sm text-lego-black mb-3">Colour palette</p>
                  <div className="flex flex-wrap gap-2">
                    {result.colorPalette.map(c => <ColorSwatch key={c} color={c} />)}
                  </div>
                </div>
              )}
            </div>

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
                          <td className="px-5 py-4"><ColorSwatch color={brick.color} /></td>
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

            <div className="flex flex-wrap gap-4 justify-center pt-4">
              <button onClick={handleReset} className="btn-pill">
                <RefreshCw size={16} strokeWidth={2.4} /> Analyze another photo
              </button>
              <button onClick={() => window.print()} className="btn-pill-outline">
                <Printer size={16} strokeWidth={2.2} /> Print brick list
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
