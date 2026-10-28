import ctypes
import ctypes.wintypes
import psutil

u = ctypes.windll.user32
W = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
u.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
u.EnumWindows.argtypes = [W, ctypes.wintypes.LPARAM]
u.EnumWindows.restype = ctypes.wintypes.BOOL

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    cmd = ' '.join(p.info.get('cmdline') or [])
    if 'main.py' in cmd and p.info['name'].startswith('python'):
        pid = p.info['pid']
        print(f"Process {pid}: {cmd}")
        def cb(h, l):
            wpid = ctypes.wintypes.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(wpid))
            if wpid.value == pid:
                b = ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(h, b, 256)
                r = ctypes.wintypes.RECT()
                u.GetWindowRect(h, ctypes.byref(r))
                vis = bool(u.IsWindowVisible(h))
                print(f"  HWND {h}: '{b.value}', Vis: {vis}, Rect: ({r.left}, {r.top}, {r.right}, {r.bottom}), Size: {r.right-r.left}x{r.bottom-r.top}")
            return True
        u.EnumWindows(W(cb), 0)
