"""Offline Xiaomi sleep-stages v2 decoder; no Bluetooth or keys required.

Layout references: Gadgetbridge SleepStagesParser / XiaomiActivityFileId;
FreeBand ActivityFiles.swift. Only this file kind is supported. Hardware
validation on Band 9 Pro is still required. Unknown versions fail closed.
"""
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path


def parse_sleep(data: bytes, device_id: str) -> dict:
    # Full assembled file: 7-byte ID, padding, body, little-endian CRC32.
    if len(data) < 41:
        raise ValueError('truncated file')
    if zlib.crc32(data[:-4]) != struct.unpack_from('<I', data, len(data)-4)[0]:
        raise ValueError('CRC32 mismatch')
    stamp, tz, version, flags = struct.unpack_from('<IbBB', data)
    if version != 2 or flags >> 7 != 0 or (flags & 127) >> 2 != 3 or flags & 3:
        raise ValueError('only ACTIVITY/SLEEP_STAGES/DETAILS v2 is supported')
    if data[7] != 0:
        raise ValueError('unrecognized padding')
    body = data[8:-4]  # Never interpret CRC bytes as a sleep stage.
    total, bed, wake = struct.unpack_from('<hII', body, 7)
    deep, light, rem, awake = struct.unpack_from('<hhhh', body, 20)
    if not bed or wake <= bed or total <= 0:
        raise ValueError('empty or invalid sleep interval')
    if min(deep, light, rem, awake) < 0 or (len(body)-29) % 5:
        raise ValueError('unsupported duration or stage layout')
    changes = list(struct.iter_unpack('<IB', body[29:]))
    if any(b[0] <= a[0] for a, b in zip(changes, changes[1:])):
        raise ValueError('unordered/duplicate stage timestamps')
    stages = []
    for i, (ts, code) in enumerate(changes):
        end = changes[i+1][0] if i+1 < len(changes) else wake
        start, end = max(ts, bed), min(end, wake)
        if end > start:
            stages.append(dict(start=start, end=end, raw_code=code,
                               stage={2:'deep', 3:'light', 4:'rem', 5:'awake'}.get(code, 'unknown')))
    digest = hashlib.sha256(data).hexdigest()
    return dict(schema_version=1, device_id=device_id,
                event_id=hashlib.sha256((device_id+':'+digest).encode()).hexdigest(),
                source=dict(model='Xiaomi Smart Band 9 Pro', file_id=data[:7].hex(),
                            file_sha256=digest, file_timestamp=stamp, format_version=version,
                            timezone_offset_minutes=tz*15, parser='sleep-stages-v2/0.1',
                            hardware_validated=False),
                sleep=dict(start=bed, end=wake, total_minutes=total,
                           deep_minutes=deep, light_minutes=light, rem_minutes=rem,
                           awake_minutes=awake, stages=stages))


if __name__ == '__main__':
    print(json.dumps(parse_sleep(Path(sys.argv[1]).read_bytes(), sys.argv[2]),
                     ensure_ascii=False, indent=2))
