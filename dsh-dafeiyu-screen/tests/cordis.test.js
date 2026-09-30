import test from 'node:test';
import assert from 'node:assert/strict';
import {Context} from '@deepseek-ai/cordis';
import {mkdtemp,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const testHome=await mkdtemp(join(tmpdir(),'dafeiyu-test-'));
process.env.DAFEIYU_HOME=testHome;
process.env.DAFEIYU_PORT='18433';
const plugin=await import('../index.js');

test('real Cordis plugin mounts local GUI and releases port on disposal',async()=>{
  const ctx=new Context();
  const fiber=ctx.plugin(plugin);
  await fiber;
  try {
    const r=await fetch('http://127.0.0.1:18433/api/status');
    assert.equal(r.status,200);const state=await r.json();assert.equal(state.mode,'dsh');
  } finally {await fiber.dispose();await rm(testHome,{recursive:true,force:true});}
  await assert.rejects(fetch('http://127.0.0.1:18433/api/status'));
});
