import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { fetchBalance, resolveLocalCredential } from './balance.js';

export const ROOT = dirname(fileURLToPath(import.meta.url));
export const HOME = process.env.DAFEIYU_HOME || join(process.env.LOCALAPPDATA || homedir(),'DSHDaFeiYuScreen');
export const PORT = Number(process.env.DAFEIYU_PORT || 18432);

export class Worker {
  constructor() { this.child=null; this.seq=0; this.pending=new Map(); }
  launch() {
    if (this.child) return;
    if (process.platform !== 'win32') throw new Error('屏幕通信需要在连接 USB 的 Windows 电脑上运行');
    const embedded=join(ROOT,'bin','python','python.exe');
    this.child=spawn(existsSync(embedded)?embedded:(process.env.DAFEIYU_PYTHON || 'python'),['-X','utf8',join(ROOT,'worker','bridge.py')],{windowsHide:true,stdio:['pipe','pipe','pipe']});
    const child=this.child;
    createInterface({input:child.stdout}).on('line',line=>{
      try {
        const m=JSON.parse(line), p=this.pending.get(m.id);
        if (!p) return;
        clearTimeout(p.timer); this.pending.delete(m.id);
        m.error?p.reject(new Error(m.error)):p.resolve(m.result);
      } catch { /* Ignore non-protocol output, never forward credentials. */ }
    });
    child.stderr.resume();
    const fail=()=>{
      if (this.child!==child) return;
      this.child=null;
      for (const p of this.pending.values()) {clearTimeout(p.timer); p.reject(new Error('屏幕通信进程已退出'));}
      this.pending.clear();
    };
    child.on('error',fail); child.on('exit',fail); child.stdin.on('error',()=>{});
  }
  request(op,data={}) {
    try { this.launch(); } catch(e) {return Promise.reject(e);}
    const id=++this.seq;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(id); reject(new Error('屏幕操作超时，请停止后重新连接')); this.child?.kill();},op==='start'?120000:15000);
      this.pending.set(id,{resolve,reject,timer});
      this.child.stdin.write(JSON.stringify({id,op,...data})+'\n');
    });
  }
  async close() {
    const c=this.child;
    if (!c) return;
    c.stdin.end();
    await new Promise(resolve=>{const timer=setTimeout(()=>{c.kill();resolve();},3000);c.once('exit',()=>{clearTimeout(timer);resolve();});});
  }
}

export function validateSettings(input) {
  const pollSeconds=Number(input.pollSeconds);
  if (!Number.isInteger(pollSeconds)||pollSeconds<10||pollSeconds>3600||typeof input.autoStart!=='boolean') throw new Error('刷新间隔需为 10–3600 秒');
  return {pollSeconds,autoStart:input.autoStart};
}

export class ScreenService {
  constructor({accountReader=null,worker=new Worker(),mode='standalone'}={}) {
    this.worker=worker; this.accountReader=accountReader; this.mode=mode;
    this.settings={pollSeconds:30,autoStart:false};
    this.state={value:null,source:'未读取',updatedAt:null,balanceError:null,screen:{connected:false,playing:false},busy:false};
    this.timer=null; this.inflight=null; this.disposed=false; this.retrySeconds=0; this.enabled=false;
  }
  async init() {
    await mkdir(HOME,{recursive:true});
    try {this.settings=validateSettings(JSON.parse(await readFile(join(HOME,'settings.json'),'utf8')));} catch{}
  }
  snapshot() {return {...this.state,settings:this.settings,mode:this.mode};}
  overlayStatus() {
    if (!this.state.updatedAt) return 'WAITING FOR BALANCE';
    const t=new Date(this.state.updatedAt).toLocaleTimeString('en-GB',{hour12:false});
    return `${this.state.balanceError?'STALE':'UPDATED'} / ${t}`;
  }
  schedule() {
    clearTimeout(this.timer);
    if (!this.disposed && this.enabled) this.timer=setTimeout(()=>void this.refresh(),Math.max(this.settings.pollSeconds,this.retrySeconds)*1000);
  }
  refresh() {
    if (this.inflight) return this.inflight;
    this.inflight=this.performRefresh().finally(()=>{this.inflight=null;this.schedule();});
    return this.inflight;
  }
  async performRefresh() {
    try {
      const {key}=await this.worker.request('readKey');
      let result=null;
      // A saved user key deliberately overrides account mode. Otherwise use the
      // public DSH service, keeping its credential wholly inside the host.
      if (!key && this.accountReader) result=await this.accountReader();
      if (!result) {
        const credential=await resolveLocalCredential(key);
        if (!credential) throw new Error('请先登录 DSH，或在设置中输入 DeepSeek API Key');
        result=await fetchBalance(credential);
      }
      if (this.disposed) return;
      this.state.value=result.value;this.state.source=result.source;this.state.updatedAt=new Date().toISOString();this.state.balanceError=null;this.retrySeconds=0;
    } catch(e) {
      this.state.balanceError=e.message;
      this.retrySeconds=e.retrySeconds || Math.min(300,Math.max(30,this.retrySeconds*2));
    }
    if (!this.disposed && this.state.screen.playing) {
      try {await this.worker.request('update',{value:this.state.value||'--',status:this.overlayStatus()});}
      catch(e) {this.state.screen.error=e.message;}
    }
    return this.snapshot();
  }
  async action(op,data={}) {
    if (op==='status') {
      // Read worker state to reflect unplug and keepalive failures.
      if (this.worker.child) this.state.screen=await this.worker.request('status');
      return this.snapshot();
    }
    if (this.state.busy) throw new Error('正在处理屏幕操作，请稍候');
    if (op==='refresh') {this.enabled=true;return this.refresh();}
    this.state.busy=true;
    try {
      if (op==='settings') {
        this.settings=validateSettings(data);
        const tmp=join(HOME,'settings.tmp');await writeFile(tmp,JSON.stringify(this.settings,null,2));await rename(tmp,join(HOME,'settings.json'));this.schedule();
      } else if (op==='start') {
        this.state.screen=await this.worker.request('start',{media:join(ROOT,'assets','tail-swing.h264'),value:this.state.value||'--',status:this.overlayStatus()});
        this.enabled=true;void this.refresh();
      } else if (op==='stop'||op==='restore') {
        this.enabled=false;clearTimeout(this.timer);
        this.state.screen=await this.worker.request(op);
      } else if (op==='saveKey'||op==='clearKey') {
        if (this.inflight) await this.inflight;
        await this.worker.request(op,op==='saveKey'?{key:data.key}:{});
        this.state.value=null;this.state.updatedAt=null;this.enabled=true;await this.refresh();
      } else throw new Error('未知操作');
      return this.snapshot();
    } finally {this.state.busy=false;}
  }
  async dispose() {
    this.disposed=true;this.enabled=false;clearTimeout(this.timer);
    await this.worker.close();
  }
}

