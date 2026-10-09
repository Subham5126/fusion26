import { useEffect, useState } from 'react';
import { scheduleFrameTick } from '../viewer/playback';
import { clamp } from '../viewer/geometry';

export function useFramePlayback(frames: readonly { id: string }[], readyFrameId?: string | null) {
  const [index, setIndex] = useState(0), [playing, setPlaying] = useState(false), [rate, setRate] = useState(1);
  useEffect(() => { setIndex(0); setPlaying(false); }, [frames]);
  useEffect(() => {
    const pause = () => { if (document.hidden) setPlaying(false); };
    document.addEventListener('visibilitychange', pause);
    return () => document.removeEventListener('visibilitychange', pause);
  }, []);
  useEffect(() => {
    if (!playing || !frames.length || (readyFrameId !== undefined && readyFrameId !== frames[index]?.id)) return;
    if (index >= frames.length - 1) { setPlaying(false); return; }
    return scheduleFrameTick(() => setIndex(current => Math.min(current + 1, frames.length - 1)), rate);
  }, [playing, index, rate, frames, readyFrameId]);
  const seek = (value: number) => { setPlaying(false); setIndex(clamp(value, 0, Math.max(0, frames.length - 1))); };
  const toggle = () => {
    if (!frames.length) return;
    if (!playing && index >= frames.length - 1) setIndex(0);
    setPlaying(value => !value);
  };
  return { index: Math.min(index, Math.max(0, frames.length - 1)), playing, rate, setRate,
    pause: () => setPlaying(false), toggle, seek, restart: () => seek(0) };
}
