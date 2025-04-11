"""
打包C盘清理工具为EXE文件
"""

import os
import shutil
import subprocess
import sys

def build_exe():
    """使用PyInstaller打包应用为EXE文件"""
    print("开始打包C盘清理工具为EXE文件...")
    
    # 创建输出目录
    if not os.path.exists('dist'):
        os.makedirs('dist')
    
    # 清理旧的构建文件
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # 使用PyInstaller打包
    cmd = [
        'pyinstaller',
        '--name=C盘清理工具',
        '--windowed',  # 无控制台窗口
        '--icon=icons/cleaner.ico',  # 图标
        '--add-data=icons;icons',  # 包含图标文件夹
        '--noconfirm',  # 不询问覆盖
        '--clean',  # 清理临时文件
        'main.py'  # 主脚本
    ]
    
    # 在Windows上使用分号作为路径分隔符
    if sys.platform.startswith('win'):
        cmd[5] = '--add-data=icons;icons'
    else:
        cmd[5] = '--add-data=icons:icons'
    
    # 执行打包命令
    subprocess.call(cmd)
    
    print("打包完成！")
    print(f"EXE文件位于: {os.path.abspath('dist/C盘清理工具/C盘清理工具.exe')}")
    
    # 创建启动批处理文件
    with open('dist/C盘清理工具/启动C盘清理工具.bat', 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('echo 正在启动C盘清理工具...\n')
        f.write('start "" "%~dp0C盘清理工具.exe"\n')
    
    print("已创建启动批处理文件")
    
    # 创建ZIP文件
    shutil.make_archive('C盘清理工具', 'zip', 'dist/C盘清理工具')
    print(f"已创建ZIP文件: {os.path.abspath('C盘清理工具.zip')}")

if __name__ == '__main__':
    build_exe()
