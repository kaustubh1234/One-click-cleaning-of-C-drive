#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 备份管理界面
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from cleaner_logic import CleanerLogic

class BackupManagerWindow(tk.Toplevel):
    """备份管理窗口"""
    
    def __init__(self, parent, cleaner):
        super().__init__(parent)
        self.title("备份管理")
        self.geometry("800x600")
        self.minsize(800, 600)
        self.transient(parent)  # 设置为父窗口的临时窗口
        self.grab_set()  # 模态窗口
        
        self.parent = parent
        self.cleaner = cleaner
        
        self.create_widgets()
        self.refresh_backup_list()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 备份信息区域
        info_frame = ttk.LabelFrame(main_frame, text="备份信息", padding="5")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.backup_dir_label = ttk.Label(info_frame, text="备份目录: ")
        self.backup_dir_label.pack(anchor=tk.W)
        
        self.backup_count_label = ttk.Label(info_frame, text="备份数量: ")
        self.backup_count_label.pack(anchor=tk.W)
        
        self.backup_size_label = ttk.Label(info_frame, text="备份总大小: ")
        self.backup_size_label.pack(anchor=tk.W)
        
        # 备份设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="备份设置", padding="5")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 备份目录设置
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dir_frame, text="备份目录:").pack(side=tk.LEFT, padx=5)
        self.backup_dir_entry = ttk.Entry(dir_frame, width=50)
        self.backup_dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_button = ttk.Button(dir_frame, text="浏览...", command=self.browse_backup_dir)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.apply_button = ttk.Button(dir_frame, text="应用", command=self.apply_backup_dir)
        self.apply_button.pack(side=tk.LEFT, padx=5)
        
        # 备份限制设置
        limit_frame = ttk.Frame(settings_frame)
        limit_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(limit_frame, text="最大备份数量:").pack(side=tk.LEFT, padx=5)
        self.max_backups_var = tk.StringVar(value="5")
        self.max_backups_entry = ttk.Entry(limit_frame, width=5, textvariable=self.max_backups_var)
        self.max_backups_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(limit_frame, text="最大备份大小(MB):").pack(side=tk.LEFT, padx=5)
        self.max_backup_size_var = tk.StringVar(value="1024")
        self.max_backup_size_entry = ttk.Entry(limit_frame, width=10, textvariable=self.max_backup_size_var)
        self.max_backup_size_entry.pack(side=tk.LEFT, padx=5)
        
        self.apply_limits_button = ttk.Button(limit_frame, text="应用限制", command=self.apply_backup_limits)
        self.apply_limits_button.pack(side=tk.LEFT, padx=5)
        
        # 备份列表区域
        list_frame = ttk.LabelFrame(main_frame, text="备份列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建Treeview用于显示备份列表
        columns = ("name", "time", "size")
        self.backup_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.backup_tree.heading("name", text="备份名称")
        self.backup_tree.heading("time", text="备份时间")
        self.backup_tree.heading("size", text="大小")
        
        # 设置列宽
        self.backup_tree.column("name", width=200)
        self.backup_tree.column("time", width=150)
        self.backup_tree.column("size", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.backup_tree.yview)
        self.backup_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置Treeview和滚动条
        self.backup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 备份操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.refresh_button = ttk.Button(button_frame, text="刷新", command=self.refresh_backup_list)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        self.restore_button = ttk.Button(button_frame, text="恢复选中的备份", command=self.restore_backup)
        self.restore_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_button = ttk.Button(button_frame, text="删除选中的备份", command=self.delete_backup)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        self.clean_button = ttk.Button(button_frame, text="清理旧备份", command=self.clean_old_backups)
        self.clean_button.pack(side=tk.LEFT, padx=5)
        
        self.close_button = ttk.Button(button_frame, text="关闭", command=self.destroy)
        self.close_button.pack(side=tk.RIGHT, padx=5)
    
    def refresh_backup_list(self):
        """刷新备份列表"""
        # 清空列表
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)
        
        # 获取备份信息
        backup_info = self.cleaner.get_backup_info()
        
        # 更新备份信息标签
        self.backup_dir_label.config(text=f"备份目录: {backup_info['backup_dir']}")
        self.backup_count_label.config(text=f"备份数量: {backup_info['backup_count']}")
        self.backup_size_label.config(text=f"备份总大小: {self.format_size(backup_info['total_size'])}")
        
        # 更新备份目录输入框
        self.backup_dir_entry.delete(0, tk.END)
        self.backup_dir_entry.insert(0, backup_info['backup_dir'])
        
        # 更新备份限制输入框
        self.max_backups_var.set(str(self.cleaner.max_backups))
        self.max_backup_size_var.set(str(int(self.cleaner.max_backup_size / (1024 * 1024))))  # 转换为MB
        
        # 填充备份列表
        for backup in backup_info['backups']:
            self.backup_tree.insert(
                "", "end",
                values=(backup['name'], backup['time'], self.format_size(backup['size'])),
                tags=(backup['path'],)
            )
    
    def browse_backup_dir(self):
        """浏览选择备份目录"""
        backup_dir = filedialog.askdirectory(
            title="选择备份目录",
            initialdir=self.cleaner.backup_dir
        )
        
        if backup_dir:
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, backup_dir)
    
    def apply_backup_dir(self):
        """应用备份目录设置"""
        new_backup_dir = self.backup_dir_entry.get().strip()
        
        if not new_backup_dir:
            messagebox.showerror("错误", "备份目录不能为空")
            return
        
        try:
            # 确保目录存在
            os.makedirs(new_backup_dir, exist_ok=True)
            
            # 设置新的备份目录
            self.cleaner.set_options({'backup_dir': new_backup_dir})
            
            messagebox.showinfo("成功", f"备份目录已设置为: {new_backup_dir}")
            self.refresh_backup_list()
        except Exception as e:
            messagebox.showerror("错误", f"设置备份目录失败: {e}")
    
    def apply_backup_limits(self):
        """应用备份限制设置"""
        try:
            max_backups = int(self.max_backups_var.get())
            max_backup_size_mb = int(self.max_backup_size_var.get())
            
            if max_backups <= 0:
                messagebox.showerror("错误", "最大备份数量必须大于0")
                return
            
            if max_backup_size_mb <= 0:
                messagebox.showerror("错误", "最大备份大小必须大于0")
                return
            
            # 转换为字节
            max_backup_size = max_backup_size_mb * 1024 * 1024
            
            # 设置新的备份限制
            self.cleaner.set_options({
                'max_backups': max_backups,
                'max_backup_size': max_backup_size
            })
            
            messagebox.showinfo("成功", f"备份限制已设置为: 最多{max_backups}个备份，总大小不超过{max_backup_size_mb}MB")
            self.refresh_backup_list()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            messagebox.showerror("错误", f"设置备份限制失败: {e}")
    
    def restore_backup(self):
        """恢复选中的备份"""
        selected_items = self.backup_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要恢复的备份")
            return
        
        # 获取选中的备份路径
        selected_item = selected_items[0]  # 只处理第一个选中项
        backup_path = self.backup_tree.item(selected_item, "tags")[0]
        
        # 确认对话框
        if not messagebox.askyesno("确认恢复", "恢复备份将覆盖当前文件，确定要继续吗？"):
            return
        
        # 恢复备份
        if self.cleaner.restore_backup(backup_path):
            messagebox.showinfo("成功", "备份恢复成功")
        else:
            messagebox.showerror("错误", "备份恢复失败")
    
    def delete_backup(self):
        """删除选中的备份"""
        selected_items = self.backup_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要删除的备份")
            return
        
        # 获取选中的备份路径
        selected_item = selected_items[0]  # 只处理第一个选中项
        backup_path = self.backup_tree.item(selected_item, "tags")[0]
        
        # 确认对话框
        if not messagebox.askyesno("确认删除", "确定要删除选中的备份吗？此操作无法撤销！"):
            return
        
        # 删除备份
        try:
            import shutil
            shutil.rmtree(backup_path)
            messagebox.showinfo("成功", "备份删除成功")
            self.refresh_backup_list()
        except Exception as e:
            messagebox.showerror("错误", f"删除备份失败: {e}")
    
    def clean_old_backups(self):
        """清理旧备份"""
        # 确认对话框
        if not messagebox.askyesno("确认清理", "确定要清理旧备份吗？此操作将根据设置的限制删除最旧的备份！"):
            return
        
        # 清理旧备份
        if self.cleaner.clean_old_backups():
            messagebox.showinfo("成功", "旧备份清理成功")
            self.refresh_backup_list()
        else:
            messagebox.showerror("错误", "旧备份清理失败")
    
    @staticmethod
    def format_size(size_bytes):
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"
