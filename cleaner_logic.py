#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 核心清理逻辑
"""

import os
import shutil
import tempfile
import time
import glob
import logging
import datetime
import concurrent.futures

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='cleaner.log'
)
logger = logging.getLogger('CCleaner')

class CleanerLogic:
    """清理逻辑核心类"""

    def __init__(self):
        """初始化清理器"""
        self.options = {
            'simulate': True,  # 默认为模拟模式
            'backup': True     # 默认备份文件
        }

        # 安全路径列表 - 这些路径不会被扫描或清理
        self.safe_paths = [
            os.path.join('C:', os.sep, 'Windows', 'System32'),
            os.path.join('C:', os.sep, 'Windows', 'SysWOW64'),
            os.path.join('C:', os.sep, 'Program Files'),
            os.path.join('C:', os.sep, 'Program Files (x86)'),
        ]

        # 默认备份目录
        default_backup_dir = os.path.join(tempfile.gettempdir(), 'CCleaner_Backup')

        # 尝试找到非C盘的默认备份位置
        try:
            # 获取所有磁盘
            import string
            import ctypes

            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(letter + ':')
                bitmask >>= 1

            # 如果有非C盘，使用第一个非C盘作为默认备份位置
            for drive in drives:
                if drive.upper() != 'C:' and os.path.exists(drive):
                    default_backup_dir = os.path.join(drive, 'CCleaner_Backup')
                    break
        except Exception as e:
            logger.warning(f"无法获取非C盘作为备份位置: {e}")

        # 设置备份目录
        self.backup_dir = default_backup_dir

        # 备份限制
        self.max_backups = 5  # 最多保留几个备份
        self.max_backup_size = 1024 * 1024 * 1024  # 1GB

        # 确保备份目录存在
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)

    def set_options(self, options):
        """设置选项"""
        self.options.update(options)

        # 如果设置了自定义备份目录
        if 'backup_dir' in options and options['backup_dir']:
            self.backup_dir = options['backup_dir']
            # 确保备份目录存在
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir, exist_ok=True)

        # 如果设置了备份限制
        if 'max_backups' in options:
            self.max_backups = options['max_backups']
        if 'max_backup_size' in options:
            self.max_backup_size = options['max_backup_size']

        # 如果设置了自定义备份目录
        if 'backup_dir' in options and options['backup_dir']:
            # 确保备份目录存在
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir, exist_ok=True)

        # 如果设置了备份限制
        if 'max_backups' in options:
            self.max_backups = options['max_backups']
        if 'max_backup_size' in options:
            self.max_backup_size = options['max_backup_size']

    def get_disk_info(self):
        """获取C盘信息"""
        try:
            # 使用os.statvfs替代psutil
            # 但Windows不支持statvfs，所以我们使用ctypes调用Windows API
            import ctypes

            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)

            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p('C:'),
                None,
                ctypes.pointer(total_bytes),
                ctypes.pointer(free_bytes)
            )

            total = total_bytes.value / (1024 * 1024 * 1024)  # GB
            free = free_bytes.value / (1024 * 1024 * 1024)    # GB
            used = total - free
            percent = (used / total) * 100 if total > 0 else 0

            return {
                'total': total,
                'used': used,
                'free': free,
                'percent': round(percent, 1)
            }
        except Exception as e:
            logger.error(f"获取磁盘信息失败: {e}")
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent': 0
            }

    def get_backup_info(self):
        """获取备份信息"""
        try:
            if not os.path.exists(self.backup_dir):
                return {
                    'backup_dir': self.backup_dir,
                    'backup_count': 0,
                    'total_size': 0,
                    'backups': []
                }

            # 获取所有备份文件夹
            backups = []
            total_size = 0

            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                if os.path.isdir(item_path):
                    # 计算备份大小
                    backup_size = 0
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    backup_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    # 尝试从文件夹名解析时间
                    try:
                        backup_time = datetime.datetime.strptime(item, '%Y%m%d_%H%M%S')
                        backup_time_str = backup_time.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        backup_time = datetime.datetime.fromtimestamp(os.path.getctime(item_path))
                        backup_time_str = backup_time.strftime('%Y-%m-%d %H:%M:%S')

                    backups.append({
                        'name': item,
                        'path': item_path,
                        'size': backup_size,
                        'time': backup_time_str,
                        'timestamp': backup_time.timestamp()
                    })

                    total_size += backup_size

            # 按时间排序，最新的在前面
            backups.sort(key=lambda x: x['timestamp'], reverse=True)

            return {
                'backup_dir': self.backup_dir,
                'backup_count': len(backups),
                'total_size': total_size,
                'backups': backups
            }
        except Exception as e:
            logger.error(f"获取备份信息失败: {e}")
            return {
                'backup_dir': self.backup_dir,
                'backup_count': 0,
                'total_size': 0,
                'backups': []
            }

    def clean_old_backups(self):
        """清理旧备份"""
        try:
            backup_info = self.get_backup_info()
            backups = backup_info['backups']

            # 如果备份数量超过限制，删除最旧的备份
            if len(backups) > self.max_backups:
                # 按时间排序，最旧的在后面
                backups_to_delete = backups[self.max_backups:]

                for backup in backups_to_delete:
                    try:
                        shutil.rmtree(backup['path'])
                        logger.info(f"删除旧备份: {backup['name']}")
                    except Exception as e:
                        logger.error(f"删除旧备份失败: {backup['path']}, {e}")

            # 如果备份总大小超过限制，从最旧的开始删除
            if backup_info['total_size'] > self.max_backup_size and backups:
                # 按时间排序，最旧的在后面
                remaining_size = backup_info['total_size']

                for backup in reversed(backups):  # 从最旧的开始删除
                    if remaining_size <= self.max_backup_size:
                        break

                    try:
                        shutil.rmtree(backup['path'])
                        logger.info(f"删除超大备份: {backup['name']}")
                        remaining_size -= backup['size']
                    except Exception as e:
                        logger.error(f"删除超大备份失败: {backup['path']}, {e}")

            return True
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return False

    def restore_backup(self, backup_path):
        """恢复备份"""
        try:
            if not os.path.exists(backup_path) or not os.path.isdir(backup_path):
                logger.error(f"备份路径不存在或不是目录: {backup_path}")
                return False

            # 遍历备份目录中的所有文件
            restored_count = 0
            for root, _, files in os.walk(backup_path):
                for file in files:
                    try:
                        # 备份文件路径
                        backup_file_path = os.path.join(root, file)

                        # 计算相对路径
                        rel_path = os.path.relpath(backup_file_path, backup_path)

                        # 原始文件路径
                        original_file_path = os.path.join('C:', os.sep, rel_path)

                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(original_file_path), exist_ok=True)

                        # 复制文件
                        shutil.copy2(backup_file_path, original_file_path)
                        restored_count += 1
                    except Exception as e:
                        logger.error(f"恢复文件失败: {backup_file_path}, {e}")

            logger.info(f"恢复完成，共恢复 {restored_count} 个文件")
            return True
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False

    def scan_system(self):
        """扫描系统中可清理的文件"""
        logger.info("开始扫描系统")
        results = {
            # 基本清理
            'temp': [],          # 临时文件
            'recycle': [],       # 回收站
            'cache': [],         # 浏览器缓存
            'logs': [],          # 系统日志
            'updates': [],       # Windows更新缓存
            'thumbnails': [],    # 缩略图缓存

            # 扩展清理
            'prefetch': [],      # 预读取文件
            'old_windows': [],   # 旧Windows文件
            'error_reports': [], # 错误报告
            'service_packs': [], # 服务包备份
            'memory_dumps': [],  # 内存转储文件
            'font_cache': [],    # 字体缓存
            'disk_cleanup': [],  # 磁盘清理备份

            # 新增安全清理项
            'app_cache': [],     # 应用程序缓存
            'media_cache': [],   # 媒体播放器缓存
            'search_index': [],  # 搜索索引临时文件
            'backup_temp': [],   # 备份临时文件
            'update_temp': [],   # 更新临时文件
            'driver_backup': [], # 驱动备份
            'app_crash': [],     # 应用程序崩溃转储
            'app_logs': [],      # 应用程序日志
            'recent_items': [],  # 最近使用的文件列表缓存
            'notification': [],  # Windows通知缓存
            'dns_cache': [],     # DNS缓存
            'printer_temp': [],  # 打印机临时文件
            'device_temp': [],   # 设备临时文件
            'windows_defender': [], # Windows Defender缓存
            'store_cache': [],   # Windows Store缓存
            'onedrive_cache': [], # OneDrive缓存

            # 新增用户请求的清理项
            'downloads': [],     # 下载文件夹(安全版)
            'installer_cache': [], # 安装程序缓存(安全版)
            'delivery_opt': [],  # Windows传递优化缓存

            # 大文件扫描
            'large_files': []    # 大文件
        }

        # 定义扫描任务
        scan_tasks = [
            self._scan_temp_files,
            self._scan_recycle_bin,
            self._scan_browser_cache,
            self._scan_system_logs,
            self._scan_windows_updates,
            self._scan_thumbnails_cache,
            self._scan_prefetch,
            self._scan_old_windows,
            self._scan_error_reports,
            self._scan_service_packs,
            self._scan_memory_dumps,
            self._scan_font_cache,
            self._scan_disk_cleanup_backup,
            self._scan_app_cache,
            self._scan_media_cache,
            self._scan_search_index,
            self._scan_backup_temp,
            self._scan_update_temp,
            self._scan_driver_backup,
            self._scan_app_crash,
            self._scan_app_logs,
            self._scan_recent_items,
            self._scan_notification_cache,
            self._scan_dns_cache,
            self._scan_printer_temp,
            self._scan_device_temp,
            self._scan_windows_defender,
            self._scan_store_cache,
            self._scan_onedrive_cache,
            self._scan_downloads_immediate,
            self._scan_installer_cache_safe,
            self._scan_delivery_optimization, # Ensure this is the correct one
            self._scan_large_files
        ]

        # 使用ThreadPoolExecutor并发运行扫描任务
        # 根据测试调整max_workers，None通常默认为os.cpu_count（）*5
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有任务
            future_to_task = {executor.submit(task, results): task for task in scan_tasks}

            # 等待所有任务完成并处理潜在的异常
            for future in concurrent.futures.as_completed(future_to_task):
                task_func = future_to_task[future]
                try:
                    future.result()  # 任务期间发生的任何异常
                    logger.info(f"Task {task_func.__name__} completed successfully.")
                except Exception as exc:
                    logger.error(f'Task {task_func.__name__} generated an exception: {exc}')

        # 结果字典由任务直接填充

        logger.info(f"扫描完成，找到 {sum(len(items) for items in results.values())} 个可清理项目")
        return results

    def _scan_temp_files(self, results):
        """扫描临时文件"""
        # 扫描Windows临时文件夹
        temp_dirs = [
            os.environ.get('TEMP', os.path.join('C:', os.sep, 'Windows', 'Temp')),
            os.path.join('C:', os.sep, 'Windows', 'Temp')
        ]

        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir) and self._is_safe_path(temp_dir):
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                file_size = os.path.getsize(file_path)
                                results['temp'].append({
                                    'path': file_path,
                                    'size': file_size,
                                    'type': 'temp'
                                })
                        except (PermissionError, FileNotFoundError) as e:
                            logger.warning(f"无法访问文件 {file_path}: {e}")

    def _scan_recycle_bin(self, results):
        """扫描回收站"""
        recycle_bin = os.path.join('C:', os.sep, '$Recycle.Bin')
        if os.path.exists(recycle_bin):
            total_size = 0
            try:
                for root, _, files in os.walk(recycle_bin):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                file_size = os.path.getsize(file_path)
                                total_size += file_size
                        except (PermissionError, FileNotFoundError):
                            pass

                if total_size > 0:
                    results['recycle'].append({
                        'path': recycle_bin,
                        'size': total_size,
                        'type': 'recycle'
                    })
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问回收站: {e}")

    def _scan_browser_cache(self, results):
        """扫描浏览器缓存"""
        # Chrome缓存
        chrome_cache = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                   'Google', 'Chrome', 'User Data', 'Default', 'Cache')

        # Edge缓存
        edge_cache = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache')

        # Firefox缓存
        firefox_profiles = os.path.join(os.environ.get('APPDATA', ''),
                                      'Mozilla', 'Firefox', 'Profiles')

        cache_dirs = [chrome_cache, edge_cache]

        # 添加Firefox配置文件缓存
        if os.path.exists(firefox_profiles):
            try:
                for profile in os.listdir(firefox_profiles):
                    profile_cache = os.path.join(firefox_profiles, profile, 'cache2')
                    if os.path.exists(profile_cache):
                        cache_dirs.append(profile_cache)
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问Firefox配置文件: {e}")

        # 扫描所有缓存目录
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir) and self._is_safe_path(cache_dir):
                total_size = 0
                try:
                    for root, _, files in os.walk(cache_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['cache'].append({
                            'path': cache_dir,
                            'size': total_size,
                            'type': 'cache'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问缓存目录 {cache_dir}: {e}")

    def _scan_system_logs(self, results):
        """扫描系统日志"""
        log_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Logs'),
            os.path.join('C:', os.sep, 'Windows', 'debug')
        ]

        for log_dir in log_dirs:
            if os.path.exists(log_dir) and self._is_safe_path(log_dir):
                try:
                    for root, _, files in os.walk(log_dir):
                        for file in files:
                            if file.endswith('.log') or file.endswith('.etl') or file.endswith('.dmp'):
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        file_size = os.path.getsize(file_path)
                                        results['logs'].append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'logs'
                                        })
                                except (PermissionError, FileNotFoundError):
                                    pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问日志目录 {log_dir}: {e}")

    def _scan_windows_updates(self, results):
        """扫描Windows更新缓存"""
        update_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'Download'),
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'DataStore')
        ]

        for update_dir in update_dirs:
            if os.path.exists(update_dir) and self._is_safe_path(update_dir):
                total_size = 0
                try:
                    for root, _, files in os.walk(update_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['updates'].append({
                            'path': update_dir,
                            'size': total_size,
                            'type': 'updates'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows更新缓存 {update_dir}: {e}")

    def _scan_thumbnails_cache(self, results):
        """扫描缩略图缓存"""
        thumbnail_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer'),
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer'),
        ]

        for thumb_dir in thumbnail_dirs:
            if os.path.exists(thumb_dir) and self._is_safe_path(thumb_dir):
                try:
                    thumb_db = os.path.join(thumb_dir, 'thumbcache_*.db')
                    for thumb_file in glob.glob(thumb_db):
                        try:
                            if os.path.isfile(thumb_file):
                                file_size = os.path.getsize(thumb_file)
                                results['thumbnails'].append({
                                    'path': thumb_file,
                                    'size': file_size,
                                    'type': 'thumbnails'
                                })
                        except (PermissionError, FileNotFoundError):
                            pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问缩略图缓存 {thumb_dir}: {e}")

    def _scan_prefetch(self, results):
        """扫描预读取文件"""
        prefetch_dir = os.path.join('C:', os.sep, 'Windows', 'Prefetch')

        if os.path.exists(prefetch_dir) and self._is_safe_path(prefetch_dir):
            try:
                for root, _, files in os.walk(prefetch_dir):
                    for file in files:
                        if file.endswith('.pf'):
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    results['prefetch'].append({
                                        'path': file_path,
                                        'size': file_size,
                                        'type': 'prefetch'
                                    })
                            except (PermissionError, FileNotFoundError):
                                pass
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问预读取文件夹 {prefetch_dir}: {e}")

    def _scan_downloads(self, results):
        """扫描下载文件夹"""
        # 获取当前用户的下载文件夹
        download_dirs = [
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'Downloads'),
            os.path.join(os.path.expanduser('~'), 'Downloads')
        ]

        # 添加一些常见的临时下载文件类型
        temp_extensions = ['.tmp', '.temp', '.part', '.crdownload', '.download']
        old_threshold = datetime.datetime.now() - datetime.timedelta(days=30)  # 30天前的文件

        for download_dir in download_dirs:
            if os.path.exists(download_dir) and self._is_safe_path(download_dir):
                try:
                    for root, _, files in os.walk(download_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    # 检查是否是临时下载文件或者超过30天的旧文件
                                    is_temp = any(file.endswith(ext) for ext in temp_extensions)

                                    # 获取文件修改时间
                                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                    is_old = mod_time < old_threshold

                                    if is_temp or is_old:
                                        file_size = os.path.getsize(file_path)
                                        results['downloads'].append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'downloads'
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问下载文件夹 {download_dir}: {e}")

    def _scan_old_windows(self, results):
        """扫描旧Windows文件"""
        old_windows_dirs = [
            os.path.join('C:', os.sep, 'Windows.old'),
            os.path.join('C:', os.sep, '$Windows.~BT'),
            os.path.join('C:', os.sep, '$Windows.~WS')
        ]

        for old_dir in old_windows_dirs:
            if os.path.exists(old_dir) and self._is_safe_path(old_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(old_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['old_windows'].append({
                            'path': old_dir,
                            'size': total_size,
                            'type': 'old_windows'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问旧Windows文件夹 {old_dir}: {e}")

    def _scan_error_reports(self, results):
        """扫描错误报告"""
        error_report_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows', 'WER'),
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'WER'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER')
        ]

        for error_dir in error_report_dirs:
            if os.path.exists(error_dir) and self._is_safe_path(error_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(error_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['error_reports'].append({
                            'path': error_dir,
                            'size': total_size,
                            'type': 'error_reports'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问错误报告文件夹 {error_dir}: {e}")

    def _scan_service_packs(self, results):
        """扫描服务包备份"""
        service_pack_dirs = [
            os.path.join('C:', os.sep, 'Windows', '$NtServicePackUninstall$'),
            os.path.join('C:', os.sep, 'Windows', '$hf_mig$')
        ]

        for sp_dir in service_pack_dirs:
            if os.path.exists(sp_dir) and self._is_safe_path(sp_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(sp_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['service_packs'].append({
                            'path': sp_dir,
                            'size': total_size,
                            'type': 'service_packs'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问服务包备份文件夹 {sp_dir}: {e}")

    def _scan_hibernation_file(self, results):
        """扫描休眠文件"""
        hibernation_file = os.path.join('C:', os.sep, 'hiberfil.sys')

        if os.path.exists(hibernation_file) and self._is_safe_path(hibernation_file):
            try:
                file_size = os.path.getsize(hibernation_file)
                if file_size > 0:
                    results['hibernation'].append({
                        'path': hibernation_file,
                        'size': file_size,
                        'type': 'hibernation'
                    })
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问休眠文件 {hibernation_file}: {e}")

    def _scan_memory_dumps(self, results):
        """扫描内存转储文件"""
        memory_dump_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Minidump'),
            os.path.join('C:', os.sep, 'Windows', 'MEMORY.DMP'),
            os.path.join('C:', os.sep, 'Windows', 'memory.dmp')
        ]

        for dump_dir in memory_dump_dirs:
            if os.path.exists(dump_dir) and self._is_safe_path(dump_dir):
                try:
                    if os.path.isfile(dump_dir):
                        # 如果是文件
                        file_size = os.path.getsize(dump_dir)
                        if file_size > 0:
                            results['memory_dumps'].append({
                                'path': dump_dir,
                                'size': file_size,
                                'type': 'memory_dumps'
                            })
                    else:
                        # 如果是目录
                        total_size = 0
                        for root, _, files in os.walk(dump_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        total_size += os.path.getsize(file_path)
                                except (PermissionError, FileNotFoundError):
                                    pass

                        if total_size > 0:
                            results['memory_dumps'].append({
                                'path': dump_dir,
                                'size': total_size,
                                'type': 'memory_dumps'
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问内存转储文件 {dump_dir}: {e}")

    def _scan_delivery_optimization(self, results):
        """扫描Windows传递优化缓存"""
        delivery_opt_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'ServiceProfiles', 'NetworkService', 'AppData', 'Local', 'Microsoft', 'Windows', 'DeliveryOptimization', 'Cache'),
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'DeliveryOptimization', 'Cache')
        ]

        for opt_dir in delivery_opt_dirs:
            if os.path.exists(opt_dir) and self._is_safe_path(opt_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(opt_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['delivery_opt'].append({
                            'path': opt_dir,
                            'size': total_size,
                            'type': 'delivery_opt'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows传递优化缓存 {opt_dir}: {e}")

    def _scan_font_cache(self, results):
        """扫描字体缓存"""
        font_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'ServiceProfiles', 'LocalService', 'AppData', 'Local', 'FontCache'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'FNTCACHE.DAT')
        ]

        for font_dir in font_cache_dirs:
            if os.path.exists(font_dir) and self._is_safe_path(font_dir):
                try:
                    if os.path.isfile(font_dir):
                        # 如果是文件
                        file_size = os.path.getsize(font_dir)
                        if file_size > 0:
                            results['font_cache'].append({
                                'path': font_dir,
                                'size': file_size,
                                'type': 'font_cache'
                            })
                    else:
                        # 如果是目录
                        total_size = 0
                        for root, _, files in os.walk(font_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        total_size += os.path.getsize(file_path)
                                except (PermissionError, FileNotFoundError):
                                    pass

                        if total_size > 0:
                            results['font_cache'].append({
                                'path': font_dir,
                                'size': total_size,
                                'type': 'font_cache'
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问字体缓存 {font_dir}: {e}")

    def _scan_installer_cache(self, results):
        """扫描安装程序缓存"""
        installer_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Installer'),
            os.path.join('C:', os.sep, 'ProgramData', 'Package Cache'),
            os.path.join('C:', os.sep, 'Windows', 'Downloaded Program Files')
        ]

        # 超过90天的安装程序缓存
        old_threshold = datetime.datetime.now() - datetime.timedelta(days=90)

        for installer_dir in installer_cache_dirs:
            if os.path.exists(installer_dir) and self._is_safe_path(installer_dir):
                try:
                    for root, _, files in os.walk(installer_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    # 检查文件是否超过90天未修改
                                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                    if mod_time < old_threshold:
                                        file_size = os.path.getsize(file_path)
                                        results['installer_cache'].append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'installer_cache'
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问安装程序缓存 {installer_dir}: {e}")

    def _scan_disk_cleanup_backup(self, results):
        """扫描磁盘清理备份"""
        cleanup_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'LogFiles', 'setupapi'),
            os.path.join('C:', os.sep, 'Windows', 'Temp', 'CheckSur'),
            os.path.join('C:', os.sep, 'Windows', 'Logs', 'CBS')
        ]

        for cleanup_dir in cleanup_dirs:
            if os.path.exists(cleanup_dir) and self._is_safe_path(cleanup_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(cleanup_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['disk_cleanup'].append({
                            'path': cleanup_dir,
                            'size': total_size,
                            'type': 'disk_cleanup'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问磁盘清理备份 {cleanup_dir}: {e}")

    def _scan_app_cache(self, results):
        """扫描应用程序缓存"""
        # 常见应用程序缓存目录
        app_cache_dirs = [
            # Adobe缓存
            os.path.join(os.environ.get('APPDATA', ''), 'Adobe', 'Common'),
            # Office缓存
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Office', 'Recent'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Office', 'OTele'),
            # 其他常见应用缓存
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'DriveFS'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Teams', 'Cache'),
            os.path.join(os.environ.get('APPDATA', ''), 'Slack', 'Cache'),
            os.path.join(os.environ.get('APPDATA', ''), 'discord', 'Cache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'INetCache', 'IE')
        ]

        for cache_dir in app_cache_dirs:
            if os.path.exists(cache_dir) and self._is_safe_path(cache_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(cache_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['app_cache'].append({
                            'path': cache_dir,
                            'size': total_size,
                            'type': 'app_cache'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问应用程序缓存 {cache_dir}: {e}")

    def _scan_media_cache(self, results):
        """扫描媒体播放器缓存"""
        # 媒体播放器缓存目录
        media_cache_dirs = [
            # Windows Media Player
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Media Player'),
            # VLC
            os.path.join(os.environ.get('APPDATA', ''), 'vlc', 'art'),
            # Spotify
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Spotify', 'Storage'),
            os.path.join(os.environ.get('APPDATA', ''), 'Spotify', 'cache'),
            # 其他媒体应用
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer', 'iconcache*')
        ]

        for cache_dir in media_cache_dirs:
            # 处理通配符模式
            if '*' in cache_dir:
                try:
                    for matched_path in glob.glob(cache_dir):
                        if os.path.exists(matched_path) and self._is_safe_path(matched_path):
                            try:
                                if os.path.isfile(matched_path):
                                    file_size = os.path.getsize(matched_path)
                                    if file_size > 0:
                                        results['media_cache'].append({
                                            'path': matched_path,
                                            'size': file_size,
                                            'type': 'media_cache'
                                        })
                            except (PermissionError, FileNotFoundError) as e:
                                logger.warning(f"无法访问媒体缓存文件 {matched_path}: {e}")
                except Exception as e:
                    logger.warning(f"处理通配符模式时出错 {cache_dir}: {e}")
                continue

            # 处理普通目录
            if os.path.exists(cache_dir) and self._is_safe_path(cache_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(cache_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    total_size += os.path.getsize(file_path)
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['media_cache'].append({
                            'path': cache_dir,
                            'size': total_size,
                            'type': 'media_cache'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问媒体缓存 {cache_dir}: {e}")

    def _scan_search_index(self, results):
        """扫描搜索索引临时文件"""
        # Windows搜索索引临时文件目录
        search_index_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Search', 'Data', 'Temp'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Search', 'Data', 'Applications', 'Windows'),
            os.path.join('C:', os.sep, 'Windows', 'ServiceProfiles', 'LocalService', 'AppData', 'Local', 'Microsoft', 'Windows', 'Search')
        ]

        # 只清理临时文件和旧索引文件
        temp_extensions = ['.tmp', '.old', '.bak', '.log']

        for index_dir in search_index_dirs:
            if os.path.exists(index_dir) and self._is_safe_path(index_dir):
                try:
                    for root, _, files in os.walk(index_dir):
                        for file in files:
                            try:
                                # 只清理临时文件和旧索引文件
                                if any(file.endswith(ext) for ext in temp_extensions):
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        file_size = os.path.getsize(file_path)
                                        results['search_index'].append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'search_index'
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问搜索索引目录 {index_dir}: {e}")

    def _scan_backup_temp(self, results):
        """扫描备份临时文件"""
        # Windows备份临时文件目录
        backup_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Temp', 'WindowsBackup'),
            os.path.join('C:', os.sep, 'Windows', 'Logs', 'WindowsBackup'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WindowsBackup')
        ]

        for backup_dir in backup_temp_dirs:
            if os.path.exists(backup_dir) and self._is_safe_path(backup_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(backup_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    # 检查是否是旧文件（超过30天）
                                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                    if (datetime.datetime.now() - mod_time).days > 30:
                                        file_size = os.path.getsize(file_path)
                                        total_size += file_size
                                        results['backup_temp'].append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'backup_temp'
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问备份临时文件目录 {backup_dir}: {e}")

    def _scan_update_temp(self, results):
        """扫描更新临时文件"""
        # Windows更新临时文件目录
        update_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'PostRebootEventCache'),
            os.path.join('C:', os.sep, 'Windows', 'SoftwareDistribution', 'Temp'),
            os.path.join('C:', os.sep, 'Windows', 'WinSxS', 'Temp'),
            os.path.join('C:', os.sep, 'Windows', 'Temp', 'TrustedInstaller')
        ]

        for update_dir in update_temp_dirs:
            if os.path.exists(update_dir) and self._is_safe_path(update_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(update_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['update_temp'].append({
                            'path': update_dir,
                            'size': total_size,
                            'type': 'update_temp'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问更新临时文件目录 {update_dir}: {e}")

    def _scan_driver_backup(self, results):
        """扫描驱动备份"""
        # 驱动备份目录
        driver_backup_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'inf', 'OLD'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'DriverStore', 'Temp')
        ]

        for driver_dir in driver_backup_dirs:
            if os.path.exists(driver_dir) and self._is_safe_path(driver_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(driver_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['driver_backup'].append({
                            'path': driver_dir,
                            'size': total_size,
                            'type': 'driver_backup'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问驱动备份目录 {driver_dir}: {e}")

    def _scan_app_crash(self, results):
        """扫描应用程序崩溃转储"""
        # 应用程序崩溃转储目录
        app_crash_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows', 'WER', 'ReportArchive'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows', 'WER', 'ReportQueue'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CrashDumps'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER', 'ReportArchive'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER', 'ReportQueue')
        ]

        for crash_dir in app_crash_dirs:
            if os.path.exists(crash_dir) and self._is_safe_path(crash_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(crash_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['app_crash'].append({
                            'path': crash_dir,
                            'size': total_size,
                            'type': 'app_crash'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问应用程序崩溃转储目录 {crash_dir}: {e}")

    def _scan_app_logs(self, results):
        """扫描应用程序日志"""
        # 常见应用程序日志目录
        app_log_dirs = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Teams', 'logs.txt'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Teams', 'logs'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Office', '*.log'),
            os.path.join(os.environ.get('APPDATA', ''), 'Slack', 'logs'),
            os.path.join(os.environ.get('APPDATA', ''), 'discord', 'logs')
        ]

        # 超过30天的日志文件
        old_threshold = datetime.datetime.now() - datetime.timedelta(days=30)

        for log_dir in app_log_dirs:
            # 处理通配符模式
            if '*' in log_dir:
                try:
                    for matched_path in glob.glob(log_dir):
                        if os.path.exists(matched_path) and self._is_safe_path(matched_path):
                            try:
                                if os.path.isfile(matched_path):
                                    # 检查是否是旧文件
                                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(matched_path))
                                    if mod_time < old_threshold:
                                        file_size = os.path.getsize(matched_path)
                                        if file_size > 0:
                                            results['app_logs'].append({
                                                'path': matched_path,
                                                'size': file_size,
                                                'type': 'app_logs'
                                            })
                            except (PermissionError, FileNotFoundError) as e:
                                logger.warning(f"无法访问应用程序日志文件 {matched_path}: {e}")
                except Exception as e:
                    logger.warning(f"处理通配符模式时出错 {log_dir}: {e}")
                continue

            # 处理普通目录
            if os.path.exists(log_dir) and self._is_safe_path(log_dir):
                try:
                    if os.path.isfile(log_dir):
                        # 如果是文件
                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(log_dir))
                        if mod_time < old_threshold:
                            file_size = os.path.getsize(log_dir)
                            if file_size > 0:
                                results['app_logs'].append({
                                    'path': log_dir,
                                    'size': file_size,
                                    'type': 'app_logs'
                                })
                    else:
                        # 如果是目录
                        for root, _, files in os.walk(log_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        # 检查是否是旧文件
                                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                        if mod_time < old_threshold:
                                            file_size = os.path.getsize(file_path)
                                            results['app_logs'].append({
                                                'path': file_path,
                                                'size': file_size,
                                                'type': 'app_logs'
                                            })
                                except (PermissionError, FileNotFoundError):
                                    pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问应用程序日志 {log_dir}: {e}")

    def _scan_recent_items(self, results):
        """扫描最近使用的文件列表缓存"""
        # 最近使用的文件列表缓存目录
        recent_dirs = [
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Recent'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Office', 'Recent')
        ]

        for recent_dir in recent_dirs:
            if os.path.exists(recent_dir) and self._is_safe_path(recent_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(recent_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['recent_items'].append({
                            'path': recent_dir,
                            'size': total_size,
                            'type': 'recent_items'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问最近使用的文件列表缓存 {recent_dir}: {e}")

    def _scan_notification_cache(self, results):
        """扫描Windows通知缓存"""
        # Windows通知缓存目录
        notification_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Notifications'),
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'AppData', 'Local', 'Microsoft', 'Windows', 'ActionCenterCache')
        ]

        for notification_dir in notification_dirs:
            if os.path.exists(notification_dir) and self._is_safe_path(notification_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(notification_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['notification'].append({
                            'path': notification_dir,
                            'size': total_size,
                            'type': 'notification'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows通知缓存 {notification_dir}: {e}")

    def _scan_dns_cache(self, results):
        """扫描DNS缓存"""
        # DNS缓存目录
        dns_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'dnsrslvr.log'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'dns', 'cache.dns')
        ]

        for dns_dir in dns_cache_dirs:
            if os.path.exists(dns_dir) and self._is_safe_path(dns_dir):
                try:
                    if os.path.isfile(dns_dir):
                        file_size = os.path.getsize(dns_dir)
                        if file_size > 0:
                            results['dns_cache'].append({
                                'path': dns_dir,
                                'size': file_size,
                                'type': 'dns_cache'
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问DNS缓存 {dns_dir}: {e}")

    def _scan_network_cache(self, results):
        """扫描网络缓存"""
        # 网络缓存目录
        network_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'drivers', 'etc', 'hosts.ics'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'drivers', 'etc', 'networks'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'wbem', 'Repository', 'FS', 'INDEX.BTR')
        ]

        for network_dir in network_cache_dirs:
            if os.path.exists(network_dir) and self._is_safe_path(network_dir):
                try:
                    if os.path.isfile(network_dir):
                        file_size = os.path.getsize(network_dir)
                        if file_size > 0:
                            results['network_cache'].append({
                                'path': network_dir,
                                'size': file_size,
                                'type': 'network_cache'
                            })
                    else:
                        total_size = 0
                        for root, _, files in os.walk(network_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        file_size = os.path.getsize(file_path)
                                        total_size += file_size
                                except (PermissionError, FileNotFoundError):
                                    pass

                        if total_size > 0:
                            results['network_cache'].append({
                                'path': network_dir,
                                'size': total_size,
                                'type': 'network_cache'
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问网络缓存 {network_dir}: {e}")

    def _scan_printer_temp(self, results):
        """扫描打印机临时文件"""
        # 打印机临时文件目录
        printer_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'System32', 'spool', 'PRINTERS'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'spool', 'SERVERS'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'spool', 'drivers', 'color')
        ]

        for printer_dir in printer_temp_dirs:
            if os.path.exists(printer_dir) and self._is_safe_path(printer_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(printer_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['printer_temp'].append({
                            'path': printer_dir,
                            'size': total_size,
                            'type': 'printer_temp'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问打印机临时文件目录 {printer_dir}: {e}")

    def _scan_device_temp(self, results):
        """扫描设备临时文件"""
        # 设备临时文件目录
        device_temp_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'INF', 'setupapi.dev.log'),
            os.path.join('C:', os.sep, 'Windows', 'INF', 'setupapi.log'),
            os.path.join('C:', os.sep, 'Windows', 'System32', 'LogFiles', 'setupapi')
        ]

        for device_dir in device_temp_dirs:
            if os.path.exists(device_dir) and self._is_safe_path(device_dir):
                try:
                    if os.path.isfile(device_dir):
                        file_size = os.path.getsize(device_dir)
                        if file_size > 0:
                            results['device_temp'].append({
                                'path': device_dir,
                                'size': file_size,
                                'type': 'device_temp'
                            })
                    else:
                        total_size = 0
                        for root, _, files in os.walk(device_dir):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        file_size = os.path.getsize(file_path)
                                        total_size += file_size
                                except (PermissionError, FileNotFoundError):
                                    pass

                        if total_size > 0:
                            results['device_temp'].append({
                                'path': device_dir,
                                'size': total_size,
                                'type': 'device_temp'
                            })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问设备临时文件目录 {device_dir}: {e}")

    def _scan_windows_defender(self, results):
        """扫描Windows Defender缓存"""
        # Windows Defender缓存目录
        defender_dirs = [
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows Defender', 'Scans', 'History'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows Defender', 'Quarantine'),
            os.path.join('C:', os.sep, 'ProgramData', 'Microsoft', 'Windows Defender', 'Support')
        ]

        for defender_dir in defender_dirs:
            if os.path.exists(defender_dir) and self._is_safe_path(defender_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(defender_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['windows_defender'].append({
                            'path': defender_dir,
                            'size': total_size,
                            'type': 'windows_defender'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows Defender缓存目录 {defender_dir}: {e}")

    def _scan_store_cache(self, results):
        """扫描Windows Store缓存"""
        # Windows Store缓存目录
        store_cache_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', 'Microsoft.WindowsStore_8wekyb3d8bbwe', 'LocalCache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', 'Microsoft.WindowsStore_8wekyb3d8bbwe', 'LocalState'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Packages', 'Microsoft.WindowsStore_8wekyb3d8bbwe', 'TempState')
        ]

        for store_dir in store_cache_dirs:
            if os.path.exists(store_dir) and self._is_safe_path(store_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(store_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['store_cache'].append({
                            'path': store_dir,
                            'size': total_size,
                            'type': 'store_cache'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问Windows Store缓存目录 {store_dir}: {e}")

    def _scan_onedrive_cache(self, results):
        """扫描OneDrive缓存"""
        # OneDrive缓存目录
        onedrive_cache_dirs = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'OneDrive', 'logs'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'OneDrive', 'settings', 'Personal', 'logs')
        ]

        for onedrive_dir in onedrive_cache_dirs:
            if os.path.exists(onedrive_dir) and self._is_safe_path(onedrive_dir):
                try:
                    total_size = 0
                    for root, _, files in os.walk(onedrive_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['onedrive_cache'].append({
                            'path': onedrive_dir,
                            'size': total_size,
                            'type': 'onedrive_cache'
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问OneDrive缓存目录 {onedrive_dir}: {e}")

    def _scan_downloads_immediate(self, results):
        """扫描下载文件夹(立即清理)"""
        # 获取当前用户的下载文件夹
        download_dirs = [
            os.path.join('C:', os.sep, 'Users', os.environ.get('USERNAME', ''), 'Downloads'),
            os.path.join(os.path.expanduser('~'), 'Downloads')
        ]

        for download_dir in download_dirs:
            if os.path.exists(download_dir) and self._is_safe_path(download_dir):
                try:
                    total_size = 0
                    file_count = 0

                    for root, _, files in os.walk(download_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    total_size += file_size
                                    file_count += 1
                            except (PermissionError, FileNotFoundError):
                                pass

                    if total_size > 0:
                        results['downloads'].append({
                            'path': download_dir,
                            'size': total_size,
                            'type': 'downloads',
                            'file_count': file_count
                        })
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问下载文件夹 {download_dir}: {e}")

    def _scan_installer_cache_safe(self, results):
        """扫描安装程序缓存(安全版)"""
        # 安装程序缓存目录
        installer_cache_dirs = [
            os.path.join('C:', os.sep, 'Windows', 'Installer', 'Temp'),
            os.path.join('C:', os.sep, 'ProgramData', 'Package Cache', 'Temp'),
            os.path.join('C:', os.sep, 'Windows', 'Downloaded Program Files', 'Temp'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Package Cache'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'Downloaded Installations')
        ]

        # 安全可清理的文件类型
        safe_extensions = ['.tmp', '.temp', '.msi.cache', '.exe.cache', '.log', '.old']

        # 超过30天的安装程序缓存
        very_old_threshold = datetime.datetime.now() - datetime.timedelta(days=30)  # 30天前的文件

        for installer_dir in installer_cache_dirs:
            if os.path.exists(installer_dir) and self._is_safe_path(installer_dir):
                try:
                    for root, _, files in os.walk(installer_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    # 检查是否是安全可清理的文件
                                    is_safe_temp = any(file.lower().endswith(ext) for ext in safe_extensions)

                                    # 检查是否是超过365天的文件
                                    is_very_old = False
                                    if not is_safe_temp:  # 如果不是安全的临时文件，检查是否非常旧
                                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                        is_very_old = mod_time < very_old_threshold

                                    if is_safe_temp or is_very_old:
                                        file_size = os.path.getsize(file_path)
                                        file_type = "temp_installer" if is_safe_temp else "very_old_installer"
                                        results['installer_cache'].append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'installer_cache',
                                            'subtype': file_type
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法访问安装程序缓存目录 {installer_dir}: {e}")

        # 特殊处理Windows Installer目录
        windows_installer = os.path.join('C:', os.sep, 'Windows', 'Installer')
        if os.path.exists(windows_installer) and self._is_safe_path(windows_installer):
            try:
                # 查找安全可清理的文件
                for root, _, files in os.walk(windows_installer):
                    for file in files:
                        try:
                            if file.lower().endswith(('.msp.cache', '.msi.cache', '.tmp', '.temp')):
                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    results['installer_cache'].append({
                                        'path': file_path,
                                        'size': file_size,
                                        'type': 'installer_cache',
                                        'subtype': 'windows_installer_cache'
                                    })
                        except (PermissionError, FileNotFoundError):
                            pass
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"无法访问Windows Installer目录 {windows_installer}: {e}")

    def _scan_large_files(self, results):
        """扫描C盘中的大文件"""
        # 大文件的最小大小（100MB）
        min_size = 100 * 1024 * 1024

        # 要扫描的目录
        scan_dirs = [
            'C:\\Users',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
            'C:\\ProgramData'
        ]

        # 要排除的目录
        exclude_dirs = [
            'C:\\Windows',
            'C:\\Program Files\\WindowsApps',
            'C:\\Program Files (x86)\\WindowsApps',
            'C:\\$Recycle.Bin'
        ]

        # 要排除的文件类型
        exclude_extensions = [
            '.sys', '.dll', '.exe', '.msi', '.mui', '.idx', '.cat', '.db'
        ]

        # 大文件列表
        large_files = []

        # 扫描指定目录
        for scan_dir in scan_dirs:
            if os.path.exists(scan_dir) and self._is_safe_path(scan_dir):
                try:
                    for root, dirs, files in os.walk(scan_dir):
                        # 跳过排除的目录
                        dirs[:] = [d for d in dirs if os.path.join(root, d) not in exclude_dirs]

                        for file in files:
                            try:
                                # 跳过排除的文件类型
                                if any(file.lower().endswith(ext) for ext in exclude_extensions):
                                    continue

                                file_path = os.path.join(root, file)
                                if os.path.isfile(file_path) and self._is_safe_path(file_path):
                                    file_size = os.path.getsize(file_path)
                                    if file_size >= min_size:
                                        # 获取文件修改时间
                                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                                        # 获取文件类型
                                        _, ext = os.path.splitext(file_path)

                                        large_files.append({
                                            'path': file_path,
                                            'size': file_size,
                                            'type': 'large_files',
                                            'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                                            'extension': ext.lower() if ext else ''
                                        })
                            except (PermissionError, FileNotFoundError):
                                pass
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"无法扫描目录 {scan_dir}: {e}")

        # 按文件大小降序排序
        large_files.sort(key=lambda x: x['size'], reverse=True)

        # 只保留前100个最大的文件
        large_files = large_files[:100]

        # 添加到结果中
        results['large_files'].extend(large_files)

        logger.info(f"找到 {len(large_files)} 个大文件")

    def clean_selected(self, items, progress_callback=None):
        """清理选中的项目"""
        logger.info(f"开始清理 {len(items)} 个项目")

        results = {
            'cleaned_items': [],
            'errors': [],
            'freed_space': 0
        }

        # 创建当前备份目录
        if self.options['backup']:
            current_backup_dir = os.path.join(
                self.backup_dir,
                datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            os.makedirs(current_backup_dir, exist_ok=True)

            # 清理旧备份
            self.clean_old_backups()

        for i, item in enumerate(items):
            try:
                path = item['path']
                item_type = item.get('type', 'unknown')

                # 更新进度
                if progress_callback:
                    progress_callback.emit(path, i + 1)

                # 检查路径安全性
                if not self._is_safe_path(path):
                    logger.warning(f"跳过不安全路径: {path}")
                    results['errors'].append({
                        'path': path,
                        'error': '不安全的路径'
                    })
                    continue

                # 处理不同类型的项目
                if item_type == 'recycle':
                    # 清空回收站
                    if not self.options['simulate']:
                        self._empty_recycle_bin()
                    results['freed_space'] += item['size']
                    results['cleaned_items'].append(path)
                elif os.path.isdir(path):
                    # 清理目录
                    freed = self._clean_directory(path, current_backup_dir if self.options['backup'] else None)
                    results['freed_space'] += freed
                    results['cleaned_items'].append(path)
                elif os.path.isfile(path):
                    # 清理文件
                    freed = self._clean_file(path, current_backup_dir if self.options['backup'] else None)
                    results['freed_space'] += freed
                    results['cleaned_items'].append(path)

                # 模拟模式下，添加项目大小
                if self.options['simulate']:
                    results['freed_space'] += item['size']

            except Exception as e:
                logger.error(f"清理项目 {item['path']} 时出错: {e}")
                results['errors'].append({
                    'path': item['path'],
                    'error': str(e)
                })

        logger.info(f"清理完成，释放空间: {results['freed_space']} 字节，错误: {len(results['errors'])}")
        return results

    def _clean_file(self, file_path, backup_dir=None):
        """清理单个文件"""
        try:
            if not os.path.exists(file_path):
                return 0

            file_size = os.path.getsize(file_path)

            # 模拟模式下不实际删除
            if self.options['simulate']:
                logger.info(f"模拟删除文件: {file_path}")
                return file_size

            # 备份文件
            if backup_dir:
                try:
                    rel_path = os.path.basename(file_path)
                    backup_path = os.path.join(backup_dir, rel_path)
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    shutil.copy2(file_path, backup_path)
                    logger.info(f"已备份文件: {file_path} -> {backup_path}")
                except Exception as e:
                    logger.warning(f"备份文件 {file_path} 失败: {e}")

            # 安全删除文件
            try:
                # 尝试使用Windows API移动到回收站
                import ctypes
                from ctypes import windll
                from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL

                SHFileOperationW = windll.shell32.SHFileOperationW

                class SHFILEOPSTRUCTW(ctypes.Structure):
                    _fields_ = [
                        ("hwnd", HWND),
                        ("wFunc", UINT),
                        ("pFrom", LPCWSTR),
                        ("pTo", LPCWSTR),
                        ("fFlags", UINT),
                        ("fAnyOperationsAborted", BOOL),
                        ("hNameMappings", ctypes.c_void_p),
                        ("lpszProgressTitle", LPCWSTR)
                    ]

                FO_DELETE = 3
                FOF_ALLOWUNDO = 0x40  # 允许撤销（移动到回收站）
                FOF_NOCONFIRMATION = 0x10  # 不显示确认对话框

                # 添加结束空字符和额外的空字符
                path = file_path + '\0\0'

                fileop = SHFILEOPSTRUCTW(
                    None,  # hwnd
                    FO_DELETE,  # wFunc
                    path,  # pFrom
                    None,  # pTo
                    FOF_ALLOWUNDO | FOF_NOCONFIRMATION,  # fFlags
                    None,  # fAnyOperationsAborted
                    None,  # hNameMappings
                    None  # lpszProgressTitle
                )

                result = SHFileOperationW(ctypes.byref(fileop))
                if result == 0:
                    logger.info(f"已删除文件到回收站: {file_path}")
                else:
                    # 如果API调用失败，则直接删除
                    os.remove(file_path)
                    logger.info(f"已直接删除文件: {file_path}")
            except Exception as e:
                # 如果出错，则直接删除
                os.remove(file_path)
                logger.info(f"已直接删除文件: {file_path}")

            return file_size
        except Exception as e:
            logger.error(f"清理文件 {file_path} 失败: {e}")
            raise

    def _clean_directory(self, dir_path, backup_dir=None):
        """清理目录"""
        try:
            if not os.path.exists(dir_path):
                return 0

            total_freed = 0

            # 模拟模式下不实际删除
            if self.options['simulate']:
                logger.info(f"模拟清理目录: {dir_path}")
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                total_freed += os.path.getsize(file_path)
                        except (PermissionError, FileNotFoundError):
                            pass
                return total_freed

            # 实际清理目录
            for root, dirs, files in os.walk(dir_path, topdown=False):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)

                        # 备份文件
                        if backup_dir:
                            try:
                                rel_path = os.path.relpath(file_path, dir_path)
                                backup_path = os.path.join(backup_dir, rel_path)
                                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                                shutil.copy2(file_path, backup_path)
                            except Exception as e:
                                logger.warning(f"备份文件 {file_path} 失败: {e}")

                        # 删除文件
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            total_freed += file_size
                            logger.info(f"已删除文件: {file_path}")
                    except (PermissionError, FileNotFoundError) as e:
                        logger.warning(f"删除文件 {os.path.join(root, file)} 失败: {e}")

                # 删除空目录
                for dir_name in dirs:
                    try:
                        dir_to_remove = os.path.join(root, dir_name)
                        if os.path.exists(dir_to_remove) and not os.listdir(dir_to_remove):
                            os.rmdir(dir_to_remove)
                            logger.info(f"已删除空目录: {dir_to_remove}")
                    except (PermissionError, FileNotFoundError) as e:
                        logger.warning(f"删除目录 {os.path.join(root, dir_name)} 失败: {e}")

            return total_freed
        except Exception as e:
            logger.error(f"清理目录 {dir_path} 失败: {e}")
            raise

    def _empty_recycle_bin(self):
        """清空回收站"""
        try:
            # 使用PowerShell清空回收站
            import subprocess
            subprocess.run(['powershell.exe', '-Command', 'Clear-RecycleBin', '-Force', '-ErrorAction', 'SilentlyContinue'],
                          check=False,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
            logger.info("已清空回收站")
            return True
        except Exception as e:
            logger.error(f"清空回收站失败: {e}")
            return False

    def _is_safe_path(self, path):
        """检查路径是否安全（不在系统关键目录中）"""
        # 检查路径是否在安全路径列表中
        for safe_path in self.safe_paths:
            if path.startswith(safe_path):
                # 如果是系统目录的子目录，需要特别小心
                return False

        # 检查是否是系统目录
        system_dirs = [
            os.path.join('C:', os.sep, 'Windows'),
            os.path.join('C:', os.sep, 'Program Files'),
            os.path.join('C:', os.sep, 'Program Files (x86)'),
            os.path.join('C:', os.sep, 'ProgramData')
        ]

        for sys_dir in system_dirs:
            if path == sys_dir:
                return False

        return True
