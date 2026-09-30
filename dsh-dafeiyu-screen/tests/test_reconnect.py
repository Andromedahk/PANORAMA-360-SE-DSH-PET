import pathlib, tempfile, unittest, sys
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
import bridge
from protocol import field, fields, get

class FakeClient:
    uploaded=[]
    selected='original.mp4'
    layout=b''
    fail_ping=False
    def __init__(self): self.closed=False
    def info(self): return {'product':'PASE'}
    def close(self): self.closed=True
    def catalog(self): return [{'path':n,'size':s} for n,s in self.uploaded]
    def upload(self,p,n,progress): self.uploaded.append((n,p.stat().st_size))
    def ping(self):
        if self.fail_ping: raise PermissionError(5,'USB access denied')
    def command(self,n,body=b'',*args,**kwargs):
        if n==104:return field(3,field(3,self.selected))+field(5,field(1,1))
        if n==105:return self.layout
        if n==200: type(self).selected=get(get(body,3),3).decode()
        if n==201:type(self).layout=body
        return b''

class RecoveryTests(unittest.TestCase):
    def test_startup_waits_for_kanali_exit_then_connects_automatically(self):
        with tempfile.TemporaryDirectory() as d,patch.object(bridge,'HOME',pathlib.Path(d)):
            FakeClient.uploaded=[];FakeClient.selected='original.mp4';FakeClient.layout=b''
            media=pathlib.Path(d)/'test.h264';media.write_bytes(b'test-media')
            b=bridge.Bridge()
            with patch.object(bridge.screen,'Client',side_effect=RuntimeError('请先退出 KANALI')):
                result=b.handle({'op':'start','media':str(media),'value':'12.34'})
                self.assertTrue(result['reconnecting']);self.assertFalse(result['connected'])
                self.assertIn('KANALI',result['error'])
            # No second start command: the pending startup survives the conflict.
            b.handle({'op':'update','value':'56.78','status':'UPDATED'})
            with patch.object(bridge.screen,'Client',FakeClient):
                b.next_retry=0;b.tick()
                self.assertTrue(b.status()['playing']);self.assertIsNone(b.status()['error'])
                self.assertIn(b'56.78',FakeClient.layout)
                b.close()

    def test_disconnect_reconnect_reuses_video_and_keeps_latest_balance(self):
        with tempfile.TemporaryDirectory() as d,patch.object(bridge,'HOME',pathlib.Path(d)),patch.object(bridge.screen,'Client',FakeClient):
            FakeClient.uploaded=[];FakeClient.selected='original.mp4';FakeClient.layout=b''
            media=pathlib.Path(d)/'test.h264';media.write_bytes(b'test-media')
            b=bridge.Bridge();self.assertTrue(b.handle({'op':'start','media':str(media),'value':'12.34'})['playing'])
            original=(pathlib.Path(d)/'restore-config.bin').read_bytes()
            b.client.fail_ping=True;b.last_ping=0;b.tick()
            self.assertTrue(b.status()['reconnecting']);self.assertFalse(b.status()['playing'])
            b.handle({'op':'update','value':'56.78','status':'UPDATED'})
            b.next_retry=0;b.tick()
            self.assertTrue(b.active);self.assertEqual(len(FakeClient.uploaded),1)
            self.assertIn(b'56.78',FakeClient.layout)
            self.assertEqual(original,(pathlib.Path(d)/'restore-config.bin').read_bytes())
            b.handle({'op':'stop'});b.tick();self.assertIsNone(b.client);self.assertIsNone(b.desired)

    def test_large_text_stays_in_tablet_safe_rectangle(self):
        for n,w,g,_ in fields(bridge.layout('1234.56','UPDATED / 12:34:56')):
            x,y,width,height=[get(g,k) for k in (2,3,4,5)]
            self.assertGreaterEqual(x,1460);self.assertLessEqual(x+width,1813)
            self.assertGreaterEqual(y,733);self.assertLessEqual(y+height,881)

if __name__=='__main__':unittest.main()
