import time
import tkinter
from tkinter import ttk
from tkinter.constants import END, W, E

import pandas


class GUI:
    def __init__(self,info_queue,handle_queue):
        self.info_queue = info_queue
        self.handle_queue = handle_queue

    def gui(self):

        self.top_window = tkinter.Tk()
        self.top_window.title('LeekControler')
        '''
        创建菜单
        '''
        menu = tkinter.Menu(self.top_window)
        menu.add_command(label='查看/修改参数',command=self.create_view_change_parm_window)
        self.top_window.config(menu=menu)

        # self.tree = ttk.Treeview(self.top_window, columns=('参数名', '值'), show="headings",
        #                     displaycolumns="#all",height=25)
        # self.tree.heading('参数名', text="参数名", anchor=W)
        # self.tree.heading('值', text="值", anchor=W)
        #
        # self.tree.pack()
        # tkinter.Button(self.top_window, text="修改参数值", command=self.create_parm_change_window).pack()
        # self.load_parm_data()
        self.top_window.mainloop()

    def create_view_change_parm_window(self):
        top = tkinter.Toplevel()
        top.title("查看参数")

        tree = ttk.Treeview(top, columns=('参数名', '值'), show="headings",
                             displaycolumns="#all", height=25)
        tree.heading('参数名', text="参数名", anchor=W)
        tree.heading('值', text="值", anchor=W)

        tree.pack()
        tkinter.Button(top, text="修改参数值", command=self.create_parm_change_window).pack()
        self.load_parm_data(top,tree)

    def create_parm_change_window(self):
        top = tkinter.Toplevel()
        top.title("修改参数值")

        # 设置标签信息
        label1 = tkinter.Label(top, text='参数名：')
        label1.grid(row=0, column=0)
        label2 = tkinter.Label(top, text='参数值：')
        label2.grid(row=1, column=0)

        # 创建输入框
        entry1 = tkinter.Entry(top)
        entry1.grid(row=0, column=1, padx=10, pady=5)
        entry2 = tkinter.Entry(top)
        entry2.grid(row=1, column=1, padx=10, pady=5)

        button1 = tkinter.Button(top, text='修改', command=lambda:self.send_handle_queue(entry1.get(), entry2.get())).grid(row=3, column=0,
                                                                    sticky=W, padx=30, pady=5)
        button2 = tkinter.Button(top, text='退出', command=top.destroy).grid(row=3, column=1,
                                                                        sticky=E, padx=30, pady=5)
    def send_handle_queue(self,parm_name,value):
        self.handle_queue.put({'parm_name':parm_name,'value':float(value)})
        return self

    def load_parm_data(self,top,tree):
        if(self.info_queue.empty()==False):
            parm_info_dict = self.info_queue.get()
            for item in tree.get_children():
                tree.delete(item)
            for key, value in parm_info_dict.items():
                tree.insert("", END, values=[key,value])
        tree.pack()
        top.after(1, self.load_parm_data,top,tree)

        return self
    # def