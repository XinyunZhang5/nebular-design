'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * Renders a finished build in 3D from its LDraw source.
 *
 * The geometry is real: LDrawLoader resolves each `3024.dat` reference against
 * the official part files in /public/ldraw, so what you see is the actual moulded
 * shape of the plate, studs and all — not a stand-in cube.
 *
 * Only the twelve parts this project can emit are bundled (44 files including
 * primitives, 176 KB). The full LDraw library is over 100 MB; shipping the whole
 * thing to render eleven plate sizes would be silly.
 */
export default function LegoViewer({
  ldraw,
  className = '',
}: {
  ldraw: string;
  className?: string;
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [step, setStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);
  const apiRef = useRef<{ showUpTo: (n: number) => void } | null>(null);
  // Orbiting can lose the panel off-screen; this puts it back.
  const resetRef = useRef<(() => void) | null>(null);
  const reframeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!ldraw || !mountRef.current) return;
    const mount = mountRef.current;
    let disposed = false;
    let cleanup = () => {};

    (async () => {
      const THREE = await import('three');
      const { LDrawLoader } = await import('three/examples/jsm/loaders/LDrawLoader.js');
      const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');
      // The loader no longer ships its own conditional-line material: the shader
      // differs between WebGLRenderer and WebGPURenderer, so the type has to be
      // injected. Without it, parsing throws before a single brick is drawn.
      const { LDrawConditionalLineMaterial } = await import(
        'three/examples/jsm/materials/LDrawConditionalLineMaterial.js'
      );
      if (disposed) return;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xf4f2ee);

      const camera = new THREE.PerspectiveCamera(38, 1, 1, 20000);
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      mount.appendChild(renderer.domElement);

      scene.add(new THREE.AmbientLight(0xffffff, 1.6));
      const key = new THREE.DirectionalLight(0xffffff, 2.4);
      key.position.set(-1, 2, 1.4);
      scene.add(key);
      const fill = new THREE.DirectionalLight(0xffffff, 0.8);
      fill.position.set(1.4, 0.6, -1);
      scene.add(fill);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      // Dragging moves the model, it does not spin it. Most of the time you are
      // reading the facade and want to get to a corner of it; orbiting is the
      // occasional gesture, so it moves to the right button.
      controls.mouseButtons = {
        LEFT: THREE.MOUSE.PAN,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.ROTATE,
      };
      controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
      // Pan along the screen plane rather than the ground plane — on a model this
      // is what "drag it left" means to anyone who has used an image viewer.
      controls.screenSpacePanning = true;

      const loader = new LDrawLoader();
      loader.setConditionalLineMaterial(LDrawConditionalLineMaterial);
      loader.setPartsLibraryPath('/ldraw/');
      loader.smoothNormals = true;

      try {
        await loader.preloadMaterials('/ldraw/LDConfig.ldr');
        if (disposed) return;

        const model: any = await new Promise((resolve, reject) =>
          loader.parse(ldraw, resolve, reject),
        );
        if (disposed) return;

        // The model already stands: the backend builds courses of bricks upward
        // from a baseplate, so the only correction needed is that LDraw's +Y points
        // down while three.js's points up. No quarter turn — an earlier version had
        // one because the build was a mosaic lying flat, and that is no longer what
        // gets made.
        model.rotation.x = Math.PI;
        scene.add(model);

        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        model.position.sub(box.getCenter(new THREE.Vector3()));
        // setFromObject refreshed the world matrices, but moving the model has just
        // invalidated them again. Anything read out of matrixWorld below would
        // otherwise be a whole model-width out of place.
        model.updateMatrixWorld(true);
        controls.target.set(0, 0, 0);

        /**
         * Square on, at the height the photo was taken from — the whole point of
         * the panel is that it reproduces that photograph, so the default view is
         * the one that matches it. Any tilt trades likeness for a sense of depth,
         * and on a panel this thin (48 LDU against 1900 wide) that trade is a bad
         * one: it buys a sliver of shading and costs the picture. Dragging still
         * orbits, so the relief is one gesture away.
         */
        // Sample points that bound the model on screen: the corners of every
        // brick's own box, in world space. The model's overall box will not do —
        // it is symmetric about the origin, so its projection is symmetric too and
        // any correction computed from it is exactly zero, every time. The
        // asymmetry that pushes the picture off centre lives in where the bricks
        // are inside that box, which is what these points carry.
        const samples: number[] = [];
        {
          const bb = new THREE.Box3();
          model.traverse((child: any) => {
            if (!child.isMesh) return;
            child.geometry.computeBoundingBox();
            bb.copy(child.geometry.boundingBox).applyMatrix4(child.matrixWorld);
            for (const x of [bb.min.x, bb.max.x])
              for (const y of [bb.min.y, bb.max.y])
                for (const z of [bb.min.z, bb.max.z]) samples.push(x, y, z);
          });
        }

        const FILL = 0.92; // fraction of the frame the model should span

        const frame = () => {
          // Panning moves the orbit target, and OrbitControls rebuilds the camera
          // from it on the next update. Resetting the position without resetting
          // the target flings the model into a corner — which is exactly what
          // "Reset view" did.
          controls.target.set(0, 0, 0);
          const halfV = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
          let distance =
            Math.max(size.y / 2 / halfV, size.x / 2 / (halfV * camera.aspect)) + size.z;
          camera.position.set(0, 0, distance);

          // Centring the geometry is not the same as centring the picture: the
          // parts of the model nearest the camera project larger, so a building
          // whose towers lean forward sits high in the frame even though its box
          // is dead centre. Measure where the model actually lands and correct,
          // twice — each correction changes the projection a little.
          const v = new THREE.Vector3();
          for (let pass = 0; pass < 3; pass++) {
            camera.near = Math.max(1, distance * 0.02);
            camera.far = distance * 6 + size.z;
            camera.updateProjectionMatrix();
            camera.updateMatrixWorld();

            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
            for (let i = 0; i < samples.length; i += 3) {
              v.set(samples[i], samples[i + 1], samples[i + 2]).project(camera);
              if (v.x < minX) minX = v.x;
              if (v.x > maxX) maxX = v.x;
              if (v.y < minY) minY = v.y;
              if (v.y > maxY) maxY = v.y;
            }

            // NDC runs -1..1, so one NDC unit is half a frame.
            const worldPerNdcY = distance * halfV;
            const worldPerNdcX = worldPerNdcY * camera.aspect;
            const dx = ((minX + maxX) / 2) * worldPerNdcX;
            const dy = ((minY + maxY) / 2) * worldPerNdcY;
            camera.position.x += dx; controls.target.x += dx;
            camera.position.y += dy; controls.target.y += dy;

            distance *= Math.max(maxX - minX, maxY - minY) / (2 * FILL);
            camera.position.z = controls.target.z + distance;
          }

          camera.near = Math.max(1, distance * 0.02);
          camera.far = distance * 6 + size.z;
          camera.updateProjectionMatrix();
          controls.update();
        };
        resetRef.current = frame;

        // Until the viewer touches anything, every layout change re-frames. The
        // container is often still 0x0 on the first pass — measuring then leaves
        // the camera parked at a distance computed from nothing, which is how a
        // 2000-piece panel ends up filling the screen with four studs.
        let userMoved = false;
        controls.addEventListener('start', () => { userMoved = true; });
        reframeRef.current = () => { if (!userMoved) frame(); };

        // computeBuildingSteps() tags each part with the `0 STEP` group it came
        // from, which is what the backend emits per height level.
        const max = model.userData?.numBuildingSteps ?? 0;
        setTotalSteps(max);
        setStep(max);
        // computeBuildingSteps tags Groups, not meshes — keying off child.isMesh
        // finds nothing and the slider silently does nothing.
        apiRef.current = {
          showUpTo: (n: number) =>
            model.traverse((child: any) => {
              const s = child.userData?.buildingStep;
              if (typeof s === 'number') child.visible = s < n;
            }),
        };

        setStatus('ready');
      } catch (err) {
        if (!disposed) {
          setStatus('error');
          setMessage(err instanceof Error ? err.message : String(err));
        }
        return;
      }

      const resize = () => {
        const { clientWidth: w, clientHeight: h } = mount;
        if (!w || !h) return;
        // The third argument is updateStyle, and passing false here was the whole
        // bug. setPixelRatio(2) on a Retina screen makes the drawing buffer — and
        // the canvas's width/height attributes — twice the container. Without a CSS
        // size to override them, the canvas lays out at 2x, the card clips it, and
        // you see the top-left quarter: a model perfectly centred in a canvas that
        // is twice as wide as the box it is in, i.e. stuck in the bottom-right
        // corner. Every off-screen measurement said it was centred, because in the
        // canvas it was.
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        // Framing depends on the aspect ratio, so it can only be right once the
        // container has one. This is a no-op after the first drag.
        reframeRef.current?.();
      };
      resize();
      const ro = new ResizeObserver(resize);
      ro.observe(mount);

      let raf = 0;
      const tick = () => {
        raf = requestAnimationFrame(tick);
        controls.update();
        renderer.render(scene, camera);
      };
      tick();

      cleanup = () => {
        cancelAnimationFrame(raf);
        ro.disconnect();
        controls.dispose();
        renderer.dispose();
        // Meshes share materials across thousands of plates, so dispose geometry
        // per object but each material only once.
        const seen = new Set<any>();
        scene.traverse((o: any) => {
          o.geometry?.dispose?.();
          for (const m of [o.material].flat()) {
            if (m && !seen.has(m)) {
              seen.add(m);
              m.dispose?.();
            }
          }
        });
        renderer.domElement.remove();
      };
    })();

    return () => {
      disposed = true;
      cleanup();
    };
  }, [ldraw]);

  return (
    <div className={className}>
      <div className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden bg-[#f4f2ee] border border-black/10">
        <div ref={mountRef} className="absolute inset-0" />
        {status === 'ready' && (
          <button
            type="button"
            onClick={() => resetRef.current?.()}
            className="absolute top-3 right-3 px-3 py-1.5 rounded-full text-xs font-bold
                       bg-white/85 backdrop-blur border border-black/10 text-lego-black
                       hover:bg-white transition-colors"
          >
            Reset view
          </button>
        )}
        {status !== 'ready' && (
          <div className="absolute inset-0 grid place-items-center text-sm text-black/50 px-6 text-center">
            {status === 'loading'
              ? 'Building the model…'
              : `Could not render this model. ${message}`}
          </div>
        )}
      </div>

      {status === 'ready' && totalSteps > 1 && (
        <div className="mt-3 flex items-center gap-3">
          <span className="text-xs uppercase tracking-wider text-black/50 shrink-0">
            Step {step} / {totalSteps}
          </span>
          <input
            type="range"
            min={1}
            max={totalSteps}
            value={step}
            onChange={(e) => {
              const n = Number(e.target.value);
              setStep(n);
              apiRef.current?.showUpTo(n);
            }}
            className="w-full accent-lego-yellow"
          />
        </div>
      )}
    </div>
  );
}
