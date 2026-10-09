import { useCallback, useEffect, useRef, useState } from 'react';
import { moveFrame, prepareLocalFrames, releaseFrames } from '../viewer/localSequence';
import type { LocalFrame } from '../viewer/localSequence';

export function useLocalSequence() {
  const [frames, setFrames] = useState<LocalFrame[]>([]);
  const [draft, setDraft] = useState<LocalFrame[]>([]);
  const [loading, setLoading] = useState(false), [error, setError] = useState<string | null>(null);
  const owned = useRef({ frames: [] as LocalFrame[], draft: [] as LocalFrame[], request: null as AbortController | null });
  useEffect(() => () => {
    owned.current.request?.abort(); owned.current.request = null;
    releaseFrames(owned.current.frames); releaseFrames(owned.current.draft);
    owned.current.frames = []; owned.current.draft = [];
  }, []);

  const select = useCallback(async (files: File[]) => {
    owned.current.request?.abort();
    const request = new AbortController(); owned.current.request = request;
    setLoading(true); setError(null);
    try {
      const next = await prepareLocalFrames(files, request.signal);
      if (owned.current.request !== request || request.signal.aborted) { releaseFrames(next); return; }
      releaseFrames(owned.current.draft); owned.current.draft = next; setDraft(next);
    } catch (cause) {
      if (!request.signal.aborted) setError(cause instanceof Error ? cause.message : 'Unable to load these images.');
    } finally {
      if (owned.current.request === request) { owned.current.request = null; setLoading(false); }
    }
  }, []);
  const reorder = (index: number, direction: -1 | 1) => {
    const next = moveFrame(owned.current.draft, index, direction); owned.current.draft = next; setDraft(next);
  };
  const confirm = () => {
    if (!owned.current.draft.length || owned.current.request) return;
    releaseFrames(owned.current.frames); owned.current.frames = owned.current.draft;
    owned.current.draft = []; setFrames(owned.current.frames); setDraft([]); setError(null);
  };
  const cancelDraft = () => { releaseFrames(owned.current.draft); owned.current.draft = []; setDraft([]); };
  const clear = () => {
    owned.current.request?.abort(); owned.current.request = null;
    releaseFrames(owned.current.frames); releaseFrames(owned.current.draft);
    owned.current.frames = []; owned.current.draft = [];
    setFrames([]); setDraft([]); setLoading(false); setError(null);
  };
  return { frames, draft, loading, error, select, reorder, confirm, cancelDraft, clear };
}
