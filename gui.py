"""Small Tk desktop frontend; all USB work is serialized on one worker."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from screen import Client, ROOT, prepare

class App:
    def __init__(self, root):
        self.root = root
        self.jobs, self.events = queue.Queue(), queue.Queue()
        self.stopping = threading.Event()
        self.busy = False
        self.source = ''
        root.title('Open Screen · 展域 360 SE')
        root.geometry('780x590')
        root.minsize(650, 480)
        root.configure(bg='#101c2c')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Microsoft YaHei UI', 11), padding=10)
        outer = tk.Frame(root, bg='#101c2c', padx=28, pady=24)
        outer.pack(fill='both', expand=True)
        tk.Label(outer, text='OPEN SCREEN', font=('Segoe UI', 27, 'bold'), fg='#50d8c4', bg='#101c2c').pack(anchor='w')
        tk.Label(outer, text='展域 360 SE  ·  2240 × 1080  ·  独立 USB 传输', font=('Microsoft YaHei UI', 11), fg='#b0c1d5', bg='#101c2c').pack(anchor='w', pady=(3, 20))
        tk.Label(outer, text='使用前退出 KANALI。窗口保持打开可维持屏幕连接。', font=('Microsoft YaHei UI', 10), fg='#b0c1d5', bg='#101c2c').pack(anchor='w')
        self.file_label = tk.Label(outer, text='选择 PNG、JPG、GIF 或视频', wraplength=690, anchor='w', justify='left', font=('Microsoft YaHei UI', 11), fg='white', bg='#203148', padx=16, pady=18)
        self.file_label.pack(fill='x', pady=15)
        row = tk.Frame(outer, bg='#101c2c')
        row.pack(fill='x')
        self.buttons = []
        for label, fn in [('选择文件', self.choose), ('发送到屏幕', self.send), ('读取设备', lambda: self.start('info')), ('恢复测试前画面', self.restore)]:
            button = ttk.Button(row, text=label, command=fn)
            button.pack(side='left', padx=(0, 8))
            self.buttons.append(button)
        self.status = tk.StringVar(value='就绪 · 图片已实机验证；GIF 和视频尚待验证')
        tk.Label(outer, textvariable=self.status, font=('Microsoft YaHei UI', 10), fg='#50d8c4', bg='#101c2c', wraplength=690, justify='left').pack(anchor='w', pady=15)
        self.log = tk.Text(outer, height=9, bg='#0a1320', fg='#bdcce0', relief='flat', font=('Consolas', 10), padx=12, pady=12, state='disabled')
        self.log.pack(fill='both', expand=True)
        tk.Label(outer, text='图片按比例完整显示，多余区域填黑。关闭窗口后释放 USB 连接。', font=('Microsoft YaHei UI', 9), fg='#8194ac', bg='#101c2c').pack(anchor='w', pady=(12, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()
        root.after(100, self.poll)

    def choose(self):
        path = filedialog.askopenfilename(filetypes=[('图片和视频', '*.png *.jpg *.jpeg *.bmp *.webp *.gif *.mp4 *.mkv *.avi *.mov *.webm')])
        if path:
            self.source = path
            self.file_label.configure(text=path)

    def send(self):
        if not self.source:
            self.choose()
        if self.source:
            self.start('send', self.source)

    def restore(self):
        path = ROOT / 'captures' / 'before-test-config.bin'
        if path.exists():
            self.start('restore', str(path))
        else:
            self.status.set('没有本机测试前配置备份。')

    def start(self, action, path=None):
        if self.busy:
            return
        self.busy = True
        for button in self.buttons:
            button.configure(state='disabled')
        self.status.set('处理中…')
        self.jobs.put((action, path))

    def emit(self, message):
        self.events.put(('log', message))

    def worker(self):
        client = None
        try:
            while not self.stopping.is_set():
                try:
                    action, path = self.jobs.get(timeout=2)
                except queue.Empty:
                    if client:
                        try:
                            client.ping()
                        except Exception as exc:
                            self.events.put(('status', f'连接已中断：{exc}'))
                            client.close()
                            client = None
                    continue
                try:
                    if action == 'send':
                        self.emit('正在转换媒体…')
                        media = prepare(path)
                    if client is None:
                        client = Client()
                        info = client.info()
                        self.emit(f'已连接 {info.get("product")}，固件 {info.get("firmware")}')
                        self.emit(f'收发记录：{client.capture.path}')
                    if action == 'send':
                        # Save the previous selection before any media writes.
                        old = client.command(104, expected=504)
                        import uuid
                        backup = client.capture.path / ('before-send-' + uuid.uuid4().hex[:8] + '.bin')
                        backup.write_bytes(old)
                        client.upload(media, media.name, self.emit)
                        client.apply(media.name)
                        self.emit('上传和配置回读成功，请查看实体屏幕。')
                    elif action == 'restore':
                        client.restore(path)
                        self.emit('原显示配置已恢复，并通过回读验证。')
                    else:
                        for item in client.catalog():
                            if not item['preset']:
                                self.emit(item['path'])
                    self.events.put(('status', '完成 · 正在维持屏幕连接'))
                except Exception as exc:
                    self.emit(f'操作未完成：{exc}')
                    self.events.put(('status', '操作失败，详见日志；不会自动重试上传。'))
                    if client:
                        client.close()
                        client = None
                finally:
                    self.events.put(('done', None))
        finally:
            if client:
                client.close()

    def poll(self):
        while True:
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'log':
                self.log.configure(state='normal')
                self.log.insert('end', text + '\n')
                self.log.see('end')
                self.log.configure(state='disabled')
            elif kind == 'status':
                self.status.set(text)
            elif kind == 'done':
                self.busy = False
                for button in self.buttons:
                    button.configure(state='normal')
        if self.stopping.is_set() and not self.thread.is_alive():
            self.root.destroy()
            return
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            self.status.set('当前操作完成后即可关闭，以免中断媒体传输。')
            return
        self.status.set('正在释放屏幕连接…')
        for button in self.buttons:
            button.configure(state='disabled')
        self.stopping.set()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
