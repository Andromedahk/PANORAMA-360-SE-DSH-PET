"""Decode this client's captured USB streams without accessing any hardware."""
import argparse
import json
from pathlib import Path
from protocol import fields, get, take_frame

NAMES = {10:'Ping/Pong',100:'DeviceInfoQuery',102:'SystemConfigQuery',103:'CatalogQuery',104:'UserConfigQuery',200:'SetUserConfig',201:'ApplyLayout',400:'TransferBegin',401:'TransferChunk',402:'TransferEnd',500:'DeviceInfo',502:'SystemConfig',503:'Catalog',504:'UserConfig',600:'Ack',800:'BeginStatus',801:'ChunkStatus',802:'EndStatus',987:'Event'}

def inspect(directory):
    directory = Path(directory).resolve()
    buffers = {'in': bytearray(), 'out': bytearray()}
    for line in (directory / 'events.jsonl').read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        name, direction = event['file'], event['direction']
        if Path(name).name != name or direction not in buffers:
            raise ValueError('Invalid capture entry')
        buffer = buffers[direction]
        buffer.extend((directory / name).read_bytes())
        while (payload := take_frame(buffer)) is not None:
            header = get(payload, 1, b'')
            record = {'direction': direction, 'version': get(header, 1, 0), 'track': get(header, 2, 0), 'bytes': len(payload), 'messages': []}
            for n, wire, value, _ in fields(payload):
                if n not in NAMES:
                    continue
                item = {'command': n, 'name': NAMES[n]}
                if n in (800, 801, 802):
                    item['status'] = get(value, 1, 0)
                elif n == 400:
                    item['file_name'] = get(value, 1, b'').decode(errors='replace')
                    item['file_size'] = get(value, 2, 0)
                elif n == 401:
                    item['chunk_bytes'] = len(get(value, 1, b''))
                record['messages'].append(item)
            print(json.dumps(record, ensure_ascii=False))
    if any(buffers.values()):
        raise ValueError('Capture ends with an incomplete frame')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    inspect(parser.parse_args().directory)
