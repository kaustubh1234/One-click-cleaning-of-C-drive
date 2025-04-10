#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 安全高效地清理C盘不必要的文件
"""

import sys
import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config import APP_NAME, VERSION
from cleaner_logic import CleanerLogic
from backup_manager import BackupManagerWindow

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='cleaner.log'
)
logger = logging.getLogger('CCleaner')

class CleanerApp(tk.Tk):
    """基于tkinter的C盘清理工具主应用程序"""

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("800x600")
        self.minsize(800, 600)

        self.cleaner = CleanerLogic()
        self.scan_results = {}
        self.selected_items = []

        self.create_widgets()
        self.update_disk_info()

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 系统信息区域
        info_frame = ttk.LabelFrame(main_frame, text="系统信息", padding="5")
        info_frame.pack(fill=tk.X, pady=5)

        self.disk_info_label = ttk.Label(info_frame, text="C盘使用情况: 正在加载...")
        self.disk_info_label.pack(anchor=tk.W)

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.scan_button = ttk.Button(button_frame, text="扫描系统", command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        self.clean_all_button = ttk.Button(button_frame, text="一键清理", command=self.start_clean_all)
        self.clean_all_button.pack(side=tk.LEFT, padx=5)

        self.clean_button = ttk.Button(button_frame, text="清理选中项", command=self.start_clean, state=tk.DISABLED)
        self.clean_button.pack(side=tk.LEFT, padx=5)

        self.select_all_button = ttk.Button(button_frame, text="全选", command=self.select_all_items, state=tk.DISABLED)
        self.select_all_button.pack(side=tk.LEFT, padx=5)

        self.deselect_all_button = ttk.Button(button_frame, text="取消全选", command=self.deselect_all_items, state=tk.DISABLED)
        self.deselect_all_button.pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=5)

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.pack_forget()  # 初始隐藏

        self.status_label = ttk.Label(self.progress_frame, text="")
        self.status_label.pack(anchor=tk.W)

        # 结果区域
        result_frame = ttk.LabelFrame(main_frame, text="扫描结果", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 创建Treeview用于显示结果
        columns = ("name", "size", "path")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="tree headings")

        # 设置列标题
        self.result_tree.heading("name", text="项目")
        self.result_tree.heading("size", text="大小")
        self.result_tree.heading("path", text="路径")

        # 设置列宽
        self.result_tree.column("name", width=200)
        self.result_tree.column("size", width=100)
        self.result_tree.column("path", width=400)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)

        # 放置Treeview和滚动条
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 安全选项区域
        safety_frame = ttk.LabelFrame(main_frame, text="安全选项", padding="5")
        safety_frame.pack(fill=tk.X, pady=5)

        # 模拟模式选项
        simulate_frame = ttk.Frame(safety_frame)
        simulate_frame.pack(fill=tk.X, pady=2)

        self.simulate_var = tk.BooleanVar(value=False)  # 默认关闭模拟模式
        self.simulate_check = ttk.Checkbutton(simulate_frame, text="模拟模式 (不实际删除文件)",
                                             variable=self.simulate_var)
        self.simulate_check.pack(side=tk.LEFT)

        # 备份选项
        backup_frame = ttk.Frame(safety_frame)
        backup_frame.pack(fill=tk.X, pady=2)

        self.backup_var = tk.BooleanVar(value=True)
        self.backup_check = ttk.Checkbutton(backup_frame, text="删除前备份文件",
                                           variable=self.backup_var)
        self.backup_check.pack(side=tk.LEFT)

        self.backup_manager_button = ttk.Button(backup_frame, text="备份管理", command=self.open_backup_manager)
        self.backup_manager_button.pack(side=tk.LEFT, padx=10)

        # 备份目录选项
        backup_dir_frame = ttk.Frame(safety_frame)
        backup_dir_frame.pack(fill=tk.X, pady=2)

        ttk.Label(backup_dir_frame, text="备份目录:").pack(side=tk.LEFT, padx=5)

        self.backup_dir_var = tk.StringVar(value=self.cleaner.backup_dir)
        backup_dir_entry = ttk.Entry(backup_dir_frame, textvariable=self.backup_dir_var, width=40)
        backup_dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_button = ttk.Button(backup_dir_frame, text="浏览...", command=self.browse_backup_dir)
        browse_button.pack(side=tk.LEFT, padx=5)

    def update_disk_info(self):
        """更新磁盘信息"""
        disk_info = self.cleaner.get_disk_info()
        self.disk_info_label.config(
            text=f"C盘总空间: {disk_info['total']:.2f} GB | "
                 f"已用空间: {disk_info['used']:.2f} GB ({disk_info['percent']}%) | "
                 f"可用空间: {disk_info['free']:.2f} GB"
        )

    def start_scan(self):
        """开始扫描系统"""
        self.scan_button.config(state=tk.DISABLED)
        self.clean_button.config(state=tk.DISABLED)
        self.select_all_button.config(state=tk.DISABLED)
        self.deselect_all_button.config(state=tk.DISABLED)
        self.result_tree.delete(*self.result_tree.get_children())
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()
        self.status_label.config(text="正在扫描系统，请稍候...")

        # 使用after方法在后台执行扫描
        self.after(100, self.perform_scan)

    def perform_scan(self):
        """执行扫描操作"""
        try:
            self.scan_results = self.cleaner.scan_system()
            self.after(100, self.on_scan_finished)
        except Exception as e:
            logger.error(f"扫描过程中出错: {e}")
            messagebox.showerror("扫描错误", f"扫描过程中出错: {e}")
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.scan_button.config(state=tk.NORMAL)

    def on_scan_finished(self):
        """扫描完成后的处理"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_button.config(state=tk.NORMAL)

        if not any(self.scan_results.values()):
            self.status_label.config(text="扫描完成，未发现可清理项目")
            return

        # 计算总大小
        total_size = sum(item['size'] for category in self.scan_results.values() for item in category)
        self.status_label.config(text=f"扫描完成，发现可释放空间: {self.format_size(total_size)}")

        # 填充结果树
        self.populate_results_tree()
        self.clean_button.config(state=tk.NORMAL)
        self.select_all_button.config(state=tk.NORMAL)
        self.deselect_all_button.config(state=tk.NORMAL)

        # 更新磁盘信息
        self.update_disk_info()

    def populate_results_tree(self):
        """填充结果树"""
        categories = {
            # 基本清理
            'temp': "临时文件",
            'recycle': "回收站",
            'cache': "浏览器缓存",
            'logs': "系统日志",
            'updates': "Windows更新缓存",
            'thumbnails': "缩略图缓存",

            # 扩展清理
            'prefetch': "预读取文件",
            'old_windows': "旧Windows文件",
            'error_reports': "错误报告",
            'service_packs': "服务包备份",
            'memory_dumps': "内存转储文件",
            'font_cache': "字体缓存",
            'disk_cleanup': "磁盘清理备份",

            # 新增安全清理项
            'app_cache': "应用程序缓存",
            'media_cache': "媒体播放器缓存",
            'search_index': "搜索索引临时文件",
            'backup_temp': "备份临时文件",
            'update_temp': "更新临时文件",
            'driver_backup': "驱动备份",
            'app_crash': "应用程序崩溃转储",
            'app_logs': "应用程序日志",
            'recent_items': "最近使用的文件列表",
            'notification': "Windows通知缓存",
            'dns_cache': "DNS缓存",
            'network_cache': "网络缓存",
            'printer_temp': "打印机临时文件",
            'device_temp': "设备临时文件",
            'windows_defender': "Windows Defender缓存",
            'store_cache': "Windows Store缓存",
            'onedrive_cache': "OneDrive缓存",

            # 新增用户请求的清理项
            'downloads': "下载文件夹(立即清理)",
            'installer_cache': "安装程序缓存(30天前)",
            'delivery_opt': "Windows传递优化缓存(立即清理)",

            # 大文件扫描
            'large_files': "大文件 (>100MB)"
        }

        for category, items in self.scan_results.items():
            if not items:
                continue

            # 计算类别总大小
            category_size = sum(item['size'] for item in items)
            category_name = categories.get(category, category)

            # 添加类别节点
            category_id = self.result_tree.insert(
                "", "end", text=category_name,
                values=(category_name, self.format_size(category_size), "")
            )

            # 添加文件节点
            for item in items:
                file_name = os.path.basename(item['path'])

                # 大文件显示更多信息
                if category == 'large_files' and 'modified' in item and 'extension' in item:
                    # 对于大文件，显示文件名、大小、修改时间和文件类型
                    file_info = f"{file_name} [修改时间: {item['modified']}] [类型: {item['extension']}]"
                    self.result_tree.insert(
                        category_id, "end", text=file_name,
                        values=(file_info, self.format_size(item['size']), item['path']),
                        tags=("item",)
                    )
                else:
                    # 对于普通文件，只显示文件名和大小
                    self.result_tree.insert(
                        category_id, "end", text=file_name,
                        values=(file_name, self.format_size(item['size']), item['path']),
                        tags=("item",)
                    )

        # 展开所有节点
        for item_id in self.result_tree.get_children():
            self.result_tree.item(item_id, open=True)

    def start_clean(self):
        """开始清理选中的项目"""
        # 获取选中的项目
        selected_ids = self.result_tree.selection()
        if not selected_ids:
            messagebox.showinfo("提示", "请先选择要清理的项目")
            return

        # 收集选中的项目数据
        self.selected_items = []
        for item_id in selected_ids:
            # 检查是否是文件项目（不是类别）
            parent_id = self.result_tree.parent(item_id)
            if parent_id:  # 如果有父节点，说明是文件项目
                path = self.result_tree.item(item_id, "values")[2]
                # 在scan_results中查找对应的项目
                for category in self.scan_results.values():
                    for item in category:
                        if item['path'] == path:
                            self.selected_items.append(item)
                            break

        if not self.selected_items:
            messagebox.showinfo("提示", "请选择具体的文件或目录进行清理")
            return

        # 确认对话框
        total_size = sum(item['size'] for item in self.selected_items)
        if self.simulate_var.get():
            message = f"您选择了模拟模式，将会模拟清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)}。"
        else:
            message = f"您确定要清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)} 吗？\n此操作无法撤销！"

        if not messagebox.askyesno("确认清理", message):
            return

        # 设置清理选项
        self.cleaner.set_options({
            'simulate': self.simulate_var.get(),
            'backup': self.backup_var.get(),
            'backup_dir': self.backup_dir_var.get()
        })

        # 开始清理
        self.scan_button.config(state=tk.DISABLED)
        self.clean_button.config(state=tk.DISABLED)
        self.select_all_button.config(state=tk.DISABLED)
        self.deselect_all_button.config(state=tk.DISABLED)
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()
        self.status_label.config(text="正在清理文件，请稍候...")

        # 使用after方法在后台执行清理
        self.after(100, self.perform_clean)

    def perform_clean(self):
        """执行清理操作"""
        try:
            results = self.cleaner.clean_selected(self.selected_items)
            self.after(100, lambda: self.on_clean_finished(results))
        except Exception as e:
            logger.error(f"清理过程中出错: {e}")
            messagebox.showerror("清理错误", f"清理过程中出错: {e}")
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.scan_button.config(state=tk.NORMAL)
            self.clean_button.config(state=tk.NORMAL)
            self.clean_all_button.config(state=tk.NORMAL)

    def perform_clean_all(self):
        """执行一键清理操作"""
        try:
            # 先扫描系统
            self.scan_results = self.cleaner.scan_system()

            # 准备所有项目的列表
            all_items = []
            for category_items in self.scan_results.values():
                all_items.extend(category_items)

            # 如果没有可清理项目
            if not all_items:
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
                self.scan_button.config(state=tk.NORMAL)
                self.clean_all_button.config(state=tk.NORMAL)
                self.status_label.config(text="扫描完成，未发现可清理项目")
                return

            # 显示清理进度
            total_size = sum(item['size'] for item in all_items)
            self.status_label.config(text=f"正在清理 {len(all_items)} 个项目，总计 {self.format_size(total_size)}...")

            # 执行清理
            results = self.cleaner.clean_selected(all_items)
            self.after(100, lambda: self.on_clean_all_finished(results))
        except Exception as e:
            logger.error(f"一键清理过程中出错: {e}")
            messagebox.showerror("清理错误", f"一键清理过程中出错: {e}")
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.scan_button.config(state=tk.NORMAL)
            self.clean_all_button.config(state=tk.NORMAL)

    def on_clean_finished(self, results):
        """清理完成后的处理"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_button.config(state=tk.NORMAL)
        self.clean_all_button.config(state=tk.NORMAL)

        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])

        if self.simulate_var.get():
            message = f"模拟清理完成，可释放空间: {self.format_size(freed_space)}"
        else:
            message = f"清理完成，已释放空间: {self.format_size(freed_space)}"

        if errors:
            message += f"，{len(errors)} 个错误"

        self.status_label.config(text=message)

        # 如果有错误，显示错误日志
        if errors:
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            messagebox.showwarning("清理错误", f"清理过程中发生 {len(errors)} 个错误\n\n{error_details}")

        # 更新磁盘信息
        self.update_disk_info()

        # 重新扫描
        self.start_scan()

    def on_clean_all_finished(self, results):
        """一键清理完成后的处理"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.scan_button.config(state=tk.NORMAL)
        self.clean_all_button.config(state=tk.NORMAL)

        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])

        if self.simulate_var.get():
            message = f"模拟清理完成，可释放空间: {self.format_size(freed_space)}"
        else:
            message = f"一键清理完成，已释放空间: {self.format_size(freed_space)}"

        if errors:
            message += f"，{len(errors)} 个错误"

        self.status_label.config(text=message)

        # 如果有错误，显示错误日志
        if errors:
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            messagebox.showwarning("清理错误", f"清理过程中发生 {len(errors)} 个错误\n\n{error_details}")

        # 显示清理结果
        messagebox.showinfo("清理完成", f"一键清理完成\n\n已释放空间: {self.format_size(freed_space)}\n错误数量: {len(errors)}")

        # 更新磁盘信息
        self.update_disk_info()

        # 重新扫描
        self.start_scan()

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

    def browse_backup_dir(self):
        """浏览选择备份目录"""
        backup_dir = filedialog.askdirectory(
            title="选择备份目录",
            initialdir=self.cleaner.backup_dir
        )

        if backup_dir:
            self.backup_dir_var.set(backup_dir)
            # 更新清理器的备份目录
            self.cleaner.set_options({'backup_dir': backup_dir})

    def open_backup_manager(self):
        """打开备份管理窗口"""
        BackupManagerWindow(self, self.cleaner)

    def select_all_items(self):
        """全选所有项目"""
        # 选中所有类别
        for category_id in self.result_tree.get_children():
            # 设置类别项为选中状态
            self.result_tree.item(category_id, open=True)  # 展开类别

            # 选中该类别下的所有文件
            for item_id in self.result_tree.get_children(category_id):
                self.result_tree.selection_add(item_id)

        # 更新清理按钮状态
        self.clean_button.config(state=tk.NORMAL)

    def deselect_all_items(self):
        """取消全选"""
        # 取消选中所有项目
        self.result_tree.selection_remove(self.result_tree.selection())

        # 更新清理按钮状态
        self.clean_button.config(state=tk.DISABLED)

    def start_clean_all(self):
        """一键清理所有项目"""
        # 确认对话框
        if not messagebox.askyesno("确认清理", "一键清理将清理所有可清理项目，确定要继续吗？"):
            return

        # 先扫描系统
        self.scan_button.config(state=tk.DISABLED)
        self.clean_all_button.config(state=tk.DISABLED)
        self.clean_button.config(state=tk.DISABLED)
        self.select_all_button.config(state=tk.DISABLED)
        self.deselect_all_button.config(state=tk.DISABLED)
        self.result_tree.delete(*self.result_tree.get_children())
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()
        self.status_label.config(text="正在扫描系统，请稍候...")

        # 设置清理选项
        self.cleaner.set_options({
            'simulate': self.simulate_var.get(),
            'backup': self.backup_var.get(),
            'backup_dir': self.backup_dir_var.get()
        })

        # 使用after方法在后台执行扫描和清理
        self.after(100, self.perform_clean_all)

def main():
    """应用程序入口点"""
    logger.info(f"启动 {APP_NAME} v{VERSION}")

    app = CleanerApp()
    app.mainloop()

    logger.info(f"{APP_NAME} 已退出")

if __name__ == "__main__":
    main()
