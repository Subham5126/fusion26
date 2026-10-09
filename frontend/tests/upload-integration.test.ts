import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../../tests/contracts/fixtures/track-result.json';
import { buildUploadManifest, uploadOverlay } from '../src/viewer/uploadOverlay';
import type { LocalFrame } from '../src/viewer/localSequence';
import { parseAnalysisResult } from '../src/api/responseValidation';
import { runUpload } from '../src/api/client';
import { createAnalysisJobController } from '../src/state/analysisJob';
import type { AnalysisState } from '../src/state/analysis';
import { imageTransform, pixelToViewport } from '../src/viewer/geometry';

const frames = (): LocalFrame[] => Array.from({length:5},(_,i) => ({id:`local-${i}`, file:new File(['pixels'],`${i}.png`,{type:'image/png'}), url:`blob:${i}`,
  width_px:640,height_px:480,timestamp_s:null,header:{width:640,height:480,orientation:1,format:'image/png'}}));
function source() {
  const local=frames(), manifest=buildUploadManifest(local), result=structuredClone(fixture);
  result.sequence_id=manifest.sequence_id; result.source_type='user_upload'; result.profile='spotgeo'; result.registration.status='estimated';
  const diagnostics={sequence:manifest,registration:{status:'estimated',transform_direction:'raw_to_reference',
    frames:Array.from({length:5},()=>({reference_to_raw:[[1,0,10],[0,1,5],[0,0,1]]}))}};
  return {local,manifest,result:parseAnalysisResult(result),diagnostics};
}
test('upload manifest preserves native 640x480 order and unknown timestamps', () => {
  const local=frames(), manifest=buildUploadManifest(local);
  assert.equal(manifest.source_type,'user_upload'); assert.equal(manifest.profile,'spotgeo');
  assert.deepEqual(manifest.frames.map(frame=>frame.image_ref),['frame_0','frame_1','frame_2','frame_3','frame_4']);
  assert.ok(manifest.frames.every(frame=>frame.timestamp_s===null && frame.width_px===640));
  assert.throws(()=>buildUploadManifest(local.slice(0,4)),/exactly five/);
  local[0].header.orientation=6; assert.throws(()=>buildUploadManifest(local),/Orientation/);
});
test('actual multipart transport sends files in confirmed order without setting a guessed boundary', async () => {
  const original=globalThis.fetch, local=frames(), manifest=buildUploadManifest(local);
  globalThis.fetch=async(url, options)=>{
    assert.equal(url,'/api/analyze/upload'); assert.equal(options?.method,'POST'); assert.equal(options?.headers,undefined);
    const data=options!.body as FormData; assert.equal(JSON.parse(data.get('manifest') as string).sequence_id,manifest.sequence_id);
    assert.deepEqual(data.getAll('files').map(file=>(file as File).name),local.map(frame=>frame.file.name));
    return new Response(JSON.stringify({job_id:'job-upload',status:'queued'}),{status:202});
  };
  try { assert.equal((await runUpload(manifest,local.map(frame=>frame.file))).job_id,'job-upload'); } finally { globalThis.fetch=original; }
});
test('registered tracks project through the current frame inverse while raw boxes remain native', () => {
  const s=source(), model=uploadOverlay(s.result,s.local[2],2,s.manifest,s.diagnostics);
  assert.equal(model.warnings.length,0);
  assert.equal(model.detections[0].center.x,s.result.detections[2].x_raw_px);
  assert.equal(model.tracks[0].observed[0].x,s.result.tracks[0].points[0].x_reference_px+10);
  assert.equal(model.tracks[0].predictions[0].x,s.result.tracks[0].trajectory!.predictions[0].x_reference_px+10);
  for (const width of [320,640,1000]) {
    const transform=imageTransform({width:640,height:480},{width,height:400},{zoom:1,pan:{x:0,y:0}});
    assert.equal(pixelToViewport(model.detections[0].center,transform).x,transform.left+(model.detections[0].center.x+.5)*transform.scale);
  }
});
test('foreign or malformed diagnostics and mismatched track observations suppress overlays', () => {
  const s=source();
  for (const diagnostic of [null,{}, {sequence:{...s.manifest,frames:null},registration:s.diagnostics.registration}])
    assert.equal(uploadOverlay(s.result,s.local[0],0,s.manifest,diagnostic).tracks.length,0);
  s.result.tracks[0].points[0].x_raw_px=300;
  assert.match(uploadOverlay(s.result,s.local[0],0,s.manifest,s.diagnostics).warnings[0],/disagree/);
});
test('upload polling checks source identity and reset removes a completed result', async () => {
  const s=source(), original=globalThis.fetch, states:AnalysisState[]=[];
  globalThis.fetch=async()=>new Response(JSON.stringify({job_id:s.result.job_id,status:'queued'}),{status:202});
  const controller=createAnalysisJobController(state=>states.push(state),{
    submit:async()=>{throw Error('must use upload')}, wait:async()=>{},
    job:async()=>({job_id:s.result.job_id,status:'succeeded',progress_stage:'completed',progress_fraction:1,warnings:[],error:null}),
    result:async()=>s.result });
  try { await controller.start(s.manifest,s.local.map(frame=>frame.file)); assert.equal(states.at(-1)?.phase,'succeeded');
    controller.reset(); assert.deepEqual(states.at(-1),{phase:'idle'}); } finally { controller.dispose(); globalThis.fetch=original; }
});
