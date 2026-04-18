import os
import json
import tkinter as tk
from tkinter import font as tkfont


class MainWindow:
    '''桌面悬浮窗口类'''

    def __init__(self):
        '''初始化主窗口'''
        self.root = tk.Tk()
        self.root.withdraw()

        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
        self.config = self.load_config()

        self.setup_window()
        self.create_widgets()
        self.load_motto()

    def load_config(self):
        '''加载配置文件，如果不存在则使用默认配置'''
        default_config = {
            'x': 100,
            'y': 100,
            'width': 400,
            'height': 150,
            'alpha': 0.9,
            'visible': True,
            'always_on_top': True,
            'theme': 'light',
            'motto_text': '点击此处编辑座右铭'
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置和保存的配置
                    return {**default_config, **config}
            except:
                return default_config
        return default_config

    def save_config(self):
        '''保存配置到文件'''
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def setup_window(self):
        '''设置窗口属性'''
        self.window = tk.Toplevel(self.root)
        self.window.title('motto')
        # 设置透明度
        self.window.attributes('-alpha', self.config['alpha'])
        # 窗口置顶
        self.window.attributes('-topmost', self.config['always_on_top'])
        # 设置窗口大小和位置
        geo = f'{self.config["width"]}x{self.config["height"]}+{self.config["x"]}+{self.config["y"]}'
        self.window.geometry(geo)

        # 移除窗口边框，实现无装饰悬浮窗口
        self.window.overrideredirect(True)

        # 根据主题设置背景色
        bg_color = '#f5f5f5' if self.config['theme'] == 'light' else '#2b2b2b'
        self.window.configure(bg=bg_color)

        # 绑定拖拽移动事件
        self.window.bind('<Button-1>', self.start_drag)
        self.window.bind('<B1-Motion>', self.do_drag)
        # 右键菜单
        self.window.bind('<Button-3>', self.show_context_menu)

        # 绑定窗口位置变化事件，用于记忆位置
        self.window.bind('<Configure>', self.on_configure)

    def create_widgets(self):
        '''创建窗口控件'''
        # 根据主题设置颜色
        bg_color = '#f5f5f5' if self.config['theme'] == 'light' else '#2b2b2b'
        fg_color = '#333333' if self.config['theme'] == 'light' else '#ffffff'

        # 座右铭显示标签
        self.motto_label = tk.Label(
            self.window,
            text=self.config.get('motto_text', '点击此处编辑座右铭'),
            font=('Arial', 16, 'bold'),
            fg=fg_color,
            bg=bg_color,
            wraplength=self.config['width'] - 40,
            justify='center'
        )
        self.motto_label.pack(expand=True, fill='both', padx=20, pady=20)

        # 双击进入编辑模式
        self.motto_label.bind('<Double-Button-1>', self.edit_motto)

        # 关闭按钮
        self.close_btn = tk.Button(
            self.window,
            text='×',
            font=('Arial', 14),
            fg='#888',
            bg=bg_color,
            bd=0,
            command=self.hide_window,
            width=2
        )
        self.close_btn.place(relx=0.98, rely=0.02, anchor='ne')

    def load_motto(self):
        '''从配置加载座右铭文本'''
        if self.config.get('motto_text'):
            self.motto_label.config(text=self.config['motto_text'])

    def start_drag(self, event):
        '''开始拖拽，记录起始坐标'''
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def do_drag(self, event):
        '''执行拖拽移动窗口'''
        deltax = event.x - self.drag_start_x
        deltay = event.y - self.drag_start_y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f'+{x}+{y}')

    def on_configure(self, event):
        '''窗口位置或大小变化时保存配置'''
        if self.window.winfo_exists():
            self.config['x'] = self.window.winfo_x()
            self.config['y'] = self.window.winfo_y()
            self.config['width'] = self.window.winfo_width()
            self.config['height'] = self.window.winfo_height()
            self.save_config()

    def show_context_menu(self, event):
        '''显示右键菜单'''
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label='编辑座右铭', command=self.edit_motto)
        menu.add_command(label='显示/隐藏', command=self.toggle_visibility)
        menu.add_separator()
        menu.add_command(label='退出', command=self.quit_app)
        menu.post(event.x_root, event.y_root)

    def edit_motto(self, event=None):
        '''编辑座右铭对话框'''
        # 创建对话框
        dialog = tk.Toplevel(self.window)
        dialog.title('编辑座右铭')
        dialog.geometry('400x200')
        # 模态窗口
        dialog.transient(self.window)
        dialog.grab_set()

        # 居中显示
        dialog.geometry(f'400x200+{self.window.winfo_x() + 50}+{self.window.winfo_y() + 50}')

        # 文本输入框
        text = tk.Text(dialog, font=('Arial', 12), wrap='word', height=6)
        text.insert('1.0', self.config.get('motto_text', ''))
        text.pack(fill='both', expand=True, padx=10, pady=10)

        def save():
            '''保存座右铭'''
            self.config['motto_text'] = text.get('1.0', 'end-1c').strip()
            self.motto_label.config(text=self.config['motto_text'])
            self.save_config()
            dialog.destroy()

        def cancel():
            '''取消编辑'''
            dialog.destroy()

        # 按钮区域
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(btn_frame, text='保存', command=save).pack(side='right', padx=5)
        tk.Button(btn_frame, text='取消', command=cancel).pack(side='right')

        # 绑定回车保存，ESC取消
        dialog.bind('<Return>', lambda e: save())
        dialog.bind('<Escape>', lambda e: cancel())

    def toggle_visibility(self):
        '''切换窗口显示/隐藏状态'''
        if self.window.winfo_viewable():
            self.window.withdraw()
            self.config['visible'] = False
        else:
            self.window.deiconify()
            self.config['visible'] = True
        self.save_config()

    def hide_window(self):
        '''隐藏窗口'''
        self.window.withdraw()
        self.config['visible'] = False
        self.save_config()

    def show_window(self):
        '''显示窗口'''
        self.window.deiconify()
        self.config['visible'] = True
        self.save_config()

    def quit_app(self):
        '''退出应用程序'''
        self.save_config()
        self.root.quit()

    def run(self):
        '''运行主循环'''
        if self.config.get('visible', True):
            self.window.deiconify()
        self.root.mainloop()


if __name__ == '__main__':
    app = MainWindow()
    app.run()