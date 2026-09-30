import assert from 'node:assert/strict';
import {join} from 'node:path';
import {Worker,ROOT} from '../service.js';
const worker=new Worker();
let started=false;
try {
  const state=await worker.request('start',{media:join(ROOT,'assets','tail-swing.h264'),value:'12.34',status:'TEST ONLY'});
  started=true;assert.equal(state.playing,true);
  await worker.request('update',{value:'56.78',status:'TEST ONLY'});
  const first=await worker.request('verify');
  assert.equal(first.labels['721'],'56.78');assert.equal(first.labels['732'],'TEST ONLY');
  await new Promise(r=>setTimeout(r,3500));
  const second=await worker.request('verify');assert.equal(second.labels['721'],'56.78');
  console.log(JSON.stringify({mediaSelection:true,independentNumberReadback:true,keepalive:true,visualAcceptance:'pending user'}));
} finally {
  if(started){await worker.request('restore');console.log('Original media and layout restored');}
  await worker.close();
}
