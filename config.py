#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 配置文件
"""

# 应用程序版本
VERSION = "1.0.0"

# 应用程序名称
APP_NAME = "C盘清理工具"

# 默认配置
DEFAULT_CONFIG = {
    # 安全选项
    "simulate_mode": True,      # 模拟模式（不实际删除文件）
    "backup_files": True,       # 删除前备份文件
    
    # 清理选项
    "clean_temp_files": True,   # 清理临时文件
    "clean_recycle_bin": True,  # 清理回收站
    "clean_browser_cache": True, # 清理浏览器缓存
    "clean_system_logs": True,  # 清理系统日志
    "clean_windows_updates": True, # 清理Windows更新缓存
    "clean_thumbnails": True,   # 清理缩略图缓存
    
    # 界面选项
    "language": "zh_CN",        # 界面语言
    "theme": "light",           # 界面主题
    
    # 高级选项
    "scan_depth": 3,            # 扫描深度（目录层级）
    "min_file_size": 1024,      # 最小文件大小（字节）
    "max_backup_size": 1073741824, # 最大备份大小（1GB）
    "max_backups": 5            # 保留的最大备份数量
}

# 安全路径列表 - 这些路径不会被扫描或清理
SAFE_PATHS = [
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Program Files",
    "C:\\Program Files (x86)"
]

# 可清理的文件类型
CLEANABLE_FILE_TYPES = {
    "temp": [".tmp", ".temp", ".~mp"],
    "logs": [".log", ".etl", ".dmp"],
    "cache": [".cache", ".dat"],
    "thumbnails": [".db", ".thumbcache"],
    "updates": [".cab", ".msu", ".msp"]
}

# 临时文件路径
TEMP_PATHS = [
    "%TEMP%",
    "C:\\Windows\\Temp",
    "%LOCALAPPDATA%\\Temp"
]

# 浏览器缓存路径
BROWSER_CACHE_PATHS = {
    "chrome": "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache",
    "edge": "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Cache",
    "firefox": "%APPDATA%\\Mozilla\\Firefox\\Profiles\\*\\cache2"
}

# 系统日志路径
SYSTEM_LOG_PATHS = [
    "C:\\Windows\\Logs",
    "C:\\Windows\\debug"
]

# Windows更新缓存路径
WINDOWS_UPDATE_PATHS = [
    "C:\\Windows\\SoftwareDistribution\\Download",
    "C:\\Windows\\SoftwareDistribution\\DataStore"
]

# 缩略图缓存路径
THUMBNAIL_CACHE_PATHS = [
    "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db"
]
