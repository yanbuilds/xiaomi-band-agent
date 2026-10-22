#!/usr/bin/env python3
"""Clean-room Xiaomi BLE V2 probe for Xiaomi Smart Band 9 Pro (n67cn).

This intentionally keeps credentials local. It performs the nonce/HKDF/HMAC
handshake and can request battery, vibrate, or send a short notification.
It does not acknowledge activity files, so the band will not delete history.
"""
from __future__ import annotations

import argparse, asyncio, datetime as dt, hashlib, hmac, os, struct
from pathlib import Path
from bleak import BleakClient, BleakScanner
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESCCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

FE95 = "0000fe95-0000-1000-8000-00805f9b34fb"
RX = "0000005e-0000-1000-8000-00805f9b34fb"  # notify from band
TX = "0000005f-0000-1000-8000-00805f9b34fb"  # writes to band

def vi(v: int) -> bytes:
    out = bytearray()
    while v >= 0x80: out.append((v & 0x7f) | 0x80); v >>= 7
    out.append(v); return bytes(out)
def field(n: int, data: bytes) -> bytes: return vi((n << 3) | 2) + vi(len(data)) + data
def var(n: int, v: int) -> bytes: return vi(n << 3) + vi(v)
def msg(*parts: bytes) -> bytes: return b"".join(parts)

def parse_pb(data: bytes):
    vals, blobs, i = {}, {}, 0
    while i < len(data):
        k = 0; s = 0
        while True:
            b = data[i]; i += 1; k |= (b & 127) << s
            if b < 128: break
            s += 7
        n, wire = k >> 3, k & 7
        if wire == 0:
            v = 0; s = 0
            while True:
                b = data[i]; i += 1; v |= (b & 127) << s
                if b < 128: break
                s += 7
            vals[n] = v
        elif wire == 2:
            ln = 0; s = 0
            while True:
                b = data[i]; i += 1; ln |= (b & 127) << s
                if b < 128: break
                s += 7
            blobs[n] = data[i:i+ln]; i += ln
        elif wire == 1: i += 8
        elif wire == 5: i += 4
        else: raise ValueError(f"protobuf wire {wire}")
    return vals, blobs

