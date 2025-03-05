import tkinter as tk
import cv2
import PIL
from PIL import Image, ImageTk
import os
import json
import requests
from datetime import datetime, timedelta
from PIL import ImageDraw, ImageFont

# ========== 以下是你已有的一些方法，可直接拷贝过来使用 ========== #
WEATHER_API_KEY = "key" # 你的高德地图天气API Key
WEATHER_CITY = "210202"
LOCAL_WEATHER_JSON = "resource/weather_result.json"

TEMPLATE_PATH = "resource/newspaper_template.png"
FONT_PATH = "resource/msyh.ttc"  # 如果有别的路径，请自行改写

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

def get_weather_info():
    """
    获取天气信息，逻辑与之前相同
    """
    local_data = None
    if os.path.exists(LOCAL_WEATHER_JSON):
        try:
            with open(LOCAL_WEATHER_JSON, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception as e:
            print("读取本地 weather_result.json 失败：", e)
            local_data = None

    if local_data:
        try:
            lives_info = local_data["lives"][0]
            report_time_str = lives_info["reporttime"]  # "2025-02-27 14:02:16"
            report_time = datetime.strptime(report_time_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - report_time <= timedelta(hours=1):
                print("本地天气数据未超过1小时，直接使用本地数据。")
                return extract_weather_str(local_data)
            else:
                print("本地天气数据超过1小时，调用API更新。")
        except Exception as e:
            print("解析本地天气数据时出现异常，调用API更新:", e)
    else:
        print("未找到本地 weather_result.json，调用API获取最新数据。")

    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={WEATHER_CITY}&key={WEATHER_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "1" and "lives" in data and len(data["lives"]) > 0:
                with open(LOCAL_WEATHER_JSON, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return extract_weather_str(data)
            else:
                print("API返回数据异常，无法提取有效天气信息:", data)
                return "晴 25℃"
        else:
            print("API请求失败，status_code:", response.status_code)
            return "晴 25℃"
    except Exception as e:
        print("请求天气API出现错误:", e)
        return "晴 25℃"

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
# ========== 以上是已有方法 ========== #


class NewspaperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("今日登报 Demo")

        # 窗口大小可根据模板大小来定
        self.WIN_WIDTH = 876
        self.WIN_HEIGHT = 1072
        # 或者根据模板图实际大小，这里先写死
        self.root.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}")

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("无法打开摄像头！")
            # 也可以弹个提示后退出
            return

        # 读取模板图并转换成Tkinter可用的图像
        self.background_image = Image.open(TEMPLATE_PATH).convert("RGB")
        self.bg_tk = ImageTk.PhotoImage(self.background_image)

        # 用 Label 来承载整个背景图
        self.bg_label = tk.Label(self.root, image=self.bg_tk)
        self.bg_label.place(x=0, y=0, width=self.WIN_WIDTH, height=self.WIN_HEIGHT)

        # 摄像头在模板中的“照片区域”大小（根据你的需求设置）
        self.cam_width = 448
        self.cam_height = 336
        # 摄像头在背景中的位置（即贴图位置）
        self.cam_pos_x = 210
        self.cam_pos_y = 250

        # 在背景上叠加一个 Label，用来显示摄像头实时画面
        self.cam_label = tk.Label(self.bg_label)
        self.cam_label.place(x=self.cam_pos_x, y=self.cam_pos_y, width=self.cam_width, height=self.cam_height)

        # 定义两个按钮——“拍照”、“退出”
        self.btn_capture = tk.Button(self.root, text="拍照", command=self.capture_photo)
        self.btn_capture.place(x=400, y=10, width=80, height=30)

        self.btn_exit = tk.Button(self.root, text="退出", command=self.exit_app)
        self.btn_exit.place(x=500, y=10, width=80, height=30)

        # 天气信息（可提前获取并显示）
        self.weather_str = get_weather_info()
        # 这里简单地在窗口标题栏显示天气，可自行修改
        self.root.title(f"今日登报 - 天气：{self.weather_str}")

        # 启动循环更新摄像头画面
        self.update_frame()

    def update_frame(self):
        """
        从摄像头读取一帧，转换后显示到 cam_label 上
        """
        ret, frame = self.cap.read()
        if ret:
            # 转为 RGB 并resize到指定尺寸
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (self.cam_width, self.cam_height))
            # 转为 Pillow 图像
            img = Image.fromarray(frame)
            # 转为 Tkinter 可显示的图像
            imgtk = ImageTk.PhotoImage(image=img)
            # 显示到 cam_label
            self.cam_label.imgtk = imgtk
            self.cam_label.configure(image=imgtk)

        # after(延迟毫秒数, 函数)——递归调用自己，实现实时刷新
        self.root.after(30, self.update_frame)

    def capture_photo(self):
        """
        拍照函数：保存当前帧为文件，然后调用create_newspaper_image()
        """
        ret, frame = self.cap.read()
        if ret:
            # 保存当前帧
            photo_path = "captured.jpg"
            cv2.imwrite(photo_path, frame)
            print(f"拍照成功, 保存到 {photo_path}")
            
            # 生成报纸图片
            final_path = create_newspaper_image(photo_path, self.weather_str)
            print("最终报纸图片：", final_path)
            # 可以在这里弹窗提示用户，或者直接弹出一个新窗口显示 final_path

    def exit_app(self):
        """
        退出应用
        """
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = NewspaperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
