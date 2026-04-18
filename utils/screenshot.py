import os
import json
import datetime
import tempfile
import tkinter as tk
from PIL import Image, ImageGrab, ImageTk


class Screenshot:
    '''截图管理类，负责截图的核心功能'''

    def __init__(self):
        '''初始化截图管理器'''
        # 截图保存目录
        self.screenshot_dir = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        # 截图记录数据文件
        self.data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'screenshots.json')
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'temp')
        self.screenshots = self.load_screenshots()

    def load_screenshots(self):
        '''从文件加载截图记录'''
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_screenshots(self):
        '''保存截图记录到文件'''
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.screenshots, f, ensure_ascii=False, indent=2)

    def capture_full_screen(self):
        '''捕获整个屏幕'''
        return ImageGrab.grab()

    def capture_region(self):
        '''捕获用户选择的区域'''
        selector = RegionSelector()
        return selector.get_region()

    def build_output_path(self):
        '''生成最终保存路径'''
        # 按日期创建目录
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        save_dir = os.path.join(self.screenshot_dir, date_str)
        os.makedirs(save_dir, exist_ok=True)

        # 生成文件名
        time_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'{time_str}.png'
        return os.path.join(save_dir, filename)

    def register_screenshot(self, filepath):
        '''将已保存截图写入历史记录'''
        filename = os.path.basename(filepath)
        self.screenshots = [s for s in self.screenshots if s.get('path') != filepath]
        self.screenshots.insert(0, {
            'path': filepath,
            'time': datetime.datetime.now().isoformat(),
            'filename': filename
        })
        self.save_screenshots()

    def save_screenshot(self, image):
        '''保存截图到最终目录并写入历史'''
        filepath = self.build_output_path()

        # 保存图片
        image.save(filepath)

        # 记录到数据文件
        self.register_screenshot(filepath)

        return filepath

    def create_temp_screenshot(self, image):
        '''将截图暂存到临时目录，等待用户确认保存'''
        os.makedirs(self.temp_dir, exist_ok=True)
        fd, filepath = tempfile.mkstemp(prefix='motto_', suffix='.png', dir=self.temp_dir)
        os.close(fd)
        image.save(filepath)
        return filepath

    def get_screenshots(self):
        '''获取所有截图记录'''
        return self.screenshots


class RegionSelector:
    '''区域选择器，用于在屏幕上选择截图区域'''

    def __init__(self, parent=None):
        '''初始化区域选择器

        Args:
            parent: 父窗口，如果提供则使用 Toplevel 否则创建独立窗口
        '''
        self.parent = parent
        self.result = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.root = None
        self.canvas = None
        self.background_image = None
        self.original_screenshot = None
        self.original_size = None
        self.display_size = None

    def get_region(self):
        '''获取用户选择的区域

        Returns:
            裁剪后的图片，如果取消则返回None
        '''
        # 先截取当前屏幕
        self.original_screenshot = ImageGrab.grab()
        self.original_size = self.original_screenshot.size

        if self.parent and self.parent.winfo_exists():
            screen_width = self.parent.winfo_screenwidth()
            screen_height = self.parent.winfo_screenheight()
        else:
            screen_width, screen_height = self.original_size
        self.display_size = (screen_width, screen_height)

        # 创建全屏选择窗口
        if self.parent:
            self.root = tk.Toplevel(self.parent)
        elif tk._default_root is not None:
            self.root = tk.Toplevel(tk._default_root)
        else:
            self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.geometry(f'{screen_width}x{screen_height}+0+0')
        self.root.configure(bg='black')

        # 创建画布
        self.canvas = tk.Canvas(
            self.root,
            width=screen_width,
            height=screen_height,
            highlightthickness=0,
            cursor='crosshair'
        )
        self.canvas.pack(fill='both', expand=True)
        display_image = self.original_screenshot
        if self.original_size != self.display_size:
            display_image = self.original_screenshot.resize(self.display_size, Image.LANCZOS)

        self.background_image = ImageTk.PhotoImage(display_image, master=self.canvas)
        self.canvas.create_image(0, 0, anchor='nw', image=self.background_image)

        # 提示区
        self.canvas.create_rectangle(20, 20, 420, 60, fill='black', outline='', stipple='gray50')
        self.canvas.create_text(
            32,
            40,
            anchor='w',
            text='拖拽选择区域，松开鼠标完成截图，右键或 Esc 取消',
            fill='white',
            font=('Arial', 13)
        )

        # 绑定鼠标事件
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Button-3>', self.cancel_selection)

        # 绑定键盘事件
        self.root.bind('<Escape>', self.cancel_selection)

        self.root.update_idletasks()
        self.root.lift()
        self.root.focus_force()
        self.canvas.focus_set()
        self.root.grab_set()

        # 等待选择窗口关闭
        self.root.wait_window()

        # 裁剪选中区域
        if self.result:
            x1, y1, x2, y2 = self.result
            left, top = min(x1, x2), min(y1, y2)
            width, height = abs(x2 - x1), abs(y2 - y1)
            if width > 0 and height > 0:
                scale_x = self.original_size[0] / self.display_size[0]
                scale_y = self.original_size[1] / self.display_size[1]
                orig_left = int(left * scale_x)
                orig_top = int(top * scale_y)
                orig_right = int((left + width) * scale_x)
                orig_bottom = int((top + height) * scale_y)
                return self.original_screenshot.crop((orig_left, orig_top, orig_right, orig_bottom))
        return None

    def on_click(self, event):
        '''鼠标按下事件，记录起始点'''
        self.start_x, self.start_y = event.x, event.y
        self.result = None
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def on_drag(self, event):
        '''鼠标拖拽事件，绘制选择框'''
        if self.rect_id:
            event.widget.delete(self.rect_id)
        self.rect_id = event.widget.create_rectangle(
            self.start_x, self.start_y, event.x, event.y, outline='red', width=2)

    def on_release(self, event):
        '''鼠标释放事件，记录选择结果'''
        self.result = (self.start_x, self.start_y, event.x, event.y)
        if abs(event.x - self.start_x) > 2 and abs(event.y - self.start_y) > 2:
            self.confirm_selection()
        else:
            self.result = None
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                self.rect_id = None

    def confirm_selection(self, event=None):
        '''确认当前选择'''
        if self.root and self.root.winfo_exists():
            try:
                self.root.grab_release()
            except tk.TclError:
                pass
            self.root.destroy()

    def cancel_selection(self, event=None):
        '''取消截图选择'''
        self.result = None
        self.confirm_selection()


def take_screenshot():
    '''执行区域截图的主函数

    Returns:
        保存的文件路径，如果取消则返回None
    '''
    screenshot = Screenshot()
    image = screenshot.capture_region()
    if image:
        return screenshot.save_screenshot(image)
    return None
