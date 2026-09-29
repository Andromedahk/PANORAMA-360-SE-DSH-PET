import struct
import unittest
from protocol import field, fields, frame, get, replace, request, take_frame, validate_response, varint, read_varint

class WireTests(unittest.TestCase):
    def test_request_golden(self):
        self.assertEqual(request(100, b'', 1), bytes.fromhex('54525958090000000a0408011001a20600'))

    def test_fragmented_and_concatenated_frames(self):
        packet = frame(b'abc') + frame(b'def')
        buf = bytearray()
        results = []
        for v in packet:
            buf.append(v)
            result = take_frame(buf)
            if result is not None:
                results.append(result)
        self.assertEqual(results, [b'abc', b'def'])
        self.assertFalse(buf)

    def test_bad_input(self):
        for data in (b'\x80', b'\xff'*11, b'\x00', b'\x0a\x05abc'):
            with self.assertRaises(ValueError):
                fields(data)
        with self.assertRaises(ValueError):
            take_frame(bytearray(b'TRYX' + struct.pack('<I', 0xffffffff)))

    def test_unknown_config_fields_preserved(self):
        unknown = varint(90 << 3 | 5) + b'\x01\x02\x03\x04'
        before = field(3, 'old') + unknown + field(50, b'opaque')
        after = replace(before, {3: 'new'})
        self.assertEqual(get(after, 3), b'new')
        self.assertIn(unknown, after)
        self.assertEqual(get(after, 50), b'opaque')

    def test_ack_and_track_validation(self):
        payload = field(1, field(2, 99)) + field(800, b'')
        self.assertEqual(validate_response(payload, 800, 99), b'')
        self.assertIsNone(validate_response(payload, 800, 100))
        with self.assertRaises(RuntimeError):
            validate_response(field(1, field(2, 99)) + field(800, field(1, 1)), 800, 99)
        with self.assertRaises(RuntimeError):
            validate_response(payload, 801, 99)

    def test_uint64(self):
        for n in (0, 127, 128, 16384, 2**64-1):
            self.assertEqual(read_varint(varint(n), 0)[0], n)

if __name__ == '__main__':
    unittest.main()
