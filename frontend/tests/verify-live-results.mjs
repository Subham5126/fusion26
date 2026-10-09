// Validate real TCP-produced JSON through the frontend's actual strict parser.
import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const directory=await mkdtemp(join(tmpdir(),'orbittrace-live-contract-'));
try {
  const outfile=join(directory,'live.cjs');
  await build({stdin:{contents:`import {parseAnalysisResult} from '../src/api/responseValidation';
    import {readFileSync,readdirSync} from 'node:fs'; import {join} from 'node:path';
    const folder=process.argv[2]; const files=readdirSync(folder).filter(name=>name.endsWith('_result.json'));
    if(files.length<4) throw Error('Expected actual demo, counts, empty and ESA results');
    for(const name of files) { const result=parseAnalysisResult(JSON.parse(readFileSync(join(folder,name),'utf8'))); console.log(name,result.detections.length,result.tracks.length); }
    console.log(files.length+' actual HTTP results accepted by frontend contract');`,resolveDir:fileURLToPath(new URL('.',import.meta.url)),loader:'ts'},
    outfile,bundle:true,platform:'node',format:'cjs',logLevel:'silent'});
  await import(pathToFileURL(outfile).href);
} finally { await rm(directory,{recursive:true,force:true}); }
