"""Windows inbox usbprint transport; no replacement USB driver required."""
import ctypes as c
from ctypes import wintypes as w
import os
import uuid

if os.name != 'nt':
    raise ImportError('Windows only')

k = c.WinDLL('kernel32', use_last_error=True)
s = c.WinDLL('setupapi', use_last_error=True)
INVALID = c.c_void_p(-1).value

class GUID(c.Structure):
    _fields_ = [('raw', c.c_ubyte * 16)]

class INTERFACE(c.Structure):
    _fields_ = [('size', w.DWORD), ('guid', GUID), ('flags', w.DWORD), ('reserved', c.c_size_t)]

class OVERLAPPED(c.Structure):
    _fields_ = [('internal', c.c_size_t), ('internal_high', c.c_size_t),
                ('offset', w.DWORD), ('offset_high', w.DWORD), ('event', w.HANDLE)]

def bind(lib, name, restype, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = restype, args
    return fn

get_devices = bind(s, 'SetupDiGetClassDevsW', w.HANDLE, c.POINTER(GUID), w.LPCWSTR, w.HWND, w.DWORD)
enum_interface = bind(s, 'SetupDiEnumDeviceInterfaces', w.BOOL, w.HANDLE, c.c_void_p, c.POINTER(GUID), w.DWORD, c.POINTER(INTERFACE))
get_detail = bind(s, 'SetupDiGetDeviceInterfaceDetailW', w.BOOL, w.HANDLE, c.POINTER(INTERFACE), c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p)
destroy = bind(s, 'SetupDiDestroyDeviceInfoList', w.BOOL, w.HANDLE)
create_file = bind(k, 'CreateFileW', w.HANDLE, w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE)
close_handle = bind(k, 'CloseHandle', w.BOOL, w.HANDLE)
create_event = bind(k, 'CreateEventW', w.HANDLE, c.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR)
read_file = bind(k, 'ReadFile', w.BOOL, w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.POINTER(OVERLAPPED))
write_file = bind(k, 'WriteFile', w.BOOL, w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.POINTER(OVERLAPPED))
wait_one = bind(k, 'WaitForSingleObject', w.DWORD, w.HANDLE, w.DWORD)
result = bind(k, 'GetOverlappedResult', w.BOOL, w.HANDLE, c.POINTER(OVERLAPPED), c.POINTER(w.DWORD), w.BOOL)
cancel = bind(k, 'CancelIoEx', w.BOOL, w.HANDLE, c.POINTER(OVERLAPPED))
create_mutex = bind(k, 'CreateMutexW', w.HANDLE, c.c_void_p, w.BOOL, w.LPCWSTR)

def devices():
    guid = GUID((c.c_ubyte * 16).from_buffer_copy(uuid.UUID('28d78fad-5a12-11d1-ae5b-0000f803a8c2').bytes_le))
    handle = get_devices(c.byref(guid), None, None, 0x12)
    if handle == INVALID:
        raise c.WinError(c.get_last_error())
    paths = []
    try:
        index = 0
        while True:
            info = INTERFACE()
            info.size = c.sizeof(info)
            if not enum_interface(handle, None, c.byref(guid), index, c.byref(info)):
                if c.get_last_error() == 259:
                    break
                raise c.WinError(c.get_last_error())
            size = w.DWORD()
            get_detail(handle, c.byref(info), None, 0, c.byref(size), None)
            if not size.value:
                raise c.WinError(c.get_last_error())
            detail = c.create_string_buffer(size.value)
            c.cast(detail, c.POINTER(w.DWORD))[0] = 8 if c.sizeof(c.c_void_p) == 8 else 6
            if not get_detail(handle, c.byref(info), detail, size, None, None):
                raise c.WinError(c.get_last_error())
            path = c.wstring_at(c.addressof(detail) + 4)
            if 'vid_391a&pid_1021' in path.lower():
                paths.append(path)
            index += 1
    finally:
        destroy(handle)
    return paths

class Pending:
    def __init__(self, handle, data=None, size=65536):
        self.handle = handle
        self.buf = c.create_string_buffer(data) if data is not None else c.create_string_buffer(size)
        self.ov = OVERLAPPED()
        self.ov.event = create_event(None, True, False, None)
        if not self.ov.event:
            raise c.WinError(c.get_last_error())
        self.done = False
        fn = write_file if data is not None else read_file
        n = len(data) if data is not None else size
        if not fn(handle, self.buf, n, None, c.byref(self.ov)) and c.get_last_error() != 997:
            err = c.get_last_error()
            close_handle(self.ov.event)
            self.ov.event = None
            raise c.WinError(err)

    def finish(self, timeout_ms):
        state = wait_one(self.ov.event, timeout_ms)
        if state == 258:
            raise TimeoutError('USB response timed out')
        if state != 0:
            raise c.WinError(c.get_last_error())
        count = w.DWORD()
        if not result(self.handle, c.byref(self.ov), c.byref(count), False):
            raise c.WinError(c.get_last_error())
        self.done = True
        return self.buf.raw[:count.value]

    def close(self):
        if self.ov.event:
            if not self.done:
                cancel(self.handle, c.byref(self.ov))
                count = w.DWORD()
                # Keep the buffer alive until cancellation is acknowledged.
                result(self.handle, c.byref(self.ov), c.byref(count), True)
            close_handle(self.ov.event)
            self.ov.event = None

class Transport:
    def __init__(self, path):
        if path not in devices():
            raise ValueError('Not a connected TRYX PASE 391a:1021 interface')
        self.mutex = create_mutex(None, False, 'Local\\KanaliOpenScreen-PASE')
        error = c.get_last_error()
        if not self.mutex:
            raise c.WinError(error)
        if error == 183:
            close_handle(self.mutex)
            raise RuntimeError('另一个 Open Screen 实例正在使用屏幕，请先关闭它。')
        self.handle = create_file(path, 0xC0000000, 3, None, 3, 0x40000000, None)
        if self.handle == INVALID:
            error = c.get_last_error()
            close_handle(self.mutex)
            raise c.WinError(error)

    def arm_read(self):
        return Pending(self.handle)

    def write(self, data, timeout_ms=5000):
        op = Pending(self.handle, data=data)
        try:
            sent = len(op.finish(timeout_ms))
            if sent != len(data):
                raise OSError(f'Incomplete USB write: {sent}/{len(data)}; not retried')
        finally:
            op.close()

    def close(self):
        if self.handle != INVALID:
            close_handle(self.handle)
            self.handle = INVALID
            close_handle(self.mutex)
