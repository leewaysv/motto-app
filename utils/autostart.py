import os
import sys
import winreg


def enable_autostart(app_name='motto', app_path=None):
    '''启用开机自启动

    Args:
        app_name: 注册表中的程序名称
        app_path: 程序路径，如果为None则使用当前程序路径
    '''
    if app_path is None:
        app_path = sys.executable

    try:
        # 打开注册表项
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            0,
            winreg.KEY_SET_VALUE
        )

        # 设置值
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'\"{app_path}\"')
        winreg.CloseKey(key)

        return True
    except Exception as e:
        print(f'设置开机自启动失败: {e}')
        return False


def disable_autostart(app_name='motto'):
    '''禁用开机自启动

    Args:
        app_name: 注册表中的程序名称
    '''
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            0,
            winreg.KEY_SET_VALUE
        )

        # 删除值
        try:
            winreg.DeleteValue(key, app_name)
        except FileNotFoundError:
            pass  # 键不存在

        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f'取消开机自启动失败: {e}')
        return False


def is_autostart_enabled(app_name='motto'):
    '''检查是否已启用开机自启动

    Args:
        app_name: 注册表中的程序名称
    Returns:
        bool: 是否启用
    '''
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            0,
            winreg.KEY_READ
        )

        try:
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False

    except Exception as e:
        return False


if __name__ == '__main__':
    # 测试
    print(f'当前开机自启动状态: {is_autostart_enabled()}')

    if is_autostart_enabled():
        print('正在取消开机自启动...')
        disable_autostart()
        print('已取消')
    else:
        print('正在启用开机自启动...')
        enable_autostart()
        print('已启用')

    print(f'当前开机自启动状态: {is_autostart_enabled()}')