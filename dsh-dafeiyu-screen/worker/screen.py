"""Independent experimental Windows client for TRYX Panorama SE (391a:1021)."""
import argparse
import datetime
import json
import pathlib
import shutil
import subprocess
import time
import uuid
from protocol import field, fields, get, replace, request, take_frame, validate_response

ROOT = pathlib.Path(__file__).resolve().parent

class Capture:
    def __init__(self):
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        self.path = ROOT / 'captures' / stamp
        self.path.mkdir(parents=True)
        self.count = 0

    def record(self, direction, data):
        self.count += 1
        name = f'{self.count:05d}-{direction}.bin'
        (self.path / name).write_bytes(data)
        with (self.path / 'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'time': time.time(), 'direction': direction, 'bytes': len(data), 'file': name}) + '\n')

class Client:
    def __init__(self):
        from winusbprint import Transport, devices
        # Refuse simultaneous ownership, even when CreateFile allows sharing.
        listing = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], creationflags=0x08000000).decode(errors='replace').lower()
        if '"kanali.exe"' in listing or '"screen.exe"' in listing:
            raise RuntimeError('请先从系统托盘完全退出 KANALI（及 Screen.exe 后台进程），避免同时读写屏幕。')
        paths = devices()
        if len(paths) != 1:
            raise RuntimeError(f'Expected one PASE screen; found {len(paths)}')
        self.transport = Transport(paths[0])
        self.capture = Capture()
        self.buffer = bytearray()
        self.syncing = True
        self.track = int(time.time() * 1000)

    def close(self):
        self.transport.close()

    def command(self, command, body=b'', expected=None, track=None, optional_ack=False, capture=True):
        if track is None:
            self.track += 1
            track = self.track
        data = request(command, body, track, 0 if command in (400, 401, 402) else 1)
        timeout = 0.3 if optional_ack else 30 if command in (400, 401, 402) else 5
        deadline = time.monotonic() + timeout
        pending = self.transport.arm_read()
        try:
            if capture:
                self.capture.record('out', data)
            self.transport.write(data, 30000 if command in (400, 401, 402) else 5000)
            for _ in range(100):
                # A previous owner may have closed after reading half a response.
                # Recover framing only during this connection's first handshake;
                # track-id matching below still rejects all stale responses.
                if self.syncing and len(self.buffer) >= 4 and self.buffer[:4] != b'TRYX':
                    offset = self.buffer.find(b'TRYX')
                    if offset < 0:
                        del self.buffer[:-3]
                    else:
                        del self.buffer[:offset]
                payload = take_frame(self.buffer)
                if payload is not None:
                    result = validate_response(payload, expected, track)
                    if result is not None:
                        self.syncing = False
                        return result
                    continue
                left = deadline - time.monotonic()
                if left <= 0:
                    if optional_ack and not self.buffer:
                        return None
                    raise TimeoutError('No matching device acknowledgement; outcome unknown, not retried')
                if pending is None:
                    pending = self.transport.arm_read()
                try:
                    chunk = pending.finish(max(1, int(left * 1000)))
                except TimeoutError:
                    if optional_ack and not self.buffer:
                        return None
                    raise
                pending.close()
                pending = None
                if not chunk:
                    raise OSError('Empty USB response')
                if capture:
                    self.capture.record('in', chunk)
                self.buffer.extend(chunk)
            raise RuntimeError('Too many unmatched responses')
        finally:
            if pending is not None:
                pending.close()

    def info(self):
        body = self.command(100, expected=500)
        labels = {1:'os', 2:'os_version', 3:'firmware', 4:'product', 5:'app', 8:'serial', 10:'chip'}
        return {labels[n]: v.decode('utf-8', errors='replace') for n, wire, v, _ in fields(body) if n in labels and wire == 2}

    def catalog(self):
        body = self.command(103, expected=503)
        return [{'path': get(v, 1, b'').decode('utf-8', errors='replace'), 'size': get(v, 3, 0), 'preset': n == 2} for n, wire, v, _ in fields(body) if n in (1, 2) and wire == 2]

    def upload(self, path, remote, progress=print):
        size = path.stat().st_size
        if not 0 < size <= 256 * 1024 * 1024:
            raise ValueError('Prepared media must be between 1 byte and 256 MiB')
        self.track += 1
        track = self.track
        self.command(400, field(1, remote) + field(2, size), 800, track)
        sent = 0
        with path.open('rb') as f:
            while data := f.read(0x40000):
                self.command(401, field(1, data), 801, track)
                sent += len(data)
                progress(f'上传 {sent}/{size} bytes')
        if sent != size:
            raise RuntimeError('Source changed during transfer; upload not finalized')
        self.command(402, field(1, 'media'), 802, track)

    def apply(self, remote):
        old = self.command(104, expected=504)
        work, display = get(old, 3), get(old, 5)
        if work is None or display is None:
            raise RuntimeError('Device configuration incomplete; refusing to invent defaults')
        (self.capture.path / 'previous-config.bin').write_bytes(old)
        new_work = replace(work, {1: 0, 2: 0, 3: remote})
        new_display = replace(display, {1: 1})
        new = replace(old, {3: new_work, 5: new_display})
        self.command(200, new, 600)
        # Empty OverlayLayout applies the media without telemetry overlays.
        self.command(201, b'', 600, optional_ack=True)
        readback = self.command(104, expected=504)
        if get(get(readback, 3, b''), 3) != remote.encode():
            raise RuntimeError('Apply was acknowledged but media selection readback differs')
        return True

    def restore(self, path):
        saved = pathlib.Path(path).read_bytes()
        if len(saved) > 1024 * 1024 or get(saved, 3) is None or get(saved, 5) is None:
            raise ValueError('Invalid saved display configuration')
        current = self.command(104, expected=504)
        (self.capture.path / 'before-restore-config.bin').write_bytes(current)
        self.command(200, saved, 600)
        self.command(201, b'', 600, optional_ack=True)
        actual = self.command(104, expected=504)
        for section, keys in ((3, range(1, 8)), (5, range(1, 6))):
            for key in keys:
                default = b'' if section == 3 and key in (3, 4, 5, 6) else 0
                if get(get(saved, section, b''), key, default) != get(get(actual, section, b''), key, default):
                    raise RuntimeError('Restore write completed but readback differs')

    def ping(self):
        return self.command(10, field(1, 'hello?'), 10, capture=False)

