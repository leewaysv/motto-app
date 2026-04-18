import queue
import tkinter as tk
from tkinter import messagebox
from pynput import keyboard
from ui.main_window import MainWindow
from ui.todo_view import TodoView
from ui.screenshot.thumbnails import Thumbnails
from ui.screenshot.annotator import open_annotator
from utils.tray import SystemTray


class MottoApp:
    '''motto主应用程序类，整合所有功能模块'''

    DEFAULT_HOTKEYS = {
        'take_screenshot': ['Ctrl+Shift+S', 'Ctrl+Alt+S'],
        'toggle_main_window': ['Ctrl+Shift+M'],
        'toggle_todo': ['Ctrl+Shift+T'],
    }

    HOTKEY_LABELS = {
        'take_screenshot': '截图',
        'toggle_main_window': '显示/隐藏主窗口',
        'toggle_todo': '备忘录',
    }

    def __init__(self):
        '''初始化应用程序'''
        # 主窗口及唯一的 Tk 根窗口
        self.main_window = MainWindow()
        self.root = self.main_window.root
        self.window = self.main_window.window
        self.config = self.main_window.config

        # Todo视图（初始不创建，需要时再创建）
        self.todo_view = None

        # 缩略图窗口（初始不创建）
        self.thumbnails_window = None

        # 快捷键设置窗口
        self.hotkey_dialog = None
        self.hotkey_entries = {}

        # 系统托盘
        self.tray = SystemTray(self)

        # 截图结束后是否恢复主窗口
        self._restore_window_after_screenshot = False

        # 跨线程 UI 调度队列
        self.ui_queue = queue.Queue()
        self.root.after(50, self.process_ui_queue)

        # 注册全局快捷键
        self.register_hotkeys()

    def register_hotkeys(self):
        '''注册全局快捷键'''
        hotkey_map = self.get_hotkey_bindings()
        # 使用专门的全局热键注册，避免手动维护按键状态
        self.listener = keyboard.GlobalHotKeys(hotkey_map)
        self.listener.daemon = True
        self.listener.start()

    def stop_hotkeys(self):
        '''停止全局快捷键监听'''
        if getattr(self, 'listener', None):
            self.listener.stop()
            self.listener = None

    def normalize_hotkey_list(self, value, fallback):
        '''规范化热键列表配置'''
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            value = fallback

        normalized = []
        for item in value:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if text:
                normalized.append(text)

        return normalized or fallback

    def get_hotkey_config(self):
        '''读取并修正热键配置'''
        configured = self.config.get('hotkeys', {})
        if not isinstance(configured, dict):
            configured = {}

        hotkeys = {}
        for action, fallback in self.DEFAULT_HOTKEYS.items():
            hotkeys[action] = self.normalize_hotkey_list(configured.get(action), fallback)

        self.config['hotkeys'] = hotkeys
        return hotkeys

    def parse_hotkey_display_list(self, text):
        '''解析用户输入的热键列表'''
        raw_items = []
        for chunk in text.replace('\n', ',').replace('，', ',').split(','):
            item = chunk.strip()
            if item:
                raw_items.append(item)
        return raw_items

    def display_to_pynput(self, hotkey_text):
        '''将显示形式的热键转为 pynput 所需格式'''
        key_map = {
            'CTRL': '<ctrl>',
            'CONTROL': '<ctrl>',
            'SHIFT': '<shift>',
            'ALT': '<alt>',
            'OPTION': '<alt>',
            'WIN': '<cmd>',
            'CMD': '<cmd>',
            'ENTER': '<enter>',
            'RETURN': '<enter>',
            'ESC': '<esc>',
            'ESCAPE': '<esc>',
            'SPACE': '<space>',
            'TAB': '<tab>',
            'BACKSPACE': '<backspace>',
            'DELETE': '<delete>',
            'UP': '<up>',
            'DOWN': '<down>',
            'LEFT': '<left>',
            'RIGHT': '<right>',
            'HOME': '<home>',
            'END': '<end>',
            'PAGEUP': '<page_up>',
            'PAGEDOWN': '<page_down>',
        }

        tokens = [token.strip() for token in hotkey_text.replace(' ', '').split('+') if token.strip()]
        if not tokens:
            raise ValueError('不能为空')

        parsed = []
        for token in tokens:
            upper = token.upper()
            if upper in key_map:
                parsed.append(key_map[upper])
            elif upper.startswith('F') and upper[1:].isdigit():
                parsed.append(f'<{upper.lower()}>')
            elif len(token) == 1 and token.isalnum():
                parsed.append(token.lower())
            else:
                raise ValueError(f'不支持的按键: {token}')

        if all(part.startswith('<') for part in parsed):
            raise ValueError('需要包含一个普通按键')

        return '+'.join(parsed)

    def format_hotkey_text(self, hotkey_text):
        '''格式化热键显示文本'''
        tokens = [token.strip() for token in hotkey_text.replace(' ', '').split('+') if token.strip()]
        formatted = []
        for token in tokens:
            upper = token.upper()
            if len(token) == 1:
                formatted.append(token.upper())
            elif upper in {'CTRL', 'CONTROL'}:
                formatted.append('Ctrl')
            elif upper == 'SHIFT':
                formatted.append('Shift')
            elif upper in {'ALT', 'OPTION'}:
                formatted.append('Alt')
            elif upper in {'ESC', 'ESCAPE'}:
                formatted.append('Esc')
            elif upper.startswith('F') and upper[1:].isdigit():
                formatted.append(upper)
            else:
                formatted.append(token.capitalize())
        return '+'.join(formatted)

    def get_hotkey_bindings(self):
        '''构建 pynput 监听配置'''
        config = self.get_hotkey_config()
        bindings = {}
        duplicates = {}

        action_callbacks = {
            'take_screenshot': self.take_screenshot,
            'toggle_main_window': self.toggle_main_window,
            'toggle_todo': self.toggle_todo,
        }

        for action, hotkeys in config.items():
            callback = action_callbacks[action]
            for hotkey_text in hotkeys:
                pynput_key = self.display_to_pynput(hotkey_text)
                if pynput_key in bindings:
                    duplicates.setdefault(pynput_key, []).append(action)
                    continue
                bindings[pynput_key] = lambda cb=callback: self.post_ui_task(cb)

        if duplicates:
            duplicate_text = ', '.join(duplicates.keys())
            raise ValueError(f'快捷键重复: {duplicate_text}')

        return bindings

    def save_app_config(self):
        '''保存应用配置'''
        self.main_window.save_config()

    def update_tray_menu(self):
        '''刷新托盘菜单'''
        if self.tray and self.tray.icon:
            self.tray.icon.menu = self.tray.create_menu()

    def apply_hotkey_settings(self, hotkey_config):
        '''应用并保存热键设置'''
        normalized = {}
        seen = {}

        for action, values in hotkey_config.items():
            if not values:
                raise ValueError(f'{self.HOTKEY_LABELS[action]} 至少保留一个快捷键')

            formatted_values = []
            for value in values:
                formatted = self.format_hotkey_text(value)
                pynput_key = self.display_to_pynput(formatted)
                owner = seen.get(pynput_key)
                if owner and owner != action:
                    raise ValueError(
                        f'快捷键 {formatted} 同时用于“{self.HOTKEY_LABELS[owner]}”和“{self.HOTKEY_LABELS[action]}”'
                    )
                seen[pynput_key] = action
                if formatted not in formatted_values:
                    formatted_values.append(formatted)

            normalized[action] = formatted_values

        self.stop_hotkeys()
        self.config['hotkeys'] = normalized
        self.save_app_config()
        self.register_hotkeys()
        self.update_tray_menu()

    def show_hotkey_settings(self):
        '''显示快捷键设置窗口'''
        if self.hotkey_dialog is not None and self.hotkey_dialog.winfo_exists():
            self.hotkey_dialog.deiconify()
            self.hotkey_dialog.lift()
            self.hotkey_dialog.focus_force()
            return

        parent = self.window if self.window.winfo_exists() else self.root
        dialog = tk.Toplevel(parent)
        dialog.title('快捷键设置')
        dialog.geometry('480x260')
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        if self.window.winfo_exists():
            x = self.window.winfo_x() + 40
            y = self.window.winfo_y() + 40
            dialog.geometry(f'480x260+{x}+{y}')

        self.hotkey_dialog = dialog
        self.hotkey_entries = {}
        current_hotkeys = self.get_hotkey_config()

        def close_dialog():
            self.hotkey_entries = {}
            self.hotkey_dialog = None
            dialog.destroy()

        body = tk.Frame(dialog, padx=14, pady=14)
        body.pack(fill='both', expand=True)

        tk.Label(
            body,
            text='每项支持多个快捷键，用逗号分隔，例如 Ctrl+Shift+S, Ctrl+Alt+S',
            anchor='w',
            justify='left'
        ).pack(fill='x', pady=(0, 10))

        for action in ('take_screenshot', 'toggle_main_window', 'toggle_todo'):
            row = tk.Frame(body)
            row.pack(fill='x', pady=4)

            tk.Label(row, text=self.HOTKEY_LABELS[action], width=14, anchor='w').pack(side='left')
            entry = tk.Entry(row, font=('Arial', 10))
            entry.insert(0, ', '.join(current_hotkeys[action]))
            entry.pack(side='left', fill='x', expand=True)
            self.hotkey_entries[action] = entry

        btn_row = tk.Frame(body)
        btn_row.pack(fill='x', pady=(14, 0))

        def fill_defaults():
            for action, entry in self.hotkey_entries.items():
                entry.delete(0, 'end')
                entry.insert(0, ', '.join(self.DEFAULT_HOTKEYS[action]))

        def save_settings():
            try:
                hotkey_config = {}
                for action, entry in self.hotkey_entries.items():
                    hotkey_config[action] = self.parse_hotkey_display_list(entry.get())
                self.apply_hotkey_settings(hotkey_config)
            except ValueError as exc:
                messagebox.showerror('快捷键设置', str(exc), parent=dialog)
                return

            messagebox.showinfo('快捷键设置', '快捷键已更新', parent=dialog)
            close_dialog()

        tk.Button(btn_row, text='恢复默认', command=fill_defaults).pack(side='left')
        tk.Button(btn_row, text='取消', command=close_dialog).pack(side='right')
        tk.Button(btn_row, text='保存', command=save_settings).pack(side='right', padx=(0, 8))

        dialog.protocol('WM_DELETE_WINDOW', close_dialog)
        dialog.bind('<Escape>', lambda e: close_dialog())

        first_entry = self.hotkey_entries.get('take_screenshot')
        if first_entry is not None:
            first_entry.focus_set()

    def post_ui_task(self, callback, *args, **kwargs):
        '''从非 UI 线程投递任务到 Tk 主线程'''
        self.ui_queue.put((callback, args, kwargs))

    def post_ui_action(self, action_name):
        '''按名称投递应用动作'''
        action = getattr(self, action_name, None)
        if callable(action):
            self.post_ui_task(action)

    def process_ui_queue(self):
        '''在 Tk 主线程中处理待执行任务'''
        while True:
            try:
                callback, args, kwargs = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f'UI任务执行失败: {e}')

        if self.root.winfo_exists():
            self.root.after(50, self.process_ui_queue)

    def take_screenshot(self):
        '''执行截图并打开标注器'''
        # 隐藏主窗口
        self._restore_window_after_screenshot = self.window.winfo_viewable()
        if self._restore_window_after_screenshot:
            self.window.withdraw()

        # 延时确保窗口隐藏
        self.root.after(200, self._do_screenshot)

    def _do_screenshot(self):
        '''执行实际截图操作'''
        try:
            # 传入 root 窗口作为 parent，确保截图窗口正确关闭
            from utils.screenshot import Screenshot
            screenshot_obj = Screenshot()
            # 创建带 parent 的 RegionSelector
            from utils.screenshot import RegionSelector
            selector = RegionSelector(self.root)
            image = selector.get_region()
            if image:
                temp_path = screenshot_obj.create_temp_screenshot(image)
                save_path = screenshot_obj.build_output_path()
                if temp_path:
                    # 仅在用户点保存后才写入正式目录和历史
                    open_annotator(
                        temp_path,
                        parent=self.root,
                        on_save_callback=self.on_annotation_saved,
                        save_path=save_path,
                        cleanup_source=True
                    )
        except Exception as e:
            print(f'截图失败: {e}')
            messagebox.showerror('截图失败', f'截图功能执行失败:\n{e}')

        # 恢复主窗口显示（检查窗口是否还存在）
        try:
            if self._restore_window_after_screenshot and self.window.winfo_exists():
                self.window.deiconify()
        except:
            pass

    def toggle_main_window(self):
        '''切换主窗口显示/隐藏'''
        self.main_window.toggle_visibility()

    def toggle_todo(self):
        '''切换Todo备忘录显示/隐藏'''
        # 在主线程中执行
        if self.todo_view is None:
            # 首次创建Todo视图
            self.todo_view = TodoView(self.window, on_close_callback=self.on_todo_close)
        else:
            # 切换显示状态
            self.todo_view.toggle()

    def on_todo_close(self):
        '''Todo关闭时的回调'''
        self.todo_view = None

    def show_screenshots(self):
        '''显示截图历史窗口'''
        if self.thumbnails_window is None or not self.thumbnails_window.window.winfo_exists():
            self.thumbnails_window = Thumbnails(
                self.window,
                on_select_callback=self.on_screenshot_select,
                on_close_callback=self.on_screenshots_close
            )
        else:
            self.thumbnails_window.refresh()
            self.thumbnails_window.window.deiconify()
            self.thumbnails_window.window.lift()
            self.thumbnails_window.window.focus_force()

    def on_screenshot_select(self, path):
        '''截图选中回调'''
        # 使用系统图片查看器打开
        import subprocess
        try:
            subprocess.Popen(['cmd', '/c', 'start', '', path])
        except Exception as e:
            print(f'打开图片失败: {e}')

    def on_annotation_saved(self, path):
        '''截图保存后的回调，刷新截图历史'''
        from utils.screenshot import Screenshot
        Screenshot().register_screenshot(path)
        if self.thumbnails_window is not None and self.thumbnails_window.window.winfo_exists():
            self.thumbnails_window.refresh()

    def on_screenshots_close(self):
        '''截图历史关闭时的回调'''
        self.thumbnails_window = None

    def show_window(self):
        '''显示主窗口（供托盘调用）'''
        self.main_window.show_window()

    def hide_window(self):
        '''隐藏主窗口（供托盘调用）'''
        self.main_window.hide_window()

    def quit_app(self):
        '''退出应用程序（供托盘调用）'''
        self.stop_hotkeys()
        self.main_window.quit_app()

    def run(self):
        '''运行应用程序'''
        # 启动系统托盘
        self.tray.run()

        # 运行主窗口
        self.main_window.run()


def main():
    '''程序入口'''
    app = MottoApp()
    app.run()


if __name__ == '__main__':
    main()
