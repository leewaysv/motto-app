import os
import json
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


class Thumbnails:
    '''缩略图窗口，显示最近截取的屏幕截图'''

    def __init__(self, parent, on_select_callback=None, on_close_callback=None):
        '''初始化缩略图窗口

        Args:
            parent: 父窗口
            on_select_callback: 选择图片时的回调函数
            on_close_callback: 关闭时的回调函数
        '''
        self.parent = parent
        self.on_select_callback = on_select_callback
        self.on_close_callback = on_close_callback

        # 数据文件路径
        self.data_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data',
            'screenshots.json'
        )
        self.screenshots = self.load_screenshots()

        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title('截图历史')
        self.window.geometry('400x500')
        self.window.transient(parent)
        self.window.minsize(320, 360)

        # 创建界面
        self.create_widgets()

        self.window.protocol('WM_DELETE_WINDOW', self.close)

    def load_screenshots(self):
        '''从文件加载截图记录'''
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def create_widgets(self):
        '''创建窗口控件'''
        # 标题栏
        title_frame = tk.Frame(self.window, bg='#4a90d9', height=30)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text='截图历史', bg='#4a90d9', fg='white',
                font=('Arial', 11, 'bold')).pack(side='left', padx=10)

        close_btn = tk.Button(title_frame, text='×', bg='#4a90d9', fg='white', bd=0,
                             font=('Arial', 12), command=self.close, width=2)
        close_btn.pack(side='right', padx=5)

        # 缩略图列表区域
        list_frame = tk.Frame(self.window)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')

        self.canvas = tk.Canvas(list_frame, yscrollcommand=scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.canvas.yview)

        # 内部框架用于放置缩略图
        self.inner_frame = tk.Frame(self.canvas)
        self.inner_window_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        self.inner_frame.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        self.window.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.inner_frame.bind('<MouseWheel>', self.on_mousewheel)

        # 加载缩略图
        self.load_thumbnails()

        # 更新滚动区域
        self.inner_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox('all'))

    def load_thumbnails(self):
        '''加载并显示缩略图'''
        # 缩略图大小
        thumb_width = 150
        thumb_height = 100
        visible_shots = [shot for shot in self.screenshots if shot.get('path') and os.path.exists(shot.get('path'))]

        # 清理已经不存在的历史项，并保证缩略图连续排列
        if len(visible_shots) != len(self.screenshots):
            self.screenshots = visible_shots
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.screenshots, f, ensure_ascii=False, indent=2)

        for index, shot in enumerate(visible_shots):
            path = shot.get('path')
            row = index // 2
            col = index % 2

            try:
                # 打开图片并创建缩略图
                img = Image.open(path)
                img.thumbnail((thumb_width, thumb_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img, master=self.window)

                # 创建缩略图框架
                frame = tk.Frame(self.inner_frame, bd=1, relief='solid')
                frame.grid(row=row, column=col, padx=5, pady=5)

                # 图片标签
                label = tk.Label(frame, image=photo, cursor='hand2')
                label.image = photo  # 保持引用
                label.pack()

                # 文件名
                filename = os.path.basename(path)
                name_label = tk.Label(frame, text=filename, font=('Arial', 8),
                        fg='#666', cursor='hand2')
                name_label.pack(pady=2)

                # 绑定点击事件
                for widget in (frame, label, name_label):
                    widget.bind('<Button-1>', lambda e, p=path: self.on_thumbnail_click(p))
                    widget.bind('<Button-3>', lambda e, p=path: self.show_context_menu(e, p))
                    widget.bind('<MouseWheel>', self.on_mousewheel)

            except Exception as e:
                print(f'加载缩略图失败: {e}')

        if not visible_shots:
            tk.Label(self.inner_frame, text='暂无截图记录',
                    font=('Arial', 12), fg='#999').pack(pady=20)

    def on_frame_configure(self, event=None):
        '''内部内容变化时更新滚动区域'''
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def on_canvas_configure(self, event):
        '''保持内部框架宽度跟随画布'''
        self.canvas.itemconfigure(self.inner_window_id, width=event.width)

    def on_mousewheel(self, event):
        '''处理鼠标滚轮滚动'''
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), 'units')

    def on_thumbnail_click(self, path):
        '''缩略图点击事件'''
        if self.on_select_callback:
            self.on_select_callback(path)
        else:
            # 默认使用系统图片查看器打开
            import subprocess
            try:
                subprocess.Popen(['cmd', '/c', 'start', '', path])
            except:
                messagebox.showerror('错误', '无法打开图片')

    def show_context_menu(self, event, path):
        '''显示右键菜单'''
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label='打开', command=lambda: self.on_thumbnail_click(path))
        menu.add_command(label='标注', command=lambda: self.open_annotator(path))
        menu.add_command(label='打开所在文件夹', command=lambda: self.open_folder(path))
        menu.add_separator()
        menu.add_command(label='删除', command=lambda: self.delete_screenshot(path))
        menu.post(event.x_root, event.y_root)

    def open_annotator(self, path):
        '''打开标注器'''
        from ui.screenshot.annotator import open_annotator
        open_annotator(path, parent=self.window, on_save_callback=lambda p: self.refresh())

    def open_folder(self, path):
        '''打开图片所在文件夹'''
        folder = os.path.dirname(path)
        import subprocess
        subprocess.Popen(['explorer', folder])

    def delete_screenshot(self, path):
        '''删除截图'''
        if messagebox.askyesno('确认', '确定要删除这张截图吗？'):
            try:
                os.remove(path)
                # 从记录中移除
                self.screenshots = [s for s in self.screenshots if s.get('path') != path]
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.screenshots, f, ensure_ascii=False, indent=2)
                # 刷新显示
                self.refresh()
            except Exception as e:
                messagebox.showerror('错误', f'删除失败: {e}')

    def refresh(self):
        '''刷新缩略图列表'''
        self.screenshots = self.load_screenshots()

        # 清除现有内容
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        # 重新加载
        self.load_thumbnails()

        # 更新滚动区域
        self.inner_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox('all'))

    def close(self):
        '''关闭窗口'''
        if self.on_close_callback:
            self.on_close_callback()
        self.window.destroy()


def create_thumbnails(parent, on_select_callback=None, on_close_callback=None):
    '''创建缩略图窗口的工厂函数'''
    return Thumbnails(parent, on_select_callback, on_close_callback)


if __name__ == '__main__':
    # 测试
    root = tk.Tk()
    root.title('测试')
    root.geometry('400x300')

    thumbnails = Thumbnails(root)

    root.mainloop()
