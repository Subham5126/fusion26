// Replay genuine TCP job results through production coordinate mappers and T08.
// Usage: node tests/verify-t08-http.mjs <HTTP evidence folder> <API/proxy URL>
import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const directory = await mkdtemp(join(tmpdir(), 'orbittrace-t08-http-'));
try {
  const outfile = join(directory, 'verify.cjs');
  await build({ stdin: { contents: `
    import assert from 'node:assert/strict';
    import {readFileSync,writeFileSync} from 'node:fs';
    import {join} from 'node:path';
    import {createHash} from 'node:crypto';
    import {createElement} from 'react';
    import {renderToStaticMarkup} from 'react-dom/server';
    import {parseAnalysisResult} from '../src/api/responseValidation';
    import {parseJobManifest} from '../src/api/frameManifest';
    import {readImageHeader} from '../src/viewer/localSequence';
    import {scientificOverlay} from '../src/viewer/scientificOverlay';
    import {uploadOverlay} from '../src/viewer/uploadOverlay';
    import {T08Overlay} from '../src/components/workbench/T08Overlay';
    export const verification=(async()=>{
    const folder=process.argv[2], base=process.argv[3];
    if(!folder || !base) throw Error('Supply evidence folder and live API URL');
    const receipt=JSON.parse(readFileSync(join(folder,'receipt.json'),'utf8'));
    const verification=[];
    for(const entry of receipt.cases) {
      if(entry.state.status!=='succeeded') {
        const response=await fetch(base+'/api/jobs/'+entry.job_id+'/result');
        assert.equal(response.status,409); continue;
      }
      const response=await fetch(base+'/api/jobs/'+entry.job_id+'/result'); assert.equal(response.status,200);
      const result=parseAnalysisResult(await response.json()); assert.equal(result.job_id,entry.job_id);
      const manifestResponse=await fetch(base+'/api/jobs/'+entry.job_id+'/manifest'); assert.equal(manifestResponse.status,200);
      const manifest=parseJobManifest(await manifestResponse.json(),entry.job_id);
      const diagnosticResponse=await fetch(base+'/api/jobs/'+entry.job_id+'/diagnostics'); assert.equal(diagnosticResponse.status,200);
      const diagnostics=await diagnosticResponse.json(); const rows=[];
      for(let index=0; index<5; index++) {
        const image=await fetch(base+'/api/jobs/'+entry.job_id+'/frames/'+index); assert.equal(image.status,200);
        const bytes=new Uint8Array(await image.arrayBuffer());
        const header=readImageHeader(bytes); const metadata=diagnostics.sequence.frames[index];
        assert.equal(header.width,metadata.width_px); assert.equal(header.height,metadata.height_px);
        const frame={id:result.job_id+'/'+index, source:'analyzed_demo', job_id:result.job_id,frame_index:index,
          file:new File([bytes],'frame_'+index+'.png',{type:'image/png'}),url:'blob:verification',
          width_px:header.width,height_px:header.height,timestamp_s:manifest.frames[index].timestamp_s,header,manifest};
        const model=result.source_type==='synthetic' ? scientificOverlay(result,frame)
          : uploadOverlay(result,frame,index,diagnostics.sequence,diagnostics);
        assert.deepEqual(model.warnings,[]);
        assert.equal(model.detections.length,result.detections.filter(d=>d.frame_index===index).length);
        for(const track of model.tracks) {
          const backend=result.tracks.find(t=>t.track_id===track.id);
          const observed=backend.points.filter(p=>p.point_type==='observed');
          assert.equal(track.observed.length,observed.filter(p=>p.frame_index<=index).length);
          const last=observed.at(-1);
          const expected=last && index>=last.frame_index ? backend.trajectory?.predictions.length ?? 0 : 0;
          assert.equal(track.predictions.length,expected);
          for(const point of track.observed.filter(p=>p.frame===index)) {
            const observation=observed.find(p=>p.frame_index===index);
            const detection=result.detections.find(d=>d.detection_id===observation.detection_id);
            assert.ok(Math.abs(point.x-detection.x_raw_px)<1e-6);
            assert.ok(Math.abs(point.y-detection.y_raw_px)<1e-6);
          }
          assert.ok(track.observed.every(p=>p.frame<=index));
          assert.ok(track.predictions.every(p=>p.frame>last.frame_index));
        }
        for(const scale of [.4,1,4,8]) {
          const html=renderToStaticMarkup(createElement(T08Overlay,{model,scale,selected:result.tracks[0]?.track_id??null,
            select:()=>{},visibility:{detections:true,tracks:true,predictions:true},nativeSize:{width:header.width,height:header.height}}));
          assert.equal((html.match(/t08-neon-box/g)??[]).length,model.detections.length);
          assert.equal((html.match(/data-predicted-frame=/g)??[]).length,model.tracks.reduce((n,t)=>n+t.predictions.length,0));
        }
        rows.push({index,width:header.width,height:header.height,image_sha256:createHash('sha256').update(bytes).digest('hex'),
          boxes:model.detections.length,observed:model.tracks.reduce((n,t)=>n+t.observed.length,0),
          forecasts:model.tracks.reduce((n,t)=>n+t.predictions.length,0)});
      }
      verification.push({name:entry.name,job_id:entry.job_id,frames:rows});
      console.log(entry.name,JSON.stringify(rows.at(-1)));
    }
    writeFileSync(join(folder,'t08-verification.json'),JSON.stringify({api:base,current_point_tolerance_px:1e-6,cases:verification},null,2));
    console.log('Fresh HTTP results mapped and rendered by T08:',verification.length);
    })();
  `, resolveDir: fileURLToPath(new URL('.', import.meta.url)), loader: 'ts' }, outfile,
    bundle: true, platform: 'node', format: 'cjs', target: 'node24', jsx: 'automatic', logLevel: 'silent' });
  const module = await import(pathToFileURL(outfile).href);
  await module.default.verification;
} finally {
  if (!resolve(directory).startsWith(resolve(tmpdir()) + sep)) throw Error('Unexpected temporary directory');
  await rm(directory, { recursive: true, force: true });
}
