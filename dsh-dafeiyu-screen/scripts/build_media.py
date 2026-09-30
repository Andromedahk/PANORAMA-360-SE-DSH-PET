"""Compose supplied RGBA frames without altering their artwork; FFmpeg handles compositing."""
import argparse, hashlib, json, pathlib, shutil, subprocess, tempfile, zipfile

def source_hash(path):
    path = pathlib.Path(path)
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    for i in range(60):
        name = f'frame_{i:03d}.png'
        digest.update(name.encode('ascii'))
        digest.update((path / name).read_bytes())
    return digest.hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--frames', required=True, help='ZIP archive or folder containing frame_000.png through frame_059.png')
    p.add_argument('--background', required=True)
    p.add_argument('--ffmpeg', default=r'C:\Program Files\KANALI\resources\Connect\ffmpeg\ffmpeg.exe')
    a = p.parse_args()
    out = pathlib.Path(__file__).resolve().parents[1] / 'assets'
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dafeiyu-') as tmp:
        if pathlib.Path(a.frames).is_dir():
            for i in range(60):
                name = f'frame_{i:03d}.png'
                shutil.copyfile(pathlib.Path(a.frames, name), pathlib.Path(tmp, name))
        else:
            with zipfile.ZipFile(a.frames) as z:
                for i in range(60):
                    name = f'frame_{i:03d}.png'
                    pathlib.Path(tmp, name).write_bytes(z.read(name))
        args = [a.ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                '-loop', '1', '-framerate', '30', '-i', a.background,
                '-framerate', '30', '-i', str(pathlib.Path(tmp, 'frame_%03d.png')),
                '-filter_complex', '[0:v]scale=2240:1080:force_original_aspect_ratio=increase,crop=2240:1080,setsar=1[bg];[1:v]scale=1722:1060[fish];[bg][fish]overlay=227:10:shortest=1,format=yuv420p[v]',
                '-map', '[v]', '-frames:v', '60', '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                '-r', '30', '-g', '30', '-bf', '0', '-x264-params', 'scenecut=0:force-cfr=1', '-movflags', '+faststart', str(out/'tail-swing.mp4')]
        subprocess.run(args, check=True, timeout=300)
    subprocess.run([a.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(out/'tail-swing.mp4'), '-c:v', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'h264', str(out/'tail-swing.h264')], check=True)
    subprocess.run([a.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(out/'tail-swing.mp4'), '-frames:v', '1', str(out/'preview.jpg')], check=True)
    subprocess.run([a.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(out/'tail-swing.mp4'), '-c:v', 'libvpx-vp9', '-crf', '28', '-b:v', '0', '-row-mt', '1', '-an', str(out/'tail-swing.webm')], check=True, timeout=300)
    info = {'width':2240, 'height':1080, 'fps':30, 'frames':60, 'seconds':2,
            'composition':{'fishWidth':1722,'fishHeight':1060,'fishX':227,'fishY':10,'fishBottom':1070,'visibleUnionSource':[88,0,1638,1024]},
            'sources':{pathlib.Path(x).name:source_hash(x) for x in [a.frames,a.background]},
            'h264Sha256':hashlib.sha256((out/'tail-swing.h264').read_bytes()).hexdigest()}
    (out/'media.json').write_text(json.dumps(info, indent=2),encoding='utf8')
    print(json.dumps(info))

if __name__ == '__main__': main()
