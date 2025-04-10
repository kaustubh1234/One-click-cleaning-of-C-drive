#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 用户界面
"""

import os
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QProgressBar, QCheckBox, 
                            QTreeWidget, QTreeWidgetItem, QMessageBox, 
                            QFileDialog, QGroupBox, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont

from cleaner_logic import CleanerLogic

class ScanThread(QThread):
    """扫描线程，避免UI冻结"""
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, cleaner):
        super().__init__()
        self.cleaner = cleaner
        
    def run(self):
        """运行扫描过程"""
        results = self.cleaner.scan_system()
        self.finished_signal.emit(results)


class CleanThread(QThread):
    """清理线程，避免UI冻结"""
    update_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, cleaner, selected_items):
        super().__init__()
        self.cleaner = cleaner
        self.selected_items = selected_items
        
    def run(self):
        """运行清理过程"""
        results = self.cleaner.clean_selected(self.selected_items, self.update_signal)
        self.finished_signal.emit(results)


class CleanerMainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.cleaner = CleanerLogic()
        self.scan_results = {}
        self.selected_items = []
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("C盘清理工具")
        self.setMinimumSize(800, 600)
        
        # 主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部信息区域
        info_group = QGroupBox("系统信息")
        info_layout = QVBoxLayout(info_group)
        
        self.disk_info_label = QLabel("C盘使用情况: 正在加载...")
        info_layout.addWidget(self.disk_info_label)
        
        # 扫描和清理按钮区域
        button_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("扫描系统")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.clicked.connect(self.start_scan)
        
        self.clean_button = QPushButton("清理选中项")
        self.clean_button.setMinimumHeight(40)
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self.start_clean)
        
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.clean_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("")
        
        # 结果树
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["项目", "大小", "路径"])
        self.results_tree.setColumnWidth(0, 250)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.itemChanged.connect(self.on_item_changed)
        
        # 安全选项
        safety_group = QGroupBox("安全选项")
        safety_layout = QVBoxLayout(safety_group)
        
        self.simulate_checkbox = QCheckBox("模拟模式 (不实际删除文件)")
        self.simulate_checkbox.setChecked(True)
        
        self.backup_checkbox = QCheckBox("删除前备份文件")
        self.backup_checkbox.setChecked(True)
        
        safety_layout.addWidget(self.simulate_checkbox)
        safety_layout.addWidget(self.backup_checkbox)
        
        # 添加所有组件到主布局
        main_layout.addWidget(info_group)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.results_tree)
        main_layout.addWidget(safety_group)
        
        self.setCentralWidget(central_widget)
        
        # 初始化磁盘信息
        self.update_disk_info()
    
    def update_disk_info(self):
        """更新磁盘信息"""
        disk_info = self.cleaner.get_disk_info()
        self.disk_info_label.setText(
            f"C盘总空间: {disk_info['total']:.2f} GB | "
            f"已用空间: {disk_info['used']:.2f} GB ({disk_info['percent']}%) | "
            f"可用空间: {disk_info['free']:.2f} GB"
        )
    
    def start_scan(self):
        """开始扫描系统"""
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.results_tree.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.status_label.setText("正在扫描系统，请稍候...")
        
        # 启动扫描线程
        self.scan_thread = ScanThread(self.cleaner)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()
    
    def on_scan_finished(self, results):
        """扫描完成后的处理"""
        self.scan_results = results
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        
        if not results:
            self.status_label.setText("扫描完成，未发现可清理项目")
            return
            
        total_size = sum(item['size'] for category in results.values() for item in category)
        self.status_label.setText(f"扫描完成，发现可释放空间: {self.format_size(total_size)}")
        
        # 填充结果树
        self.populate_results_tree(results)
        self.clean_button.setEnabled(True)
        
        # 更新磁盘信息
        self.update_disk_info()
    
    def populate_results_tree(self, results):
        """填充结果树"""
        self.results_tree.clear()
        
        categories = {
            'temp': "临时文件",
            'recycle': "回收站",
            'cache': "浏览器缓存",
            'logs': "系统日志",
            'updates': "Windows更新缓存",
            'thumbnails': "缩略图缓存",
            'downloads': "下载文件夹"
        }
        
        for category, items in results.items():
            if not items:
                continue
                
            category_size = sum(item['size'] for item in items)
            category_name = categories.get(category, category)
            
            category_item = QTreeWidgetItem(self.results_tree)
            category_item.setText(0, category_name)
            category_item.setText(1, self.format_size(category_size))
            category_item.setFlags(category_item.flags() | Qt.ItemIsUserCheckable)
            category_item.setCheckState(0, Qt.Unchecked)
            
            for item in items:
                file_item = QTreeWidgetItem(category_item)
                file_item.setText(0, os.path.basename(item['path']))
                file_item.setText(1, self.format_size(item['size']))
                file_item.setText(2, item['path'])
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
                file_item.setData(0, Qt.UserRole, item)
        
        self.results_tree.expandAll()
    
    def on_item_changed(self, item, column):
        """处理项目选择状态变化"""
        if column != 0:
            return
            
        # 如果是类别项，同步所有子项
        if item.parent() is None:
            check_state = item.checkState(0)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, check_state)
        
        # 更新选中项列表
        self.update_selected_items()
    
    def update_selected_items(self):
        """更新选中的项目列表"""
        self.selected_items = []
        
        for i in range(self.results_tree.topLevelItemCount()):
            category_item = self.results_tree.topLevelItem(i)
            
            for j in range(category_item.childCount()):
                child_item = category_item.child(j)
                if child_item.checkState(0) == Qt.Checked:
                    item_data = child_item.data(0, Qt.UserRole)
                    if item_data:
                        self.selected_items.append(item_data)
        
        # 更新清理按钮状态
        self.clean_button.setEnabled(len(self.selected_items) > 0)
    
    def start_clean(self):
        """开始清理选中的项目"""
        if not self.selected_items:
            return
            
        # 确认对话框
        total_size = sum(item['size'] for item in self.selected_items)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("确认清理")
        
        if self.simulate_checkbox.isChecked():
            msg.setText(f"您选择了模拟模式，将会模拟清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)}。")
        else:
            msg.setText(f"您确定要清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)} 吗？")
            msg.setInformativeText("此操作无法撤销！")
        
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec_() != QMessageBox.Yes:
            return
        
        # 设置清理选项
        self.cleaner.set_options({
            'simulate': self.simulate_checkbox.isChecked(),
            'backup': self.backup_checkbox.isChecked()
        })
        
        # 开始清理
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, len(self.selected_items))
        self.status_label.setText("正在清理文件，请稍候...")
        
        # 启动清理线程
        self.clean_thread = CleanThread(self.cleaner, self.selected_items)
        self.clean_thread.update_signal.connect(self.on_clean_progress)
        self.clean_thread.finished_signal.connect(self.on_clean_finished)
        self.clean_thread.start()
    
    def on_clean_progress(self, file_path, progress):
        """清理进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在清理: {os.path.basename(file_path)}")
    
    def on_clean_finished(self, results):
        """清理完成后的处理"""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        
        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])
        
        if self.simulate_checkbox.isChecked():
            message = f"模拟清理完成，可释放空间: {self.format_size(freed_space)}"
        else:
            message = f"清理完成，已释放空间: {self.format_size(freed_space)}"
        
        if errors:
            message += f"，{len(errors)} 个错误"
        
        self.status_label.setText(message)
        
        # 如果有错误，显示错误日志
        if errors:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("清理错误")
            error_msg.setText(f"清理过程中发生 {len(errors)} 个错误")
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            error_msg.setDetailedText(error_details)
            error_msg.exec_()
        
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
