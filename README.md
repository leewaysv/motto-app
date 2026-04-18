# motto-app

一个基于 Tkinter 的 Windows 桌面小工具，提供常驻座右铭视图、备忘录和截图标注能力，适合个人日常记录与快速截屏。

## 功能

- 桌面悬浮座右铭窗口，支持拖拽、隐藏和编辑
- 备忘录窗口，支持新增、完成和删除待办事项
- 区域截图与截图编辑
- 截图历史缩略图查看
- 系统托盘菜单
- 自定义全局快捷键
- 开机自启动切换

## 环境

- Windows 10 / 11
- Python 3.10 及以上

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 默认快捷键

- `Ctrl+Shift+S` / `Ctrl+Alt+S`：截图
- `Ctrl+Shift+M`：显示或隐藏主窗口
- `Ctrl+Shift+T`：打开或隐藏备忘录

快捷键也可以在托盘菜单中的“快捷键设置”里自行修改。

## 托盘功能

托盘菜单支持以下操作：

- 显示 / 隐藏主窗口
- 发起截图
- 打开截图历史
- 打开备忘录
- 修改快捷键
- 开启 / 关闭开机启动
- 退出应用

## 配置与数据

- `config/config.json`：默认窗口配置和快捷键配置
- `data/todo.json`：备忘录数据
- `data/screenshots.json`：截图历史记录

仓库中的数据文件保持为公开仓库可用的安全默认值；运行后产生的个人数据会写回这些文件。

## 说明

这是一个 Windows 桌面个人项目，界面基于 Tkinter，依赖 `Pillow`、`pystray`、`pynput` 等库完成截图、托盘和全局快捷键能力。

