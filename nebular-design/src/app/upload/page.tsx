'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { api, AnalysisResult } from '@/lib/api';

const DIFFICULTY_COLORS: Record<string, string> = {
  Beginner: '#007934', Intermediate: '#FF6B00', Expert: '#E3000B',
};

const LEGO_COLOR_HEX: Record<string, string> = {
  White: '#FFFFFF', 'Light Bluish Gray': '#AFB5C7', 'Dark Bluish Gray': '#595D6E',
  Black: '#1C1C1C', Red: '#E3000B', Blue: '#006DB7', Yellow: '#F7D117',
  Green: '#007934', Orange: '#FF6B00', Transparent: '#E8F4FD', 'Trans-Clear': '#E8F4FD',
  Tan: '#E6C99A', Brown: '#4B2E1A', 'Light Gray': '#D0D0D0', 'Dark Gray': '#595D6E',
};

function ColorSwatch({ color }: { color: string }) {
  const hex = LEGO_COLOR_HEX[color] || '#CCCCCC';
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border-2 border-lego-black text-xs font-bold"
      style={{ background: hex + '33' }}>
      <div className="w-3 h-3 rounded-sm border border-black/30" style={{ background: hex }} />
      {color}
    </div>
  );
}

function ProgressSteps({ current }: { current: number }) {
  const steps = ['Upload', 'Analyzing', 'Results'];
  return (
    <div className="flex items-center justify-center gap-0 mb-10">
      {steps.map((label, i) => (
        <div key={label} className="flex items-center">
          <div className="flex items-center gap-2 px-4 py-2 rounded-md border-2 font-black text-sm transition-all"
            style={{
              background: i <= current ? '#F7D117' : '#F2F2F2',
              borderColor: '#1C1C1C',
              boxShadow: i <= current ? '3px 3px 0 #1C1C1C' : 'none',
            }}>
            <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-black border-2 border-lego-black"
              style={{ background: i < current ? '#007934' : i === current ? '#F7D117' : '#D0D0D0' }}>
              {i < current ? '✓' : i + 1}
            </span>
            {label}
          </div>
          {i < steps.length - 1 && (
            <div className="h-0.5 w-6" style={{ background: i < current ? '#1C1C1C' : '#D0D0D0' }} />
          )}
        </div>
      ))}
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
    <div className="min-h-screen bg-lego-bg py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-10">
          <span className="lego-badge mb-4">AI Builder · DepthAnything + Claude</span>
          <h1 className="font-black text-4xl sm:text-5xl text-lego-black mt-4">Build It with LEGO</h1>
          <p className="text-lego-dark-gray font-semibold mt-3 text-lg">
            Upload a photo → 3D depth analysis → AI brick matching
          </p>
        </div>

        <ProgressSteps current={step} />

        {/* STEP 0 */}
        {step === 0 && (
          <div className="space-y-6">
            {error && (
              <div className="p-4 rounded-md border-2 font-bold text-sm bg-red-50"
                style={{ borderColor: '#E3000B', color: '#E3000B' }}>⚠️ {error}</div>
            )}
            {!preview ? (
              <div {...getRootProps()} className="lego-card p-12 text-center cursor-pointer transition-all"
                style={{
                  background: isDragActive ? '#FFF9D6' : '#FFFFFF',
                  boxShadow: isDragActive ? '8px 8px 0 #F7D117' : '6px 6px 0 #1C1C1C',
                  borderStyle: isDragActive ? 'dashed' : 'solid',
                }}>
                <input {...getInputProps()} />
                <div className="text-6xl mb-4">{isDragActive ? '🎯' : '📸'}</div>
                <h3 className="font-black text-xl text-lego-black mb-2">
                  {isDragActive ? 'Drop it right here!' : 'Upload Your Building Photo'}
                </h3>
                <p className="text-lego-dark-gray font-semibold mb-6">Drag & drop or click to browse</p>
                <div className="btn-lego inline-flex mx-auto">Browse Files</div>
                <p className="text-lego-gray text-sm font-semibold mt-4">JPG, PNG, WebP · Max 15 MB</p>
              </div>
            ) : (
              <div className="lego-card p-6">
                <div className="flex flex-col sm:flex-row gap-6 items-start">
                  <div className="w-full sm:w-48 h-36 rounded-md overflow-hidden border-2 border-lego-black flex-shrink-0">
                    <img src={preview} alt="Preview" className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="w-5 h-5 bg-lego-green rounded-full flex items-center justify-center text-white text-xs font-black">✓</span>
                      <span className="font-black text-lego-black">Photo ready!</span>
                    </div>
                    <p className="text-lego-dark-gray font-semibold text-sm mb-1">{file?.name}</p>
                    <p className="text-lego-gray text-xs font-semibold mb-6">
                      {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : ''}
                    </p>
                    <div className="flex gap-3 flex-wrap">
                      <button onClick={handleAnalyze} className="btn-lego">🧠 Analyze with AI</button>
                      <button onClick={handleReset} className="btn-lego-outline text-sm" style={{ padding: '10px 18px' }}>
                        Change photo
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { icon: '📐', tip: 'DepthAnything V2 extracts 3D structure' },
                { icon: '🧠', tip: 'Claude matches real LEGO parts to depth data' },
                { icon: '☁️', tip: 'Images stored securely (S3 / local)' },
              ].map(({ icon, tip }) => (
                <div key={tip} className="flex items-center gap-3 bg-white rounded-lg p-3 border-2 border-lego-light-gray">
                  <span className="text-2xl">{icon}</span>
                  <span className="text-sm font-bold text-lego-dark-gray">{tip}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 1 */}
        {step === 1 && (
          <div className="lego-card p-10 text-center">
            <div className="text-6xl mb-6 animate-bounce">🧠</div>
            <h2 className="font-black text-2xl text-lego-black mb-3">Analyzing your building...</h2>
            <p className="text-lego-dark-gray font-semibold mb-8">
              DepthAnything is estimating 3D depth → Claude is matching LEGO bricks
            </p>
            <div className="max-w-sm mx-auto">
              <div className="lego-progress mb-3">
                <div className="lego-progress-bar" style={{ width: `${progress}%` }} />
              </div>
              <p className="text-lego-dark-gray font-bold text-sm">{Math.round(progress)}%</p>
            </div>
            <div className="mt-8 flex flex-wrap justify-center gap-3 text-sm font-semibold text-lego-gray">
              {['Uploading to S3...', 'Running DepthAnything...', 'Claude brick matching...'].map((s, i) => (
                <div key={s} className="px-3 py-1 rounded-full border-2"
                  style={{
                    borderColor: progress > i * 30 ? '#007934' : '#D0D0D0',
                    background: progress > i * 30 ? '#EAFAF1' : '#F2F2F2',
                    color: progress > i * 30 ? '#007934' : '#9A9A9A',
                  }}>
                  {progress > i * 30 ? '✓ ' : ''}{s}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 2 */}
        {step === 2 && result && (
          <div className="space-y-6">
            <div className="lego-card p-6 bg-lego-yellow">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="font-black text-2xl text-lego-black">{result.buildingName}</h2>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <span className="lego-badge"
                      style={{ background: DIFFICULTY_COLORS[result.difficulty] || '#888', color: 'white' }}>
                      {result.difficulty}
                    </span>
                    <span className="lego-badge bg-white">🧱 {result.estimatedPieceCount} pieces</span>
                    <span className="lego-badge bg-white">⏱️ {result.estimatedTime}</span>
                  </div>
                </div>
                {displayImage && (
                  <div className="w-24 h-20 rounded-md overflow-hidden border-2 border-lego-black flex-shrink-0">
                    <img src={displayImage} alt="Your building" className="w-full h-full object-cover" />
                  </div>
                )}
              </div>
              {result.colorPalette?.length > 0 && (
                <div className="mt-4">
                  <p className="font-black text-sm text-lego-black mb-2">Color Palette</p>
                  <div className="flex flex-wrap gap-2">
                    {result.colorPalette.map(c => <ColorSwatch key={c} color={c} />)}
                  </div>
                </div>
              )}
            </div>

            <div className="flex border-b-[3px] border-lego-black">
              {(['bricks', 'steps'] as const).map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)}
                  className="px-6 py-3 font-black text-sm capitalize rounded-t-md -mb-[3px] border-t-2 border-x-2"
                  style={{
                    borderColor: '#1C1C1C', background: activeTab === tab ? '#F7D117' : '#F2F2F2',
                    borderBottomColor: activeTab === tab ? '#F7D117' : '#1C1C1C',
                  }}>
                  {tab === 'bricks' ? `🧱 Brick List (${result.bricks.length})` : `📋 Assembly Steps (${result.steps.length})`}
                </button>
              ))}
            </div>

            {activeTab === 'bricks' && (
              <div className="lego-card overflow-hidden" style={{ boxShadow: '6px 6px 0 #1C1C1C' }}>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-lego-black text-lego-yellow">
                        <th className="text-left px-4 py-3 font-black text-sm">#</th>
                        <th className="text-left px-4 py-3 font-black text-sm">Brick Name</th>
                        <th className="text-left px-4 py-3 font-black text-sm hidden sm:table-cell">Part ID</th>
                        <th className="text-left px-4 py-3 font-black text-sm">Color</th>
                        <th className="text-right px-4 py-3 font-black text-sm">Qty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.bricks.map((brick, i) => (
                        <tr key={i} className="border-b-2 border-lego-light-gray hover:bg-lego-yellow/20">
                          <td className="px-4 py-3 font-bold text-lego-gray text-sm">{i + 1}</td>
                          <td className="px-4 py-3">
                            <div className="font-black text-sm text-lego-black">{brick.name}</div>
                            <div className="text-xs text-lego-gray font-semibold hidden sm:block">{brick.description}</div>
                          </td>
                          <td className="px-4 py-3 text-sm font-mono text-lego-dark-gray hidden sm:table-cell">{brick.partId}</td>
                          <td className="px-4 py-3"><ColorSwatch color={brick.color} /></td>
                          <td className="px-4 py-3 text-right font-black text-lg text-lego-black">{brick.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-lego-yellow/30 border-t-2 border-lego-black">
                        <td colSpan={4} className="px-4 py-3 font-black text-sm text-lego-black">Total Pieces</td>
                        <td className="px-4 py-3 text-right font-black text-xl text-lego-black">
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
                  <div key={i} className="lego-card p-6">
                    <div className="flex gap-4 items-start">
                      <div className="w-10 h-10 rounded-md flex items-center justify-center font-black text-white text-lg flex-shrink-0 border-2 border-lego-black"
                        style={{ background: `hsl(${i * 47 % 360},70%,45%)`, boxShadow: '3px 3px 0 #1C1C1C' }}>
                        {s.step}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-black text-lego-black text-lg">{s.title}</h3>
                        <p className="text-lego-dark-gray font-semibold mt-1 leading-relaxed">{s.description}</p>
                        {s.bricksUsed?.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {s.bricksUsed.map((b, j) => (
                              <span key={j} className="px-2.5 py-1 text-xs font-bold rounded border-2 border-lego-black bg-lego-light-gray">
                                🧱 {b}
                              </span>
                            ))}
                          </div>
                        )}
                        {s.tip && (
                          <div className="mt-3 flex items-start gap-2 p-3 rounded-md border-2 border-lego-yellow bg-lego-yellow/20">
                            <span className="text-sm">💡</span>
                            <p className="text-sm font-bold text-lego-black">{s.tip}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex flex-wrap gap-4 justify-center pt-4">
              <button onClick={handleReset} className="btn-lego">📸 Analyze Another Photo</button>
              <button onClick={() => window.print()} className="btn-lego-outline">🖨️ Print Brick List</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