export async function serve(service,{port=PORT,onExit=null}={}) {
  const csrf=randomBytes(32).toString('hex');
  const html=(await readFile(join(ROOT,'ui.html'),'utf8')).replace('__CSRF__',csrf);
  const staticFiles=new Map([
    ['/ui.js',['ui.js','text/javascript; charset=utf-8']],
    ['/tail-swing.mp4',['assets/tail-swing.mp4','video/mp4']],
    ['/tail-swing.webm',['assets/tail-swing.webm','video/webm']],
    ['/preview.jpg',['assets/preview.jpg','image/jpeg']]
  ]);
  const server=createServer(async(req,res)=>{
    const send=(code,body,type='application/json; charset=utf-8')=>{res.writeHead(code,{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});res.end(typeof body==='string'||Buffer.isBuffer(body)?body:JSON.stringify(body));};
    try {
      const host=req.headers.host || '';
      const actualPort=server.address()?.port;
      if (![ `127.0.0.1:${actualPort}`,`localhost:${actualPort}`].includes(host)) return send(403,{error:'仅允许本机访问'});
      if (req.headers['sec-fetch-site']==='cross-site') return send(403,{error:'不允许跨站访问'});
      const path=new URL(req.url,`http://${host}`).pathname;
      if (req.method==='GET'&&path==='/') return send(200,html,'text/html; charset=utf-8');
      if (req.method==='GET'&&staticFiles.has(path)) {
        const [file,type]=staticFiles.get(path); const data=await readFile(join(ROOT,file));
        // Range responses let browser video elements loop and seek reliably.
        const match=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range||'');
        if (match) {
          const start=Number(match[1]),end=Math.min(Number(match[2]||data.length-1),data.length-1);
          if (start>end) {res.writeHead(416,{'Content-Range':`bytes */${data.length}`});res.end();return;}
          res.writeHead(206,{'Content-Type':type,'Content-Range':`bytes ${start}-${end}/${data.length}`,'Content-Length':end-start+1,'Accept-Ranges':'bytes'});res.end(data.subarray(start,end+1));return;
        }
        return send(200,data,type);
      }
      if (req.method==='GET'&&path==='/api/status') return send(200,await service.action('status'));
      if (req.method==='POST'&&path.startsWith('/api/')) {
        const origin=req.headers.origin;
        if (req.headers['x-dafeiyu-token']!==csrf || (origin&&origin!==`http://${host}`)) return send(403,{error:'页面已过期，请刷新后重试'});
        let raw='';for await(const c of req){raw+=c;if(raw.length>20000)return send(413,{error:'输入过长'});}
        const input=raw?JSON.parse(raw):{};
        const op=path.slice(5);
        if (op==='exit'&&onExit) {send(200,{ok:true});setTimeout(onExit,100);return;}
        return send(200,await service.action(op,input));
      }
      send(404,{error:'页面不存在'});
    } catch(e) {send(400,{error:e instanceof SyntaxError?'输入格式无效':e.message});}
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});
  return server;
}
