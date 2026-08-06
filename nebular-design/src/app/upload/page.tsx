'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { api, AnalysisResult } from '@/lib/api';
import { BrickStack, G, WALL } from '@/components/Bricks';
import BuildDetail, { hexToRgba } from '@/components/BuildDetail';
import {
  ImageUp, Check, RefreshCw, Sparkles, Printer, ScanLine, Cpu, Cloud, Layers,
} from 'lucide-react';

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
  const [projectId, setProjectId] = useState<string | null>(null);
  const [buildName, setBuildName] = useState<string | null>(null);
  const [error, setError] = useState('');

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]; if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError('');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.gif'] },
    maxSize: 50 * 1024 * 1024,
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

      setProjectId(project.id);
      if (project.image_url) setImageUrl(project.image_url);
      if (project.result_json) setResult(project.result_json);
      // Claude's name is the starting point, not the stored one — `project.name`
      // stays null until the builder actually types something.
      setBuildName(project.name ?? project.result_json?.buildingName ?? null);

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
    setProjectId(null); setBuildName(null);
  };

  const handleRename = async (name: string) => {
    setBuildName(name);  // optimistic — a rename that fails is not worth a modal
    if (!projectId) return;
    try {
      await api.images.rename(projectId, name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that name');
    }
  };

  // Local-storage mode returns a /static/ path relative to the API, not the
  // frontend. Hardcoding the port here broke as soon as the API moved off 8000.
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const displayImage = imageUrl
    ? (imageUrl.startsWith('/static/') ? `${apiBase}${imageUrl}` : imageUrl)
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
                <p className="text-lego-gray text-sm font-medium mt-5">JPG, PNG, WebP · up to 50 MB</p>
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

        {/* STEP 2 — results. The same view the profile shows, from one component:
            a build that could only be seen fully on the screen that made it was the
            whole complaint. */}
        {step === 2 && result && projectId && (
          <div className="animate-fade-up">
            <BuildDetail
              result={result}
              projectId={projectId}
              title={buildName && buildName !== 'Untitled Structure' ? buildName : null}
              photoUrl={displayImage}
              onRename={handleRename}
              footer={
                <div className="flex flex-wrap gap-4 justify-center pt-4">
                  <button onClick={handleReset} className="btn-pill">
                    <RefreshCw size={16} strokeWidth={2.4} /> Analyze another photo
                  </button>
                  <button onClick={() => window.print()} className="btn-pill-outline">
                    <Printer size={16} strokeWidth={2.2} /> Print brick list
                  </button>
                </div>
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
