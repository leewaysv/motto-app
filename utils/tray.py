from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw


class SystemTray:
    '''系统托盘图标管理类'''

    def __init__(self, app):
        '''初始化系统托盘

        Args:
            app: 主应用实例
        '''
        self.app = app
        self.icon = None
        self.create_icon()

    def create_icon(self):
        '''创建托盘图标'''
        # 创建图标图像
        width = 64
        height = 64

        # 创建图像
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)

        # 绘制字母 'M' 代表 motto
        draw.rectangle([10, 10, 54, 54], fill='#4a90d9', outline='#4a90d9')
        draw.text((18, 15), 'M', fill='white', font=None)

        # 创建图标
        self.icon = pystray.Icon(
            'motto',
            image,
            'motto - 桌面座右铭',
            self.create_menu()
        )

    def create_menu(self):
        '''创建托盘菜单'''
        # 获取开机启动状态
        autostart_enabled = self.is_autostart_enabled()
        autostart_text = '关闭开机启动' if autostart_enabled else '开启开机启动'

        menu = pystray.Menu(
            pystray.MenuItem('显示', self._wrap_action('show_window')),
            pystray.MenuItem('隐藏', self._wrap_action('hide_window')),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('截图', self._wrap_action('take_screenshot')),
            pystray.MenuItem('截图历史', self._wrap_action('show_screenshots')),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('备忘录', self._wrap_action('show_todo')),
            pystray.MenuItem('快捷键设置', self._wrap_action('show_hotkey_settings')),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(autostart_text, self._wrap_action('toggle_autostart')),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出', self._wrap_action('quit_app'))
        )
        return menu

    def _wrap_action(self, method_name):
        '''包装方法，使其在主线程中执行'''
        def wrapper(icon=None, item=None):
            self._execute_action(method_name)
        return wrapper

    def _execute_action(self, method_name):
        '''执行指定的方法'''
        try:
            if hasattr(self.app, 'post_ui_task'):
                self.app.post_ui_task(self._do_action, method_name)
            else:
                self._do_action(method_name)
        except Exception as e:
            print(f'执行托盘操作失败: {e}')

    def _do_action(self, method_name):
        '''实际执行操作的方法'''
        try:
            if method_name == 'show_window':
                self.app.show_window()
            elif method_name == 'hide_window':
                self.app.hide_window()
            elif method_name == 'take_screenshot':
                self.app.take_screenshot()
            elif method_name == 'show_screenshots':
                self.app.show_screenshots()
            elif method_name == 'show_todo':
                self.app.toggle_todo()
            elif method_name == 'show_hotkey_settings':
                self.app.show_hotkey_settings()
            elif method_name == 'toggle_autostart':
                self._toggle_autostart()
            elif method_name == 'quit_app':
                self.app.quit_app()
                self.icon.stop()
        except Exception as e:
            print(f'执行托盘操作失败: {e}')

    def _toggle_autostart(self):
        '''切换开机自启动'''
        from utils.autostart import enable_autostart, disable_autostart, is_autostart_enabled

        if is_autostart_enabled():
            disable_autostart()
            messagebox.showinfo('提示', '已取消开机自启动')
        else:
            enable_autostart()
            messagebox.showinfo('提示', '已启用开机自启动')

        # 更新菜单
        self.icon.menu = self.create_menu()

    def is_autostart_enabled(self):
        '''检查开机自启动状态'''
        from utils.autostart import is_autostart_enabled
        return is_autostart_enabled()

    def run(self):
        '''运行托盘图标'''
        # 在单独的线程中运行
        import threading
        thread = threading.Thread(target=self.icon.run, daemon=True)
        thread.start()

    def stop(self):
        '''停止托盘图标'''
        if self.icon:
            self.icon.stop()


def create_tray(app):
    '''创建系统托盘的工厂函数'''
    return SystemTray(app)


if __name__ == '__main__':
    # 测试
    print('系统托盘模块测试')
    print('此模块需要主程序配合使用')
