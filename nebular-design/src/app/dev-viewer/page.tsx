'use client';

/**
 * Harness for <LegoViewer />, so the viewer can be driven by a browser test
 * without going through login and a 25-second analysis first. Not linked from
 * anywhere; it exists because measuring the camera in Node kept saying the model
 * was centred while the browser kept putting it in a corner, and the difference
 * turned out to be canvas layout — something only a real browser can catch.
 */

import { useEffect, useState } from 'react';
import LegoViewer from '@/components/LegoViewer';

export default function DevViewerPage() {
  const [ldraw, setLdraw] = useState('');
  useEffect(() => {
    fetch('/dev-build.ldr').then(r => r.text()).then(setLdraw);
  }, []);

  if (process.env.NODE_ENV === 'production') {
    return <div className="p-10">Not available.</div>;
  }

  return (
    <div className="bg-lego-bg min-h-screen">
      <div className="max-w-4xl mx-auto px-6 py-14">
        <div className="card-soft p-7" data-testid="card">
          <div className="eyebrow-min mb-2">Finished build</div>
          {ldraw ? <LegoViewer ldraw={ldraw} /> : <p>loading…</p>}
        </div>
      </div>
    </div>
  );
}
