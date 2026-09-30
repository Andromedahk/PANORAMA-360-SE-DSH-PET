import test from 'node:test';
import assert from 'node:assert/strict';
import {request} from 'node:http';
import {ScreenService,serve} from '../service.js';

class FakeWorker {
  constructor(){this.ops=[];this.child={};this.playing=false;}
  async request(op,data={}){this.ops.push({op,...data});if(op==='readKey')return {key:null};if(op==='start')this.playing=true;if(op==='stop'||op==='restore')this.playing=false;return {playing:this.playing,connected:this.playing};}
  async close(){this.closed=true;}
}
test('periodic balances never reapply/reupload video; errors keep stale value',async()=>{
  const worker=new FakeWorker();let calls=0,fail=false;
  const service=new ScreenService({worker,accountReader:async()=>{calls++;if(fail)throw new Error('network unavailable');return{value:'18.42',source:'test'};}});
  await service.action('start');await service.inflight;
  await Promise.all([service.refresh(),service.refresh()]);
  assert.equal(calls,2);assert.equal(worker.ops.filter(x=>x.op==='start').length,1);
  assert.equal(worker.ops.filter(x=>x.op==='update').length,2);
  fail=true;await service.refresh();
  assert.equal(service.state.value,'18.42');assert.match(worker.ops.at(-1).status,/STALE/);
  await service.action('stop');assert.equal(service.enabled,false);await service.dispose();assert.equal(worker.closed,true);
});
test('HTTP rejects unauthenticated writes and foreign Host; serves video ranges',async()=>{
  const worker=new FakeWorker(),service=new ScreenService({worker}),server=await serve(service,{port:0});
  const base=`http://127.0.0.1:${server.address().port}`;
  try{
    assert.equal((await fetch(base+'/api/start',{method:'POST',body:'{}'})).status,403);
    const foreign=await new Promise((resolve,reject)=>{const r=request(base+'/api/status',{headers:{Host:'evil.test'}},res=>{res.resume();resolve(res.statusCode);});r.on('error',reject);r.end();});
    assert.equal(foreign,403);
    const html=await(await fetch(base)).text(),token=html.match(/name="dafeiyu-token" content="([a-f0-9]+)"/)[1];
    const good=await fetch(base+'/api/stop',{method:'POST',headers:{'X-Dafeiyu-Token':token,'Content-Type':'application/json'},body:'{}'});
    assert.equal(good.status,200);
    const range=await fetch(base+'/tail-swing.mp4',{headers:{Range:'bytes=0-99'}});assert.equal(range.status,206);assert.equal((await range.arrayBuffer()).byteLength,100);
    const invalid=await fetch(base+'/api/settings',{method:'POST',headers:{'X-Dafeiyu-Token':token},body:JSON.stringify({pollSeconds:0,autoStart:false})});assert.equal(invalid.status,400);
  }finally{server.close();server.closeAllConnections();await service.dispose();}
});
