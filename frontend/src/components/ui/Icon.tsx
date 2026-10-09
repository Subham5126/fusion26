// Small, locally authored line icons; no external icon runtime is required.
const paths = {
  arrow: 'M4 12h15m-6-6 6 6-6 6',
  external: 'M6 18 18 6M6 6h12v12',
  menu: 'M4 6h16M4 12h16M4 18h16',
  close: 'm6 6 12 12M6 18 18 6',
  scan: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 12h8M12 8v8',
  layers: 'm3 7 9-4 9 4-9 4-9-4Zm0 5 9 4 9-4M3 17l9 4 9-4',
  track: 'M5 18 10 12l5 1 4-7M4 18h2M9 12h2M14 13h2M18 6h2',
  file: 'M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8M8 16h6',
  shield: 'm12 3 8 3v6c0 5-8 9-8 9S4 17 4 12V6l8-3Zm-4 9 3 3 5-6',
  activity: 'M3 12h4l3-7 4 14 3-7h4',
  chevron: 'm8 4 8 8-8 8',
  play: 'm8 5 11 7-11 7V5Z',
  back: 'm15 5-9 7 9 7V5ZM4 5v14',
  next: 'm9 5 9 7-9 7V5Zm11 0v14',
  image: 'M3 4h18v16H3V4Zm0 12 5-5 4 4 3-3 6 6M15 8h1',
  plus: 'M4 12h16M12 4v16',
  minus: 'M4 12h16',
  upload: 'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',
  download: 'M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4',
  clock: 'M12 7v5l3 2',
  info: 'M12 11v6m0-10v1',
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, className }: {
  name: IconName; className?: string;
}) {
  return <svg className={`icon ${className ?? ''}`} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true">
    {(name === 'clock' || name === 'info') && <circle cx="12" cy="12" r="9" />}
    <path d={paths[name]} />
  </svg>;
}
