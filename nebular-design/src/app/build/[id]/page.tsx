'use client';

/**
 * One saved build, in full.
 *
 * A route rather than a modal on the profile page. The content is a WebGL
 * viewer, a hundred-row parts table and a step list — that is a page, not a
 * dialog, and putting it in one gives a URL you can send to someone and a back
 * button that does the obvious thing. It also keeps the viewer out of a
 * scrolling, animating container: it sizes itself from its parent, and the last
 * round of framing bugs all came from a parent whose size was not what it looked.
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, buildTitle, Project } from '@/lib/api';
import BuildDetail from '@/components/BuildDetail';
import { ArrowLeft, Loader2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function BuildPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem('nebular_user')) { router.push('/login'); return; }
    if (!id) return;
    api.images
      .get(id)
      .then(setProject)
      .catch(e => setError(e instanceof Error ? e.message : 'Could not load that build'));
  }, [id, router]);

  const rename = async (name: string) => {
    if (!project) return;
    // Optimistic: the title is the one thing on this page the builder just typed,
    // and waiting on a round trip to show it back reads as the edit not working.
    setProject({ ...project, name });
    try {
      setProject(await api.images.rename(project.id, name));
    } catch {
      setProject(project);
    }
  };

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-lego-bg px-6">
        <div className="card-soft px-10 py-9 text-center max-w-sm">
          <h1 className="font-extrabold text-xl text-lego-black mb-2">Build not found</h1>
          <p className="text-lego-dark-gray font-medium mb-6">{error}</p>
          <Link href="/profile" className="btn-pill btn-pill-sm mx-auto w-fit">
            <ArrowLeft size={16} strokeWidth={2.4} /> Back to profile
          </Link>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex-1 flex items-center justify-center bg-lego-bg">
        <div className="card-soft px-10 py-8 text-center">
          <Loader2 size={28} className="animate-spin mx-auto mb-3 text-lego-black" />
          <p className="font-bold text-lego-black">Loading build…</p>
        </div>
      </div>
    );
  }

  const photo = project.image_url?.startsWith('/static/')
    ? `${API_URL}${project.image_url}`
    : project.image_url;

  return (
    <div className="bg-lego-bg">
      <div className="max-w-4xl mx-auto px-6 py-10">
        <Link
          href="/profile"
          className="inline-flex items-center gap-1.5 text-sm font-bold text-lego-dark-gray hover:text-lego-black transition-colors mb-7"
        >
          <ArrowLeft size={16} strokeWidth={2.4} /> All builds
        </Link>

        {project.result_json ? (
          <BuildDetail
            result={project.result_json}
            projectId={project.id}
            title={buildTitle(project)}
            photoUrl={photo}
            onRename={rename}
            eyebrow={timeAgo(project.created_at)}
            footer={
              project.depth_data && !('skipped' in project.depth_data) ? (
                <div
                  className="p-5 rounded-2xl text-xs font-mono text-lego-dark-gray"
                  style={{ background: 'rgba(28,28,28,0.04)' }}
                >
                  <p className="font-bold text-lego-black mb-1.5" style={{ fontFamily: 'inherit' }}>
                    Depth analysis · Depth Anything V2
                  </p>
                  <p>
                    Mean depth: {String(project.depth_data.mean_depth ?? '-')} · Edge strength:{' '}
                    {String(project.depth_data.edge_strength ?? '-')}
                  </p>
                  <p>
                    Zone: {String(project.depth_data.dominant_depth_zone ?? '-')} · Complexity:{' '}
                    {String(project.depth_data.geometric_complexity ?? '-')}
                  </p>
                </div>
              ) : null
            }
          />
        ) : (
          <div className="card-soft px-8 py-14 text-center">
            <h1 className="font-extrabold text-xl text-lego-black mb-2">Nothing to show yet</h1>
            <p className="text-lego-dark-gray font-medium">
              This build has no analysis attached — it may have failed partway through.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
