import tkinter as tk
import json
import os


class TodoView:
    '''Todo备忘录视图类'''

    def __init__(self, parent, on_close_callback=None):
        '''初始化Todo视图

        Args:
            parent: 父窗口
            on_close_callback: 关闭时的回调函数
        '''
        self.parent = parent
        self.on_close_callback = on_close_callback

        # 数据文件路径
        self.data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'todo.json')
        self.todos = self.load_todos()

        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title('备忘录')
        self.window.geometry('350x450')
        self.window.attributes('-topmost', True)
        self.window.minsize(280, 320)

        # 创建自定义标题栏
        self.create_title_bar()

        # 创建Todo列表
        self.create_todo_list()

        # 创建添加输入框
        self.create_input_area()

        # 绑定关闭事件
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.bind('<Escape>', lambda e: self.close())

        self.focus_input()

    def create_title_bar(self):
        '''创建自定义标题栏'''
        title_frame = tk.Frame(self.window, bg='#4a90d9', height=30)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 标题文字
        title_label = tk.Label(title_frame, text='备忘录', bg='#4a90d9', fg='white', font=('Arial', 11, 'bold'))
        title_label.pack(side='left', padx=10)

        # 关闭按钮
        close_btn = tk.Button(title_frame, text='×', bg='#4a90d9', fg='white', bd=0,
                             font=('Arial', 12), command=self.close, width=2)
        close_btn.pack(side='right', padx=5)

    def create_todo_list(self):
        '''创建Todo列表显示区域'''
        list_frame = tk.Frame(self.window)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # 滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')

        # 列表框
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                   font=('Arial', 11), selectbackground='#4a90d9')
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

        # 绑定右键菜单和双击切换状态
        self.listbox.bind('<Button-3>', self.show_context_menu)
        self.listbox.bind('<Double-Button-1>', self.toggle_todo)

        self.refresh_list()

    def create_input_area(self):
        '''创建输入区域'''
        input_frame = tk.Frame(self.window)
        input_frame.pack(fill='x', padx=10, pady=(0, 10))

        # 输入框
        self.entry = tk.Entry(input_frame, font=('Arial', 11))
        self.entry.pack(side='left', fill='x', expand=True)

        # 添加按钮
        add_btn = tk.Button(input_frame, text='添加', command=self.add_todo,
                           bg='#4a90d9', fg='white', bd=0, font=('Arial', 10))
        add_btn.pack(side='right', padx=(5, 0))

        # 回车添加
        self.entry.bind('<Return>', lambda e: self.add_todo())

    def focus_input(self):
        '''让窗口和输入框拿到焦点'''
        self.window.deiconify()
        self.window.lift()
        self.window.after(50, self._focus_entry)

    def _focus_entry(self):
        '''聚焦输入框'''
        try:
            self.window.focus_force()
            self.entry.focus_set()
            self.entry.icursor('end')
        except tk.TclError:
            pass

    def load_todos(self):
        '''从文件加载Todo数据'''
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_todos(self):
        '''保存Todo数据到文件'''
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.todos, f, ensure_ascii=False, indent=2)

    def refresh_list(self):
        '''刷新列表显示'''
        self.listbox.delete(0, 'end')
        for i, todo in enumerate(self.todos):
            # 显示完成状态符号
            status = '✓' if todo.get('done', False) else '○'
            text = todo.get('text', '')
            display_text = f'{status} {text}'
            self.listbox.insert('end', display_text)

            # 已完成的显示为灰色
            if todo.get('done', False):
                self.listbox.itemconfig(i, fg='#999')

    def add_todo(self):
        '''添加新的Todo项'''
        text = self.entry.get().strip()
        if text:
            self.todos.append({'text': text, 'done': False})
            self.save_todos()
            self.refresh_list()
            self.entry.delete(0, 'end')

    def toggle_todo(self, event=None):
        '''切换Todo完成状态'''
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            self.todos[index]['done'] = not self.todos[index].get('done', False)
            self.save_todos()
            self.refresh_list()

    def delete_todo(self):
        '''删除选中的Todo项'''
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            del self.todos[index]
            self.save_todos()
            self.refresh_list()

    def show_context_menu(self, event):
        '''显示右键菜单'''
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label='完成/取消', command=self.toggle_todo)
        menu.add_command(label='删除', command=self.delete_todo)
        menu.post(event.x_root, event.y_root)

    def close(self):
        '''关闭窗口'''
        if self.on_close_callback:
            self.on_close_callback()
        self.window.destroy()

    def toggle(self):
        '''切换窗口显示/隐藏'''
        if self.window.winfo_viewable():
            self.window.withdraw()
        else:
            self.window.deiconify()
            self.focus_input()


def create_todo_view(parent, on_close_callback=None):
    '''创建Todo视图的工厂函数'''
    return TodoView(parent, on_close_callback)


if __name__ == '__main__':
    # 测试代码
    root = tk.Tk()
    root.title('测试')
    root.geometry('400x300')

    todo = TodoView(root)

    root.mainloop()
