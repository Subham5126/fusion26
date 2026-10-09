import { useCallback, useEffect, useRef, useState } from 'react';
import { createAnalysisJobController } from '../state/analysisJob';
import type { AnalysisState } from '../state/analysis';
import type { SequenceInput } from '../types/contracts';

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
    reset: useCallback(() => controller.current?.reset(), []),
    upload: useCallback((sequence: SequenceInput, files: File[]) => { void controller.current?.start(sequence, files); }, []),
  };
}
