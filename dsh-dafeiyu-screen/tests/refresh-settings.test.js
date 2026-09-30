import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

test('refresh interval reschedules immediately, persists, and stops without touching video',async()=>{
  const home=await mkdtemp(join(tmpdir(),'panorama-settings-'));
  process.env.DAFEIYU_HOME=home;
  const {ScreenService}=await import('../service.js');
  const ops=[];
  const worker={request:async op=>{ops.push(op);return {};},close:async()=>{}};
  const service=new ScreenService({worker});
  try {
    await service.init();service.enabled=true;service.schedule();
    const previous=service.timer;
    await service.action('settings',{pollSeconds:60,autoStart:true});
    assert.notEqual(service.timer,previous);
    const delay=Date.parse(service.snapshot().nextRefreshAt)-Date.now();
    assert.ok(delay>58000&&delay<=60000);
    assert.deepEqual(ops,[]);
    assert.equal(JSON.parse(await readFile(join(home,'settings.json'),'utf8')).pollSeconds,60);
    const restored=new ScreenService({worker});await restored.init();
    assert.deepEqual(restored.settings,{pollSeconds:60,autoStart:true});await restored.dispose();
    await assert.rejects(service.action('settings',{pollSeconds:9,autoStart:false}));
    assert.equal(service.settings.pollSeconds,60);
    await service.action('stop');assert.equal(service.snapshot().nextRefreshAt,null);
  } finally {await service.dispose();await rm(home,{recursive:true,force:true});}
});