def crc16(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
        for _ in range(8): c = ((c >> 1) ^ 0xa001) if c & 1 else c >> 1
    return c
def frame(kind: int, seq: int, payload: bytes = b""):
    return b"\xa5\xa5" + bytes((kind & 15, seq)) + struct.pack("<HH", len(payload), crc16(payload)) + payload

def ctr(key: bytes, data: bytes) -> bytes:
    return Cipher(algorithms.AES(key), modes.CTR(key)).encryptor().update(data)
def command(t: int, st: int, body: bytes = b"") -> bytes:
    return var(1, t) + var(2, st) + (field(3, body) if body else b"")
def nonce_command(nonce: bytes) -> bytes:
    verify = field(1, nonce)
    return command(1, 26, field(30, verify))
def confirm_command(key, phone, watch, whmac, name):
    okm = HKDF(algorithm=hashes.SHA256(), length=64, salt=phone+watch,
               info=b"miwear-auth").derive(key)
    dk, ek, dn, en = okm[:16], okm[16:32], okm[32:36], okm[36:40]
    if not hmac.compare_digest(hmac.new(dk, watch+phone, hashlib.sha256).digest(), whmac): return None
    companion = msg(var(1,1), field(3,name.encode()), var(4,0xffffffff))
    ccm = AESCCM(ek, tag_length=4).encrypt(en+b"\0"*8, companion, None)
    confirm = field(1, hmac.new(ek, phone+watch, hashlib.sha256).digest()) + field(2, ccm)
    return command(1,27,field(32,confirm)), (dk,ek,dn,en)

START = bytes.fromhex("01 01 03 00 01 00 00 02 02 00 00 FC 03 02 00 20 00 04 02 00 10 27")

def load_key(path: Path, name: str) -> bytes:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(name+"="):
            v = line.split("=",1)[1].strip()
            if len(v)==32: return bytes.fromhex(v)
    raise RuntimeError(f"missing {name} in local credential file")

async def find_band():
    ds = await BleakScanner.discover(timeout=8)
    for d in ds:
        if "Smart Band 9 Pro" in (d.name or "") or "n67" in (d.name or "").lower(): return d
    raise RuntimeError("Band 9 Pro not found; keep its screen awake and Bluetooth enabled")

async def run(args):
    dev = await find_band() if not args.address else args.address
    print("found Band 9 Pro; connecting")
    q = asyncio.Queue(); buf = bytearray(); seq = 1; keys = None; authed = False
    async with BleakClient(dev, timeout=20) as c:
        ch = c.services.get_characteristic(TX)
        mtu = max(20, getattr(ch, "max_write_without_response_size", 20) or 20)
        async def send_frame(raw: bytes):
            for off in range(0, len(raw), mtu):
                await c.write_gatt_char(TX, raw[off:off+mtu], response=False)
        async def notify(_, data):
            nonlocal buf
            buf.extend(data)
            while len(buf) >= 8:
                if buf[:2] != b"\xa5\xa5": del buf[0]; continue
                ln = int.from_bytes(buf[4:6],"little")
                if len(buf) < 8+ln: break
                p = bytes(buf[:8+ln]); del buf[:8+ln]
                payload = p[8:]
                if crc16(payload) != int.from_bytes(p[6:8],"little"): continue
                await q.put((p[2]&15,p[3],payload))
        await c.start_notify(RX, notify)
        await send_frame(frame(2,0,START))
        # The band answers START_SESSION_REQUEST with a session-config frame;
        # only then is it ready to accept the protobuf nonce command.
        while True:
            kind0, seq0, payload0 = await asyncio.wait_for(q.get(), timeout=8)
            print(f"rx frame kind={kind0} seq={seq0} len={len(payload0)}")
            if kind0 == 2: break
        print("session configured; sending authentication nonce")
        phone = os.urandom(16)
        seq = 0
        await send_frame(frame(3,seq,b"\x01\x01"+nonce_command(phone))); seq = (seq + 1) & 0xff
        watch = whmac = None
        deadline = asyncio.get_running_loop().time()+12
        while asyncio.get_running_loop().time() < deadline:
            kind,s,p = await asyncio.wait_for(q.get(), timeout=max(.1, deadline-asyncio.get_running_loop().time()))
            print(f"rx frame kind={kind} seq={s} len={len(p)}")
            if kind == 3 and len(p)>=2:
                await send_frame(frame(1,s))
                body = p[2:]
                # unencrypted auth replies have opcode 1
                vals, blobs = parse_pb(body)
                # The Band 9 Pro firmware may return Auth{status=4} here when
                # the BLE endpoint is still owned by Mi Fitness. Do not dump
                # the nested bytes: they can contain nonce material.
                if vals.get(1)==1 and vals.get(2)==26:
                    av, ab = parse_pb(blobs.get(3,b""))
                    if av.get(3) == 4:
                        raise RuntimeError("Band returned authentication status 4; release the Mi Fitness connection/binding and retry")
                    # Some firmware revisions wrap the verify message as field 31;
                    # accept either the documented wrapper or its direct payload.
                    verify = parse_pb(ab.get(31,b""))[1] if 31 in ab else ab
                    watch, whmac = verify.get(1), verify.get(2)
                    if not watch or not whmac: continue
                    break
        if not watch: raise RuntimeError("no watch nonce/auth reply")
        result = confirm_command(load_key(Path(args.key_file), args.key_name), phone, watch, whmac, "GrokBand")
        if not result: raise RuntimeError("auth HMAC rejected key; try --key-name encryptKey_previous")
        confirm, keys = result
        await send_frame(frame(3,seq,b"\x01\x01"+confirm)); seq += 1
        print("authentication accepted")
        async def send(cmd):
            nonlocal seq
            await send_frame(frame(3,seq,b"\x01\x02"+ctr(keys[1],cmd))); seq += 1
        await send(var(1,2)+var(2,1))
        end = asyncio.get_running_loop().time()+args.duration
        while asyncio.get_running_loop().time() < end:
            try: kind,s,p = await asyncio.wait_for(q.get(), timeout=.5)
            except asyncio.TimeoutError: continue
            if kind != 3 or len(p)<2: continue
            await send_frame(frame(1,s))
            body = ctr(keys[0], p[2:]) if p[1]==2 else p[2:]
            vals, blobs = parse_pb(body)
            if args.vibrate and vals.get(1)==2 and vals.get(2)==1:
                print("received encrypted response")
            if args.vibrate and not authed:
                await send(var(1,2)+var(2,18)+field(4,var(5,0))); authed=True; print("vibration command sent")
        await c.stop_notify(RX)

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--address"); ap.add_argument("--key-file",default="work/mihealth/credentials.local"); ap.add_argument("--key-name",default="encryptKey"); ap.add_argument("--vibrate",action="store_true"); ap.add_argument("--duration",type=float,default=4); asyncio.run(run(ap.parse_args()))
