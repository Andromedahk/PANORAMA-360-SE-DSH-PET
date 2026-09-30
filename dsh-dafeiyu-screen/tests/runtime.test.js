import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';

test('cached embedded Python starts worker through Unicode workspace paths', {skip:process.platform!=='win32'||!process.env.PANORAMA_TEST_PYTHON}, async()=>{
  process.env.DAFEIYU_PYTHON=process.env.PANORAMA_TEST_PYTHON;
  const {ensurePython}=await import('../runtime.js');
  const path=await ensurePython();assert.ok(existsSync(path));
  const {Worker}=await import('../service.js');
  const worker=new Worker();
  try {const state=await worker.request('status');assert.equal(state.connected,false);}
  finally {await worker.close();}
});
