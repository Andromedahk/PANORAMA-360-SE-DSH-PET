import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
from bridge import layout,update
from protocol import fields,get,take_frame
from protocol import field,frame
from screen import Client

class OverlayTests(unittest.TestCase):
    def test_balance_labels_inside_tablet(self):
        groups=[v for n,w,v,r in fields(layout('12.34')) if n==1]
        self.assertEqual(len(groups),3)
        self.assertEqual(get(groups[1],2),1475)
        self.assertEqual(get(groups[1],3),773)
        self.assertEqual(get(groups[1],4),347)
        # Actual black screen in the edited artwork, transformed into device pixels.
        for group in groups:
            x,y,w,h=(get(group,k) for k in (2,3,4,5))
            self.assertGreaterEqual(x,1455)
            self.assertGreaterEqual(y,699)
            self.assertLessEqual(x+w,1844)
            self.assertLessEqual(y+h,905)
        number=[v for n,w,v,r in fields(groups[1]) if n==8][0]
        self.assertEqual(get(number,11),b'12.34')
    def test_updates_are_only_command_300(self):
        class Pending:
            def finish(self,n): raise TimeoutError()
            def close(self): pass
        class Transport:
            def arm_read(self): return Pending()
            def write(self,data): self.data=data
        class Client: transport=Transport();buffer=bytearray()
        c=Client();size=update(c,'22.99','UPDATED / 08:00:00')
        self.assertLess(size,100)
        payload=take_frame(bytearray(c.transport.data))
        self.assertEqual([n for n,w,v,r in fields(payload)],[300])

    def test_new_connection_recovers_partial_previous_response(self):
        class Pending:
            def finish(self,n): return b'old-response-tail'+frame(field(1,field(2,101))+field(500,field(4,'PASE')))
            def close(self): pass
        class Transport:
            def arm_read(self): return Pending()
            def write(self,*a): pass
        class Capture:
            def record(self,*a): pass
        c=Client.__new__(Client);c.transport=Transport();c.capture=Capture();c.buffer=bytearray();c.track=100;c.syncing=True
        self.assertEqual(get(c.command(100,expected=500),4),b'PASE')
        self.assertFalse(c.syncing)
        c.buffer=bytearray(b'bad-header');c.track=100
        with self.assertRaises(ValueError):c.command(100,expected=500)

if __name__=='__main__':unittest.main()
