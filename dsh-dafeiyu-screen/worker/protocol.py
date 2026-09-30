"""Minimal PASE wire codec. See THIRD_PARTY.md for protocol provenance."""
import struct

MAX_PAYLOAD = 4 * 1024 * 1024

def varint(n):
    if not 0 <= n < 2**64:
        raise ValueError('uint64 out of range')
    out = bytearray()
    while n > 127:
        out.append((n & 127) | 128)
        n >>= 7
    return bytes(out) + bytes([n])

def read_varint(data, pos):
    n = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise ValueError('Truncated varint')
        v = data[pos]
        pos += 1
        if shift == 63 and v > 1:
            raise ValueError('Varint overflow')
        n |= (v & 127) << shift
        if not v & 128:
            return n, pos
    raise ValueError('Varint overflow')

def field(number, value):
    if not 1 <= number < 2**29:
        raise ValueError('Invalid protobuf field number')
    if isinstance(value, int):
        return varint(number << 3) + varint(value)
    if isinstance(value, str):
        value = value.encode('utf-8')
    return varint(number << 3 | 2) + varint(len(value)) + value

def fields(data):
    """Return (number, wire type, value, original bytes), preserving unknowns."""
    pos, out = 0, []
    while pos < len(data):
        start = pos
        tag, pos = read_varint(data, pos)
        number, wire = tag >> 3, tag & 7
        if not 1 <= number < 2**29:
            raise ValueError('Invalid field tag')
        if wire == 0:
            value, pos = read_varint(data, pos)
        elif wire in (1, 2, 5):
            if wire == 2:
                size, pos = read_varint(data, pos)
            else:
                size = 8 if wire == 1 else 4
            if pos + size > len(data):
                raise ValueError('Truncated protobuf field')
            value, pos = data[pos:pos + size], pos + size
        else:
            raise ValueError('Unsupported protobuf wire type')
        out.append((number, wire, value, data[start:pos]))
    return out

def get(data, number, default=None):
    values = [value for key, _, value, _ in fields(data) if key == number]
    return values[-1] if values else default

def replace(data, updates):
    return b''.join(raw for n, _, _, raw in fields(data) if n not in updates) + b''.join(field(n, value) for n, value in updates.items())

def frame(payload):
    if not 0 < len(payload) <= MAX_PAYLOAD:
        raise ValueError('Invalid frame size')
    return b'TRYX' + struct.pack('<I', len(payload)) + payload

def take_frame(buffer):
    if len(buffer) < 8:
        return None
    if buffer[:4] != b'TRYX':
        raise ValueError('Invalid TRYX magic')
    size = struct.unpack_from('<I', buffer, 4)[0]
    if not 0 < size <= MAX_PAYLOAD:
        raise ValueError('Invalid TRYX frame length')
    if len(buffer) < size + 8:
        return None
    payload = bytes(buffer[8:8 + size])
    del buffer[:8 + size]
    return payload

def request(command, body, track, version=1):
    header = (field(1, version) if version else b'') + field(2, track)
    return frame(field(1, header) + field(command, body))

def validate_response(payload, expected, track):
    header = get(payload, 1)
    if header is None or get(header, 2, 0) != track:
        return None
    error = get(payload, 2, b'')
    if get(error, 1, 0):
        raise RuntimeError(f'Device error {get(error, 1)}: {get(error, 2, b"")!r}')
    body = get(payload, expected)
    if body is None:
        raise RuntimeError(f'Unexpected response; wanted field {expected}')
    if expected in (800, 801, 802) and get(body, 1, 0) != 0:
        raise RuntimeError(f'Transfer rejected: status {get(body, 1)}')
    return body
