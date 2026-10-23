import importlib
import os
import struct
import tempfile
import time
import unittest
import zlib
from pathlib import Path
from fastapi.testclient import TestClient
import httpx
from agent_client import AgentConfig, AgentRunner, signed_headers, verify_signature
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

    def test_webhook_signature_rejects_replay(self):
        body = b'{"event_id":"abc"}'
        headers = signed_headers(body, 's' * 32, 1000)
        self.assertTrue(verify_signature(body, 's' * 32, headers['X-Band-Agent-Timestamp'], headers['X-Band-Agent-Signature'], now=1000))
        self.assertFalse(verify_signature(body, 's' * 32, headers['X-Band-Agent-Timestamp'], headers['X-Band-Agent-Signature'], now=1401))
        self.assertFalse(verify_signature(body, 'x' * 32, headers['X-Band-Agent-Timestamp'], headers['X-Band-Agent-Signature'], now=1000))

    def test_agent_runner_webhook_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ.update(PHONE_TOKEN='p'*32, AGENT_TOKEN='a'*32)
            api = importlib.import_module('api'); api.DB = str(Path(tmp)/'test.db')
            with TestClient(api.app) as server:
                event = parse_sleep(fixture(), 'band-local-1')
                phone = {'Authorization': 'Bearer ' + 'p'*32}
                self.assertEqual(server.post('/v1/sleep', json=event, headers=phone).status_code, 200)

                def handler(request: httpx.Request) -> httpx.Response:
                    self.assertTrue(verify_signature(request.content, 'w'*32,
                                                     request.headers['X-Band-Agent-Timestamp'],
                                                     request.headers['X-Band-Agent-Signature']))
                    return httpx.Response(200, json={'title':'睡眠回顾','text':'已分析','options':[],
                                                     'expires_at': int(time.time()) + 600})

                transport = httpx.MockTransport(handler)
                client = httpx.Client(transport=transport)
                # Route local API calls to the in-process FastAPI test server.
                original_get, original_post = client.get, client.post
                def local_get(url, **kwargs):
                    if url.endswith('/v1/agent/pending'):
                        response = server.get('/v1/agent/pending', headers=kwargs.get('headers'))
                        return httpx.Response(response.status_code, json=response.json(),
                                              request=httpx.Request('GET', url))
                    return original_get(url, **kwargs)
                def local_post(url, **kwargs):
                    if '/v1/agent/results/' in url:
                        event_id = url.rsplit('/', 1)[-1]
                        response = server.post('/v1/agent/results/' + event_id,
                                               headers=kwargs.get('headers'), json=kwargs.get('json'))
                        return httpx.Response(response.status_code, json=response.json(),
                                              request=httpx.Request('POST', url))
                    return original_post(url, **kwargs)
                client.get, client.post = local_get, local_post
                runner = AgentRunner(AgentConfig('http://127.0.0.1:8000', 'a'*32,
                                                 'https://agent.example.test/webhook', 'w'*32), client)
                self.assertEqual(runner.run_once(), {'seen': 1, 'completed': 1, 'failed': 0})


if __name__ == '__main__': unittest.main()
