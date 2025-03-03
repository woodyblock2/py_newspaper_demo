# 导入cv2,request, PIL等库 以及 datetime
import cv2
import os
import json
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# 这个是天气API的URL和KEY，仅示例用
WEATHER_API_KEY = "key" # 高德地图，获取天气应用的Key
WEATHER_CITY = "210202"  # 大连市中山区编码

# 指定Template路径 resource文件夹下的newspaper_template.png
TEMPLATE_PATH = os.path.join("resource", "newspaper_template.png")
FONT_PATH = "/resource/msyh.ttc"  # 如果有自定义字体文件，就写路径，如 "fonts/msyh.ttf"
LOCAL_WEATHER_JSON = "resource/weather_result.json"

# 定义一个获取天气字符串的函数，给后面服用
def extract_weather_str(data_dict):
    """
    从接口或本地json数据中提取并拼接成 “晴 18℃” 形式
    """
    lives = data_dict.get("lives", [])
    if not lives:
        return "未知天气"
    weather_desc = lives[0].get("weather", "未知")
    temperature = lives[0].get("temperature","0")
    return f"{weather_desc} {temperature}℃"

# 定义一个函数，获取天气
def get_weather_info():
    """
    获取天气信息。
      1. 如果本地存在 weather_result.json，且其中的 reporttime 距离当前时间 <= 1小时，则直接使用本地数据
      2. 否则调用API获取最新数据，并写入到 weather_result.json
    返回格式: "霾 9°C" / "晴 25°C" 等
    """
    # 尝试读取本地的 weather_result.json
    local_data = None
    if os.path.exists(LOCAL_WEATHER_JSON):
        try:
            with open(LOCAL_WEATHER_JSON, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception as e:
            print("读取本地 weather_result.json 失败：", e)
            local_data = None

    # 如果有本地数据，检查 reporttime
    if local_data:
        try:
            lives_info = local_data["lives"][0]
            report_time_str = lives_info["reporttime"] # "2025-02-27 14:02:16"
            report_time = datetime.strptime(report_time_str, "%Y-%m-%d %H:%M:%S")

            # 如果没有超过一小时，则直接使用本地数据
            if datetime.now() - report_time <= timedelta(hours=1):
                print("本地天气数据未超过1小时，直接使用本地数据。")
                return extract_weather_str(local_data)
            else:
                print("本地天气数据超过1小时，调用API更新。")
        except Exception as e:
            print("解析本地天气数据时出现异常，调用API更新:", e)
    else:
        print("未找到本地 weather_result.json，调用API获取最新数据。")

    # 如果走到这里，说明本地数据不可用(超过一小时或解析异常)，开始请求API获取数据
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={WEATHER_CITY}&key={WEATHER_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # 为了兼容高德返回的数据, 一般会包含 "status", "info", "lives" 等
            # 确保至少有 data["lives"] 存在
            if data.get("status") == "1" and "lives" in data and len(data["lives"]) > 0:
                # 写入到本地文件
                with open(LOCAL_WEATHER_JSON, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                return extract_weather_str(data)
            else:
                print("API返回数据异常，无法从中提取有效天气信息:", data)
                # 如果需要, 可以选择返回一个默认天气
                return "晴 25°C"
        else:
            print("API请求失败，status_code:", response.status_code)
            return "晴 25°C"
    except Exception as e:
        print("请求天气API出现错误:", e)
        return "晴 25°C"

# 定义一个函数，使用cv打开摄像头，拍摄一张照片
def capture_photo():
    """
    使用cv2打开摄像头，按下'Space'或'Enter'拍摄一张照片并返回照片路径(或一个 PIL Image对象)
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头！")
        return None

    print("打开摄像头... 按<空格>拍照，按<Esc>退出。")

    photo_path = "captured.jpg"

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头画面")
            break

        # 显示画面
        cv2.imshow("Press SPACE to capture", frame)

        key = cv2.waitKey(1) & 0xFF
        # 如果按了SPACE或Enter
        if key == 32 or key == 13:
            # 保存照片
            cv2.imwrite(photo_path, frame)
            print(f"拍照完成，已保存到 {photo_path}")
            break
        elif key == 27: # ESC
            print("用户取消")
            photo_path = None
            break

    cap.release()
    cv2.destroyAllWindows()
    return photo_path

# 定义一个函数合成报纸图片
def create_newspaper_image(photo_path, weather_str, output_path="final_newspaper.png"):
    '''
    合成最终报纸图片
    '''
    # 打开报纸模板
    template = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(template)

    # 打开拍摄的照片
    user_photo = Image.open(photo_path).convert("RGB")

    # 调整照片大小，例如要放到模板正中间，站像素 500*600 像素
    user_photo = user_photo.resize((448,336))

    # 把照片贴到模板上(黏贴位置 可以调整)
    template.paste(user_photo, (210,250)) # (x, y) 为贴图左上角坐标

    # 设置字体
    if FONT_PATH:
        font = ImageFont.truetype(FONT_PATH, 15)
    else:
        font = ImageFont.load_default()

    # 获取当期日期
    now_date = datetime.now()
# 年月日手动组装
    date_str = f"{now_date.year}年{now_date.month}月{now_date.day}日"
    print("日期：", date_str)

    # 在模板上写上天气信息
    draw.text((5,5),f"今日日期：{date_str}", font=font, fill=(0,0,0))
    draw.text((300,5),f"今日天气：{weather_str}", font=font, fill=(0,0,0))

    # 也可以写一个大标题，小标题
    draw.text((600,5),"今日新闻,你登报了！", font=font, fill=(0,0,0))

    # 保存最终图片
    template.save(output_path)
    print(f"报纸图片已生成：{output_path}")
    return output_path

# 主函数
def main():
    # 1.获取天气信息
    weather_str = get_weather_info()
    print("天气信息：", weather_str)

    # 2.打开摄像头拍照
    photo_path = capture_photo()
    if not photo_path:
        print("未拍照，退出程序")
        return
    
    # 3.合成报纸图片
    final_path = create_newspaper_image(photo_path, weather_str)
    print("最终报纸图片：", final_path)

    # 4.（TODO）自动打印
    # （TODO）调用打印机API，打印 final_path

if __name__ == "__main__":
    main()
