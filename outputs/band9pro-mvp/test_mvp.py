import importlib
import os
import struct
import tempfile
import time
import unittest
import zlib
from pathlib import Path
from fastapi.testclient import TestClient
from sleep_file import parse_sleep


def fixture():
    bed = 1792591200
    head = struct.pack('<IbBB', bed, 32, 2, 12)+b'\0'
    body = b'\xff\xff'+b'\0'*5+struct.pack('<hII', 60, bed, bed+3600)
    body += b'\0'*3+struct.pack('<hhhh',20,20,20,0)+b'\0'
    body += b''.join(struct.pack('<IB', bed+i*1200, code) for i,code in enumerate([3,2,4]))
    raw = head+body
    return raw+struct.pack('<I',zlib.crc32(raw))


class Tests(unittest.TestCase):
    def test_parser(self):
        e = parse_sleep(fixture(), 'band-local-1')
        self.assertEqual([x['stage'] for x in e['sleep']['stages']], ['light','deep','rem'])
        self.assertEqual(e['source']['timezone_offset_minutes'], 480)
        self.assertEqual(sum(x['end']-x['start'] for x in e['sleep']['stages']),3600)

    def test_corruption_and_version(self):
        bad = bytearray(fixture()); bad[15] ^= 1
        with self.assertRaises(ValueError): parse_sleep(bytes(bad),'x')
        bad = bytearray(fixture()); bad[5] = 99
        bad[-4:] = struct.pack('<I',zlib.crc32(bad[:-4]))
        with self.assertRaises(ValueError): parse_sleep(bytes(bad),'x')

    def test_api_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ.update(PHONE_TOKEN='p'*32, AGENT_TOKEN='a'*32)
            api = importlib.import_module('api'); api.DB = str(Path(tmp)/'test.db')
            with TestClient(api.app) as c:
                phone={'Authorization':'Bearer '+'p'*32}
                agent={'Authorization':'Bearer '+'a'*32}
                event=parse_sleep(fixture(),'band-local-1'); eid=event['event_id']
                self.assertEqual(c.post('/v1/sleep',json=event).status_code,401)
                for _ in range(2): self.assertEqual(c.post('/v1/sleep',json=event,headers=phone).status_code,200)
                self.assertEqual(c.get('/v1/agent/pending',headers=phone).status_code,401)
                self.assertEqual(len(c.get('/v1/agent/pending',headers=agent).json()),1)
                result=dict(title='TEST',text='Synthetic fixture only',options=[dict(id='a',text='Open phone')],expires_at=int(time.time())+600)
                self.assertEqual(c.post('/v1/agent/results/'+eid,json=result,headers=agent).status_code,200)
                self.assertEqual(len(c.get('/v1/notifications',headers=phone).json()),1)
                self.assertEqual(c.post('/v1/notifications/'+eid+'/submitted',headers=phone).status_code,200)
                self.assertEqual(c.get('/v1/notifications',headers=phone).json(),[])


if __name__ == '__main__': unittest.main()
