import os
import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser, messagebox
from PIL import Image, ImageDraw, ImageTk, ImageFont


class Annotator:
    '''图片标注器，提供画笔、箭头、矩形、椭圆、文字等标注功能'''

    def __init__(self, image_path, parent=None, on_save_callback=None, save_path=None, cleanup_source=False):
        '''初始化标注器

        Args:
            image_path: 要标注的图片路径
        '''
        self.parent = parent
        self.on_save_callback = on_save_callback
        self.image_path = image_path
        self.save_path = save_path or image_path
        self.cleanup_source = cleanup_source
        self._saved = False
        self.original_image = Image.open(image_path)
        self.image = self.original_image.copy()

        # 绘图相关变量
        self.draw = ImageDraw.Draw(self.image)
        self.tool = 'brush'  # 当前工具
        self.color = 'red'   # 画笔颜色
        self.line_width = 3  # 线宽
        self.font_size = 20  # 字体大小

        # 撤销相关
        self.history = [self.image.copy()]
        self.history_index = 0

        # 当前绘制状态
        self.drawing = False
        self.start_x = None
        self.start_y = None
        self.current_shape = None
        self.preview_item = None
        self.scale_x = 1
        self.scale_y = 1
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.status_label = None
        self.undo_btn = None
        self.canvas = None
        self.canvas_frame = None
        self.tk_image = None
        self.image_item_id = None
        self._owns_root = False

        # 创建窗口
        self.create_window()

    def create_window(self):
        '''创建标注窗口'''
        if self.parent:
            self.root = tk.Toplevel(self.parent)
        elif tk._default_root is not None:
            self.root = tk.Toplevel(tk._default_root)
        else:
            self.root = tk.Tk()
            self._owns_root = True
        self.root.title('图片标注')
        self.root.geometry('900x700')
        self.root.minsize(720, 520)
        self.set_initial_geometry()
        self.root.lift()
        self.root.focus_force()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-s>', lambda e: self.save_image())

        # 画布区域
        self.create_canvas()

        # 状态栏
        self.create_statusbar()

        # 工具栏
        self.create_toolbar()

        self.root.after_idle(self.refresh_canvas)

    def set_initial_geometry(self):
        '''设置初始窗口大小，避免默认全屏'''
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(max(self.image.width + 80, 900), screen_width - 120)
        height = min(max(self.image.height + 160, 700), screen_height - 120)
        x = max(20, (screen_width - width) // 2)
        y = max(20, (screen_height - height) // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_toolbar(self):
        '''创建工具栏'''
        toolbar = tk.Frame(self.root, bg='#333')
        toolbar.pack(fill='x', side='top')

        # 工具按钮
        tools = [
            ('画笔', 'brush'),
            ('箭头', 'arrow'),
            ('矩形', 'rectangle'),
            ('椭圆', 'ellipse'),
            ('文字', 'text')
        ]

        for text, tool in tools:
            btn = tk.Button(toolbar, text=text, command=lambda t=tool: self.set_tool(t),
                           bg='#555', fg='white', bd=0, padx=10, pady=5)
            btn.pack(side='left', padx=2, pady=2)

        # 颜色选择按钮
        color_btn = tk.Button(toolbar, text='颜色', command=self.choose_color,
                             bg='#555', fg='white', bd=0, padx=10, pady=5)
        color_btn.pack(side='left', padx=2, pady=2)

        # 线宽选择
        tk.Label(toolbar, text='线宽:', bg='#333', fg='white').pack(side='left', padx=(10, 0))
        self.width_var = tk.StringVar(value='3')
        width_combo = ttk.Combobox(
            toolbar,
            textvariable=self.width_var,
            values=['1', '2', '3', '5', '8'],
            width=5,
            state='readonly'
        )
        width_combo.pack(side='left')
        width_combo.bind('<<ComboboxSelected>>', lambda e: self.set_width())

        # 分隔
        tk.Frame(toolbar, bg='#555', width=2).pack(side='left', padx=5, fill='y')

        # 撤销按钮
        self.undo_btn = tk.Button(
            toolbar,
            text='撤回',
            command=self.undo,
            bg='#555',
            fg='white',
            bd=0,
            padx=10,
            pady=5,
            state='disabled'
        )
        self.undo_btn.pack(side='left', padx=2, pady=2)

        # 保存按钮
        save_btn = tk.Button(toolbar, text='保存', command=self.save_image,
                           bg='#4a90d9', fg='white', bd=0, padx=10, pady=5)
        save_btn.pack(side='right', padx=2, pady=2)

    def create_canvas(self):
        '''创建画布'''
        # 创建画布
        self.canvas_frame = tk.Frame(self.root, bg='#1e1e1e')
        self.canvas_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg='#1e1e1e', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # 绑定鼠标事件
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

    def create_statusbar(self):
        '''创建状态栏'''
        status = tk.Frame(self.root, bg='#eee', height=25)
        status.pack(fill='x', side='bottom')

        self.status_label = tk.Label(status, text='就绪', bg='#eee', fg='#333', anchor='w')
        self.status_label.pack(side='left', padx=10)

    def set_tool(self, tool):
        '''设置当前工具'''
        self.tool = tool
        if self.status_label is not None:
            self.status_label.config(text=f'当前工具: {tool}')

    def set_width(self):
        '''设置线宽'''
        self.line_width = int(self.width_var.get())

    def choose_color(self):
        '''选择颜色'''
        color = colorchooser.askcolor(title='选择颜色')[1]
        if color:
            self.color = color

    def save_history(self):
        '''保存当前状态到历史记录（用于撤销）'''
        # 清除当前状态之后的所有历史
        self.history = self.history[:self.history_index + 1]
        self.history.append(self.image.copy())
        self.history_index += 1
        self.update_undo_button()

    def undo(self):
        '''撤销上一步操作'''
        if self.history_index > 0:
            self.history_index -= 1
            self.image = self.history[self.history_index].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.refresh_canvas()
            if self.status_label is not None:
                self.status_label.config(text='已撤回')
            self.update_undo_button()

    def update_undo_button(self):
        '''更新撤回按钮状态'''
        if self.undo_btn is not None:
            state = 'normal' if self.history_index > 0 else 'disabled'
            self.undo_btn.config(state=state)

    def on_canvas_configure(self, event):
        '''画布大小变化时重绘图像'''
        self.refresh_canvas()

    def get_display_size(self):
        '''根据当前画布大小计算图片显示尺寸'''
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        img_width, img_height = self.image.size

        ratio = min(canvas_width / img_width, canvas_height / img_height)
        display_width = max(1, int(img_width * ratio))
        display_height = max(1, int(img_height * ratio))

        self.scale_x = img_width / display_width
        self.scale_y = img_height / display_height
        self.image_offset_x = max(0, (canvas_width - display_width) // 2)
        self.image_offset_y = max(0, (canvas_height - display_height) // 2)

        return display_width, display_height

    def refresh_canvas(self):
        '''刷新画布显示'''
        if self.canvas is None or not self.canvas.winfo_exists():
            return

        display_size = self.get_display_size()
        self.tk_image = ImageTk.PhotoImage(self.image.resize(display_size, Image.LANCZOS), master=self.root)
        self.canvas.delete('all')
        self.image_item_id = self.canvas.create_image(
            self.image_offset_x,
            self.image_offset_y,
            anchor='nw',
            image=self.tk_image
        )
        self.preview_item = None

    def to_image_coords(self, x, y):
        '''将画布坐标转换为原图坐标'''
        local_x = x - self.image_offset_x
        local_y = y - self.image_offset_y
        img_x = max(0, min(self.image.width - 1, int(local_x * self.scale_x)))
        img_y = max(0, min(self.image.height - 1, int(local_y * self.scale_y)))
        return img_x, img_y

    def clear_preview(self):
        '''清除预览图形'''
        if self.preview_item:
            self.canvas.delete(self.preview_item)
            self.preview_item = None

    def on_mouse_down(self, event):
        '''鼠标按下事件'''
        self.drawing = True
        self.start_x = event.x
        self.start_y = event.y
        self.clear_preview()

        # 文字工具特殊处理
        if self.tool == 'text':
            self.add_text(event.x, event.y)
            self.drawing = False

    def on_mouse_drag(self, event):
        '''鼠标拖拽事件'''
        if not self.drawing:
            return

        # 画笔工具直接绘制
        if self.tool == 'brush':
            start = self.to_image_coords(self.start_x, self.start_y)
            end = self.to_image_coords(event.x, event.y)
            self.draw.line([start, end], fill=self.color, width=self.line_width)
            self.start_x = event.x
            self.start_y = event.y
            self.refresh_canvas()
        elif self.tool in ['arrow', 'rectangle', 'ellipse']:
            self.draw_preview(self.start_x, self.start_y, event.x, event.y)

    def on_mouse_release(self, event):
        '''鼠标释放事件'''
        if not self.drawing:
            return

        self.drawing = False

        # 绘制最终形状
        if self.tool == 'arrow':
            start = self.to_image_coords(self.start_x, self.start_y)
            end = self.to_image_coords(event.x, event.y)
            self.draw_arrow(*start, *end)
        elif self.tool == 'rectangle':
            start = self.to_image_coords(self.start_x, self.start_y)
            end = self.to_image_coords(event.x, event.y)
            self.draw.rectangle([*start, *end], outline=self.color, width=self.line_width)
        elif self.tool == 'ellipse':
            start = self.to_image_coords(self.start_x, self.start_y)
            end = self.to_image_coords(event.x, event.y)
            self.draw.ellipse([*start, *end], outline=self.color, width=self.line_width)

        self.clear_preview()
        self.save_history()
        self.refresh_canvas()

    def draw_preview(self, x1, y1, x2, y2):
        '''绘制预览形状（带透明度）'''
        self.clear_preview()

        if self.tool == 'arrow':
            self.preview_item = self.canvas.create_line(
                x1, y1, x2, y2,
                fill=self.color,
                width=self.line_width,
                arrow=tk.LAST
            )
        elif self.tool == 'rectangle':
            self.preview_item = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=self.color,
                width=self.line_width
            )
        elif self.tool == 'ellipse':
            self.preview_item = self.canvas.create_oval(
                x1, y1, x2, y2,
                outline=self.color,
                width=self.line_width
            )

    def draw_arrow(self, x1, y1, x2, y2):
        '''绘制箭头'''
        # 绘制主线
        self.draw.line([x1, y1, x2, y2], fill=self.color, width=self.line_width)

        # 计算箭头角度
        import math
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 15

        # 计算箭头两点
        arrow_angle = math.pi / 6
        x3 = x2 - arrow_len * math.cos(angle - arrow_angle)
        y3 = y2 - arrow_len * math.sin(angle - arrow_angle)
        x4 = x2 - arrow_len * math.cos(angle + arrow_angle)
        y4 = y2 - arrow_len * math.sin(angle + arrow_angle)

        # 绘制箭头
        self.draw.line([x2, y2, x3, y3], fill=self.color, width=self.line_width)
        self.draw.line([x2, y2, x4, y4], fill=self.color, width=self.line_width)

    def get_text_font(self):
        '''获取支持中文的字体'''
        font_candidates = [
            'msyh.ttc',
            'msyhbd.ttc',
            'simhei.ttf',
            'simsun.ttc',
            'arialuni.ttf',
        ]
        fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')

        for font_name in font_candidates:
            font_path = os.path.join(fonts_dir, font_name)
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, self.font_size)
                except OSError:
                    pass

        try:
            return ImageFont.truetype('arial.ttf', self.font_size)
        except OSError:
            return ImageFont.load_default()

    def add_text(self, x, y):
        '''在指定位置添加文字'''
        # 创建文字输入对话框
        dialog = tk.Toplevel(self.root)
        dialog.title('输入文字')
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog_width = 340
        dialog_height = 150
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        dialog_x = min(
            max(20, self.canvas.winfo_rootx() + x + 16),
            max(20, screen_width - dialog_width - 20)
        )
        dialog_y = min(
            max(20, self.canvas.winfo_rooty() + y + 16),
            max(20, screen_height - dialog_height - 60)
        )
        dialog.geometry(f'{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}')

        # 输入框
        text_input = tk.Text(dialog, font=('Microsoft YaHei UI', 12), wrap='word', height=3)
        text_input.pack(fill='both', expand=True, padx=10, pady=(10, 6))

        hint_label = tk.Label(dialog, text='Ctrl+Enter 确定，Esc 取消', anchor='w', fg='#666')
        hint_label.pack(fill='x', padx=10)

        def focus_text():
            text_input.focus_force()
            text_input.mark_set('insert', 'end')

        dialog.after(50, focus_text)

        def confirm():
            text = text_input.get('1.0', 'end-1c').strip()
            if text:
                # 绘制文字
                font = self.get_text_font()
                image_x, image_y = self.to_image_coords(x, y)
                self.draw.text((image_x, image_y), text, fill=self.color, font=font)
                self.refresh_canvas()
                self.save_history()
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill='x', padx=10, pady=5)
        tk.Button(btn_frame, text='确定', command=confirm).pack(side='right', padx=2)
        tk.Button(btn_frame, text='取消', command=cancel).pack(side='right', padx=2)
        dialog.protocol('WM_DELETE_WINDOW', cancel)
        dialog.bind('<Control-Return>', lambda e: confirm())
        dialog.bind('<Escape>', lambda e: cancel())

    def save_image(self):
        '''保存标注后的图片'''
        save_dir = os.path.dirname(self.save_path)
        os.makedirs(save_dir, exist_ok=True)
        self.image.save(self.save_path)
        self._saved = True
        self.original_image = self.image.copy()
        if self.status_label is not None:
            self.status_label.config(text='已保存')
        if self.on_save_callback:
            self.on_save_callback(self.save_path)
        self.cleanup_temp_source()
        messagebox.showinfo('保存成功', f'图片已保存到: {self.save_path}')

    def cleanup_temp_source(self):
        '''清理临时截图文件'''
        if self.cleanup_source and self.image_path != self.save_path and os.path.exists(self.image_path):
            try:
                os.remove(self.image_path)
            except OSError:
                pass

    def close(self):
        '''关闭标注窗口'''
        if not self._saved:
            self.cleanup_temp_source()
        self.root.destroy()

    def run(self):
        '''运行标注器'''
        if self._owns_root:
            self.root.mainloop()


def open_annotator(image_path, parent=None, on_save_callback=None, save_path=None, cleanup_source=False):
    '''打开标注器的入口函数'''
    annotator = Annotator(
        image_path,
        parent=parent,
        on_save_callback=on_save_callback,
        save_path=save_path,
        cleanup_source=cleanup_source
    )
    annotator.run()
    return annotator


if __name__ == '__main__':
    # 测试
    import sys
    if len(sys.argv) > 1:
        open_annotator(sys.argv[1])
    else:
        print('请提供图片路径')
