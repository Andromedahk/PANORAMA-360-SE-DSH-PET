"""Serial USB owner. Newline JSON on stdin/stdout; no credentials in diagnostics."""
import base64, ctypes, hashlib, json, os, pathlib, queue, sys, threading, time
from ctypes import wintypes
import screen
from protocol import field, fields, get, replace, frame, take_frame

HOME = pathlib.Path(os.environ.get('DAFEIYU_HOME', pathlib.Path(os.environ.get('LOCALAPPDATA', pathlib.Path.home()))/'DSHDaFeiYuScreen'))
HOME.mkdir(parents=True, exist_ok=True)
screen.ROOT = HOME

def label(n, text, size, line=0, color=0x244273):
    return field(1,n)+field(2,line)+field(8,'roboto-regular')+field(9,size)+field(10,color)+field(11,text)

def layout(value='--', status='WAITING FOR BALANCE'):
    def group(i,x,y,w,h,labels):
        return field(1,field(1,i)+field(2,x)+field(3,y)+field(4,w)+field(5,h)+field(6,2)+b''.join(field(8,v) for v in labels))
    # Safe inset within the horizontal tablet, identical in all 60 frames.
    # GUI coordinates below are derived from this same 2240 x 1080 layout.
    return (group(710,1475,730,347,34,[label(711,'BALANCE / CNY',22,color=0xa4b4cd)])+
            group(720,1475,773,347,69,[label(721,value,52,color=0xffffff)])+
            group(730,1475,847,347,27,[label(732,status,15,color=0xa4b4cd)]))

def update(client, value, status):
    body = b''.join(field(1,field(1,g)+field(2,field(1,l)+field(2,t)))
                    for g,l,t in [(720,721,value),(730,732,status)])
    data=frame(field(300,body))
    pending=client.transport.arm_read()
    try:
        client.transport.write(data)
        try: client.buffer.extend(pending.finish(100))
        except TimeoutError: pass
    finally: pending.close()
    while (payload:=take_frame(client.buffer)) is not None:
        error=get(payload,2,b'')
        if get(error,1,0): raise RuntimeError('Screen rejected text update')
    return len(data)

def protect(data, decrypt=False):
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buf=ctypes.create_string_buffer(data)
    src=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))); dst=Blob()
    fn=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)): raise RuntimeError('Windows credential protection failed')
    try: return ctypes.string_at(dst.data,dst.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(dst.data)

class Bridge:
    def __init__(self):
        self.client=None; self.active=False; self.error=None; self.last_ping=0
        self.backup=None; self.run=None

    def close(self):
        if self.client: self.client.close()
        self.client=None; self.active=False

    def connect(self):
        if self.client: return
        c=screen.Client()
        try:
            info=c.info()
            if info.get('product')!='PASE': raise RuntimeError('Only the tested PASE screen is supported')
            self.client=c; self.error=None
        except Exception:
            c.close(); raise

    def status(self):
        return {'connected':self.client is not None,'playing':self.active,'error':self.error,'backupAvailable':(HOME/'restore-config.bin').exists()}

    def handle(self, req):
        op=req.get('op')
        if op=='status': return self.status()
        if op=='saveKey':
            key=req.get('key','').strip()
            if not key or len(key)>16384 or any(ord(c)<33 or ord(c)>126 for c in key): raise ValueError('Invalid API Key')
            temp=HOME/'api-key.tmp'; temp.write_bytes(protect(key.encode())); temp.replace(HOME/'api-key.dpapi')
            return {'saved':True}
        if op=='readKey':
            p=HOME/'api-key.dpapi'
            return {'key':protect(p.read_bytes(),True).decode() if p.exists() else None}
        if op=='clearKey':
            (HOME/'api-key.dpapi').unlink(missing_ok=True); return {'cleared':True}
        if op=='stop': self.close(); return self.status()
        if op=='start':
            self.connect()
            c=self.client
            if self.active: return self.status()
            path=pathlib.Path(req['media']).resolve(strict=True)
            digest=hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            remote=f'dsh-fish-{digest}.mp4.h264_2240x1080'
            previous=c.command(104,expected=504); previous_run=c.command(105,expected=505)
            # Preserve the original across restarts while our own clip is selected.
            old_name=get(get(previous,3,b''),3,b'').decode(errors='replace')
            if not old_name.startswith('dsh-fish-') or not (HOME/'restore-config.bin').exists():
                (HOME/'restore-config.bin').write_bytes(previous)
                (HOME/'restore-layout.bin').write_bytes(previous_run)
            try:
                exists=any(pathlib.PurePosixPath(x['path'].replace('\\','/')).name==remote and x['size']==path.stat().st_size for x in c.catalog())
                if not exists: c.upload(path,remote,lambda _:None)
                work=get(previous,3); display=get(previous,5)
                if work is None or display is None: raise RuntimeError('Incomplete screen configuration')
                config=replace(previous,{3:replace(work,{1:0,2:0,3:remote}),5:replace(display,{1:1})})
                c.command(200,config,600)
                c.command(201,layout(req.get('value','--'),req.get('status','WAITING FOR BALANCE')),600,optional_ack=True)
                actual=c.command(104,expected=504)
                if get(get(actual,3,b''),3)!=remote.encode(): raise RuntimeError('Screen media readback mismatch')
                self.active=True; self.last_ping=time.monotonic(); self.error=None
                return self.status()
            except Exception:
                try:
                    c.command(200,previous,600); c.command(201,previous_run,600,optional_ack=True)
                finally: self.close()
                raise
        if op=='restore':
            self.connect()
            self.client.restore(HOME/'restore-config.bin')
            self.client.command(201,(HOME/'restore-layout.bin').read_bytes(),600,optional_ack=True)
            self.close(); return self.status()
        if op=='update':
            value=req.get('value','--'); status=req.get('status','UPDATED')
            if len(value)>18 or len(status)>48 or not value.isascii() or not status.isascii(): raise ValueError('Invalid overlay text')
            if not self.active: return {'bytes':0}
            return {'bytes':update(self.client,value,status)}
        if op=='verify':
            if not self.client: raise RuntimeError('Screen is not connected')
            body=self.client.command(105,expected=505)
            values={}
            for n,w,g,_ in fields(body):
                if n==1:
                    for k,wire,l,_ in fields(g):
                        if k==8: values[str(get(l,1))]=get(l,11,b'').decode(errors='replace')
            return {'labels':values}
        raise ValueError('Unknown operation')

def main():
    sys.stdin.reconfigure(encoding='utf8'); sys.stdout.reconfigure(encoding='utf8')
    inbox=queue.Queue(); bridge=Bridge()
    def read():
        for line in sys.stdin: inbox.put(line)
        inbox.put(None)
    threading.Thread(target=read,daemon=True).start()
    try:
        while True:
            try: line=inbox.get(timeout=1)
            except queue.Empty:
                if bridge.active and time.monotonic()-bridge.last_ping>=2:
                    try: bridge.client.ping(); bridge.last_ping=time.monotonic()
                    except Exception:
                        bridge.error='屏幕连接中断，请重新开始显示'; bridge.close()
                continue
            if line is None: break
            req={}
            try:
                req=json.loads(line)
                result=bridge.handle(req)
                response={'id':req.get('id'),'result':result}
            except Exception as e:
                # USB messages contain no balance credentials; never serialize input.
                response={'id':req.get('id'),'error':str(e) if req.get('op') not in ('saveKey','readKey') else '凭证读取或保存失败'}
            print(json.dumps(response,ensure_ascii=False),flush=True)
    finally: bridge.close()

if __name__=='__main__': main()
