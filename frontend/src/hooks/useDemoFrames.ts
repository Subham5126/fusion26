import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createDemoFrameController, verifiedDemoLayout } from '../viewer/demoFrames';
import type { DemoFrameState } from '../viewer/demoFrames';

export function useDemoFrames(jobId: string) {
  const [state, setState] = useState<DemoFrameState>({ jobId, index: 0, phase: 'loading' });
  const controller = useRef<ReturnType<typeof createDemoFrameController> | null>(null);
  const frames = useMemo(() => verifiedDemoLayout.indexes.map(index => ({ id: `${jobId}/${index}` })), [jobId]);
  useEffect(() => {
    const owned = createDemoFrameController(jobId, setState); controller.current = owned;
    return () => { owned.dispose(); if (controller.current === owned) controller.current = null; };
  }, [jobId]);
  const select = useCallback((index: number, force = false) => { void controller.current?.select(index, force); }, []);
  return { state, frames, select };
}
