// Each effect owns one cancellable tick. There is no persistent interval to duplicate.
export function scheduleFrameTick(next: () => void, rate: number, clock = {
  set: (callback: () => void, delay: number) => globalThis.setTimeout(callback, delay),
  clear: (id: ReturnType<typeof setTimeout>) => globalThis.clearTimeout(id),
}) {
  let canceled = false;
  const timer = clock.set(() => { if (!canceled) next(); }, 1000 / rate);
  return () => { canceled = true; clock.clear(timer); };
}
