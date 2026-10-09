import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createDemoFrameController } from '../viewer/demoFrames';
import type { DemoFrameState } from '../viewer/demoFrames';
import { createManifestController } from '../viewer/frameManifest';
import type { ManifestState } from '../viewer/frameManifest';

export function useDemoFrames(jobId: string) {
  const [state, setState] = useState<DemoFrameState>({ jobId, index: 0, phase: 'loading' });
  const [metadata, setMetadata] = useState<ManifestState>({ jobId, phase: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const controller = useRef<ReturnType<typeof createDemoFrameController> | null>(null);
  const manifest = metadata.jobId === jobId && metadata.phase === 'ready' ? metadata.manifest : undefined;
  const frames = useMemo(() => manifest?.frames.map(frame => ({ ...frame, id: `${jobId}/${frame.frame_index}` })) ?? [], [jobId, manifest]);
  useEffect(() => {
    const owned = createManifestController(jobId, setMetadata);
    void owned.load(); return owned.dispose;
  }, [jobId, attempt]);
  useEffect(() => {
    if (!manifest) return;
    const owned = createDemoFrameController(manifest, setState); controller.current = owned;
    return () => { owned.dispose(); if (controller.current === owned) controller.current = null; };
  }, [manifest]);
  const select = useCallback((index: number, force = false) => { void controller.current?.select(index, force); }, []);
  const retryManifest = useCallback(() => setAttempt(value => value + 1), []);
  return { state, metadata, manifest, frames, select, retryManifest };
}