def find_ffmpeg():
    found = shutil.which('ffmpeg')
    bundled = pathlib.Path(r'C:\Program Files\KANALI\resources\Connect\ffmpeg\ffmpeg.exe')
    if found:
        return found
    if bundled.is_file():
        return str(bundled)
    raise RuntimeError('请安装 FFmpeg 并加入 PATH，或用 --ffmpeg 指定路径。')

def prepare(source, ffmpeg=None):
    source = pathlib.Path(source).resolve(strict=True)
    ext = source.suffix.lower()
    still = ext in ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
    if not still and ext not in ('.gif', '.mp4', '.mkv', '.avi', '.mov', '.webm'):
        raise ValueError('Unsupported image / video extension')
    kind = 'png' if still else 'gif' if ext == '.gif' else 'mp4'
    name = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8] + f'.{kind}.h264_2240x1080'
    output = ROOT / 'prepared' / name
    output.parent.mkdir(exist_ok=True)
    args = [ffmpeg or find_ffmpeg(), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n']
    if still:
        args += ['-loop', '1', '-framerate', '30', '-t', '60']
    args += ['-i', str(source), '-map', '0:v:0', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '30', '-preset', 'veryfast', '-crf', '23', '-vf', 'scale=2240:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=2240:1080:(ow-iw)/2:(oh-ih)/2,setsar=1', '-an', '-f', 'h264', str(output)]
    subprocess.run(args, check=True, timeout=900, creationflags=0x08000000)
    if not 0 < output.stat().st_size <= 256 * 1024 * 1024:
        raise ValueError('Encoded media exceeds upload size limit')
    return output

def main():
    parser = argparse.ArgumentParser(description='TRYX 展域 360 SE 开源屏幕工具（实验版）')
    parser.add_argument('command', choices=['devices', 'info', 'catalog', 'prepare', 'send', 'restore'])
    parser.add_argument('file', nargs='?')
    parser.add_argument('--ffmpeg')
    args = parser.parse_args()
    if args.command == 'devices':
        from winusbprint import devices
        print(json.dumps(devices(), ensure_ascii=False, indent=2))
        return
    media = None
    if args.command in ('prepare', 'send'):
        if not args.file:
            parser.error('An input image or video is required')
        media = prepare(args.file, args.ffmpeg)
        print(f'媒体已转换: {media}', flush=True)
        if args.command == 'prepare':
            return
    client = Client()
    try:
        print(f'通信日志: {client.capture.path}', flush=True)
        print(json.dumps(client.info(), ensure_ascii=False, indent=2), flush=True)
        if args.command == 'catalog':
            print(json.dumps(client.catalog(), ensure_ascii=False, indent=2))
        elif args.command == 'send':
            client.upload(media, media.name)
            client.apply(media.name)
            print('上传和配置回读成功。请检查实体屏幕是否正确显示。')
        elif args.command == 'restore':
            if not args.file:
                parser.error('A saved configuration file is required')
            client.restore(args.file)
            print('原显示配置已恢复并通过回读验证。')
    finally:
        client.close()

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'失败: {exc}')
        raise SystemExit(1)
