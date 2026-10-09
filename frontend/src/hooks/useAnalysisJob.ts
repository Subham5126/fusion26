import { useCallback, useEffect, useRef, useState } from 'react';
import { createAnalysisJobController } from '../state/analysisJob';
import type { AnalysisState } from '../state/analysis';

export function useAnalysisJob() {
  const [state, setState] = useState<AnalysisState>({ phase: 'idle' });
  const controller = useRef<ReturnType<typeof createAnalysisJobController> | null>(null);
  useEffect(() => {
    const job = createAnalysisJobController(setState); controller.current = job;
    return () => { job.dispose(); controller.current = null; };
  }, []);
  return {
    state,
    run: useCallback(() => { void controller.current?.start(); }, []),
    cancel: useCallback(() => controller.current?.cancel(), []),
  };
}
