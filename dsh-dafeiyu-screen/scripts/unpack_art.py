"""Restore bundled artwork to PNG using only the Python standard library."""
import argparse
import pathlib
import struct
import tarfile
import zlib


def pam_to_png(data):
    header, pixels = data.split(b'ENDHDR\n', 1)
    fields = dict(line.split(maxsplit=1) for line in header.splitlines()[1:])
    width, height = int(fields[b'WIDTH']), int(fields[b'HEIGHT'])
    if fields[b'DEPTH'] != b'4' or fields[b'MAXVAL'] != b'255' or len(pixels) != width * height * 4:
        raise ValueError('Unsupported PAM image')
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value))
    stride = width * 4
    rows = b''.join(b'\0' + pixels[y * stride:(y + 1) * stride] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='New output directory')
    args = parser.parse_args()
    dest = args.output.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    source = pathlib.Path(__file__).resolve().parents[1] / 'assets/art/dafeiyu/source-images.tar.xz'
    count = 0
    with tarfile.open(source, 'r:xz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            relative = pathlib.PurePosixPath(member.name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in member.name or ':' in member.name:
                raise ValueError('Unsafe archive path')
            target = dest.joinpath(*relative.parts)
            data = archive.extractfile(member).read()
            if target.suffix == '.pam':
                target = target.with_suffix('.png')
                data = pam_to_png(data)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            count += 1
    print(f'Restored {count} files to {dest}. PNG pixels are exact; encoded file hashes may differ.')


if __name__ == '__main__':
    main()
