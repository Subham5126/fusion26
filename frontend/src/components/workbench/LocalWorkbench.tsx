import { useId, useRef } from 'react';
import { Icon } from '../ui/Icon';
import { OpticalViewer } from './OpticalViewer';
import { useLocalSequence } from '../../hooks/useLocalSequence';
import { useFramePlayback } from '../../hooks/useFramePlayback';

export function LocalWorkbench() {
  const sequence = useLocalSequence(), playback = useFramePlayback(sequence.frames);
  const input = useRef<HTMLInputElement>(null), id = useId();
  const current = sequence.frames[playback.index];
  const ready = !!current && !sequence.loading && !sequence.draft.length;
  const choose = () => { playback.pause(); input.current?.click(); };
  return <section id="observations" className="workbench-shell local-workbench" aria-label="Mission image workbench" data-source="local_preview">
    <header className="observation-toolbar" aria-label="Image selection and sequence controls">
      <div className="observation-toolbar-heading"><Icon name="image" /><div><h2>Optical observations</h2><p>Local Image Preview · Browser only; no upload.</p></div></div>
      <div className="source-actions" role="group" aria-label="Image selection">
        <button className="button button--primary button--small" type="button" onClick={choose}><Icon name="plus" />{current ? 'Replace images' : 'Choose images'}</button>
        <button className="button button--secondary button--small" type="button" aria-label="Analyze local images" disabled title="Local image analysis requires backend registration support"><Icon name="scan" /><span className="local-analysis-control-label">Analyze local images</span></button>
        {!!(current || sequence.draft.length || sequence.loading) && <button className="button button--quiet button--small" type="button" aria-label="Clear sequence" title="Clear sequence" onClick={() => { playback.pause(); sequence.clear(); }}>Clear</button>}
      </div>
    </header>
    <input ref={input} className="visually-hidden" type="file" multiple accept="image/jpeg,image/png,.jpg,.jpeg,.png" aria-label="Select telescope images" tabIndex={-1}
      onChange={event => { const files = Array.from(event.currentTarget.files ?? []); event.currentTarget.value = ''; if (files.length) { playback.pause(); void sequence.select(files); } }} />
    {sequence.loading && <div className="sequence-feedback" role="status">Validating file contents, dimensions and browser decoding…</div>}
    {sequence.error && <div className="sequence-feedback sequence-feedback--error" role="alert"><Icon name="info" /><span>{sequence.error}{current ? ' Your confirmed sequence is preserved.' : ''}</span></div>}
    {!!sequence.draft.length && <section className="frame-order-editor" aria-labelledby={`${id}-order`}>
      <div className="order-editor-heading"><div><p className="eyebrow">REVIEW BEFORE PLAYBACK</p><h3 id={`${id}-order`}>Confirm the frame order.</h3><p>{sequence.draft.length} frames selected. Move frames into the order you intend; filenames do not establish acquisition order.</p></div>
        <div className="order-editor-actions"><button type="button" className="button button--quiet button--small" disabled={sequence.loading} onClick={sequence.cancelDraft}>Cancel</button>
          <button type="button" className="button button--primary button--small" disabled={sequence.loading} onClick={() => { playback.pause(); sequence.confirm(); }}>Confirm order & view</button></div></div>
      <ol className="draft-frame-list" aria-label="Proposed frame order">{sequence.draft.map((frame, index) => <li key={frame.id}>
        <span className="frame-order-number">{String(index + 1).padStart(2, '0')}</span><img src={frame.url} alt="" width="48" height="36" />
        <span className="draft-frame-name" title={frame.file.name}>{frame.file.name}<small>{frame.width_px} × {frame.height_px} px</small></span>
        <div className="frame-order-buttons"><button type="button" disabled={index === 0 || sequence.loading} aria-label={`Move frame ${index + 1} earlier`} onClick={() => sequence.reorder(index, -1)}><Icon name="up" /></button>
          <button type="button" disabled={index === sequence.draft.length - 1 || sequence.loading} aria-label={`Move frame ${index + 1} later`} onClick={() => sequence.reorder(index, 1)}><Icon name="down" /></button></div>
      </li>)}</ol>
      {current && <p className="order-preservation-note">Your confirmed sequence stays available until you confirm this replacement.</p>}
    </section>}
    <div className="workspace-body"><div className="observation-area">
      <OpticalViewer key={sequence.frames[0]?.id ?? 'empty'} frame={current} onSelect={choose} onStep={direction => playback.seek(playback.index + direction)}
        onToggle={() => { if (ready) playback.toggle(); }} onError={playback.pause} />
      <div className="frame-caption"><span>{current ? `FRAME ${String(playback.index + 1).padStart(2, '0')}` : 'NO FRAME SELECTED'}</span><strong title={current?.file.name}>{current?.file.name ?? 'Choose and confirm your observations'}</strong></div>
      <div className="frame-timeline local-frame-timeline"><div className="timeline-controls">
        <button type="button" disabled={!ready || playback.index === 0} aria-label="Previous frame" title="Previous frame" onClick={() => playback.seek(playback.index - 1)}><Icon name="back" /></button>
        <button type="button" disabled={!ready} className="timeline-play" aria-label={playback.playing ? 'Pause frames' : 'Play frames'} onClick={playback.toggle}><Icon name={playback.playing ? 'pause' : 'play'} /></button>
        <button type="button" disabled={!ready || playback.index === sequence.frames.length - 1} aria-label="Next frame" title="Next frame" onClick={() => playback.seek(playback.index + 1)}><Icon name="next" /></button>
        <button type="button" disabled={!ready} aria-label="Restart from first frame" title="Restart from first frame" onClick={playback.restart}><Icon name="restart" /></button>
        <output aria-label="Current frame">Frame {current ? playback.index + 1 : '—'} / {sequence.frames.length || '—'}</output>
      </div>
      <label className="playback-speed">Display rate<select aria-label="Playback display rate" value={playback.rate} disabled={!ready} onChange={event => playback.setRate(Number(event.target.value))}>
        {[.5, 1, 2, 4].map(rate => <option key={rate} value={rate}>{rate} frames/s</option>)}</select></label>
      <div className="frame-slider"><input type="range" aria-label="Frame timeline" min="1" max={Math.max(1, sequence.frames.length)} value={current ? playback.index + 1 : 1} disabled={!ready}
        aria-valuetext={current ? `Frame ${playback.index + 1} of ${sequence.frames.length}: ${current.file.name}` : 'No confirmed sequence'} onChange={event => playback.seek(Number(event.target.value) - 1)} />
        <div><span>01</span><span>{sequence.frames.length ? String(sequence.frames.length).padStart(2, '0') : '—'}</span></div></div>
      <p>Display rate only · acquisition timing unknown</p></div>
    </div><aside className="track-inspector local-sequence-inspector" aria-label="Sequence inspector">
      <div className="inspector-title"><Icon name="layers" /><h3>Sequence inspector</h3></div><div className="local-inspector-summary"><span className="inspector-section-label">Source & status</span></div>
      <dl className="evidence-values"><div><dt>Source</dt><dd>Local images</dd></div><div><dt>Status</dt><dd>{sequence.loading ? 'Validating' : sequence.draft.length ? 'Review order' : current ? 'Ready to inspect' : 'Awaiting images'}</dd></div><div><dt>Frames</dt><dd>{sequence.frames.length || 'Not loaded'}</dd></div><div><dt>Dimensions</dt><dd>{current ? `${current.width_px} × ${current.height_px} px` : 'Not available'}</dd></div><div><dt>Timestamps</dt><dd>Unknown</dd></div></dl>
      <span className="inspector-section-label inspector-frames-label">Frames</span>
      {!current && <p className="inspector-empty-text">Your confirmed frame order will appear here.</p>}
      {current && <ol className="confirmed-frame-list" aria-label="Confirmed frame order">{sequence.frames.map((frame, index) => <li key={frame.id}><button type="button" disabled={sequence.loading || !!sequence.draft.length}
        aria-current={index === playback.index ? 'true' : undefined} aria-label={`Inspect frame ${index + 1}: ${frame.file.name}`} onClick={() => playback.seek(index)}>
        <span>{String(index + 1).padStart(2, '0')}</span><img src={frame.url} alt="" width="44" height="33" /><span title={frame.file.name}>{frame.file.name}</span></button></li>)}</ol>}
      <div className="local-evidence-pending"><span className="inspector-section-label">Local analysis</span><strong>Not performed</strong><p>Detections and tracks are not available. Analysis of this exact sequence is pending.</p></div>
      </aside></div>
    <footer className="workspace-footer"><span><Icon name="info" />Local viewing is ready. Local image analysis and scientific exports are pending.</span>
      <div className="export-actions"><button type="button" className="button button--quiet button--small" disabled><Icon name="download" />JSON</button><button type="button" className="button button--quiet button--small" disabled>CSV</button></div></footer>
  </section>;
}
