from PIL import Image
import os
from datetime import datetime
from PIL import ImageDraw, ImageFont

TEMPLATE_PATH = "resource/newspaper_template.png"
FONT_PATH = "resource/msyh.ttc"  # 如果有别的路径，请自行改写

def create_newspaper_image(photo_path, weather_str, output_path="final_newspaper.png"):
    """
    合成最终的报纸图片
    """
    template = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(template)
    user_photo = Image.open(photo_path).convert("RGB")

    # 根据模板中用户照片需要的大小进行 resize
    user_photo = user_photo.resize((448, 336))

    # 将照片粘贴到模板上的指定位置 (需根据模板实际情况设置)
    template.paste(user_photo, (210, 250))  # 假定 (210,250)

    # 设置字体
    if FONT_PATH and os.path.exists(FONT_PATH):
        font = ImageFont.truetype(FONT_PATH, 15)
    else:
        font = ImageFont.load_default()

    now_date = datetime.now()
    date_str = f"{now_date.year}年{now_date.month}月{now_date.day}日"

    # 左上角写日期和天气等文字
    draw.text((5, 5), f"今日日期：{date_str}", font=font, fill=(0, 0, 0))
    draw.text((300, 5), f"今日天气：{weather_str}", font=font, fill=(0, 0, 0))
    draw.text((600, 5), "今日新闻,你登报了！", font=font, fill=(0, 0, 0))

    template.save(output_path)
    print(f"报纸图片已生成：{output_path}")
    return output_path
