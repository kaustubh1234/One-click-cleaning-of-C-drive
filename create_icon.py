"""
为C盘清理工具创建图标
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """创建一个简单的图标文件"""
    # 确保icons目录存在
    if not os.path.exists('icons'):
        os.makedirs('icons')
    
    # 创建一个512x512的图像
    img = Image.new('RGBA', (512, 512), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制一个圆形背景
    draw.ellipse((0, 0, 512, 512), fill=(0, 120, 212))
    
    # 绘制一个C盘图标
    draw.rectangle((156, 156, 356, 356), fill=(255, 255, 255))
    draw.rectangle((176, 176, 336, 336), fill=(0, 120, 212))
    
    # 添加文字
    try:
        # 尝试加载字体
        font = ImageFont.truetype("arial.ttf", 120)
        draw.text((206, 186), "C", fill=(255, 255, 255), font=font)
    except IOError:
        # 如果找不到字体，使用默认字体
        draw.text((206, 186), "C", fill=(255, 255, 255))
    
    # 保存为PNG
    png_path = os.path.join('icons', 'cleaner.png')
    img.save(png_path)
    print(f"已创建PNG图标: {os.path.abspath(png_path)}")
    
    # 保存为ICO
    ico_path = os.path.join('icons', 'cleaner.ico')
    img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"已创建ICO图标: {os.path.abspath(ico_path)}")

if __name__ == '__main__':
    create_icon()
