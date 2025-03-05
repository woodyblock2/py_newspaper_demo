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
        self.btn_capture = tk.Button(self.root, text="拍照", command=self.on_capture)
        self.btn_capture.place(x=400, y=10, width=80, height=30)

        self.btn_print = tk.Button(self.root, text="打印", command=self.on_print)
        self.btn_print.place(x=500, y=10, width=80, height=30)

        # 初始时，“打印”按钮禁用
        self.btn_print["state"] = "disabled"
        # 天气信息（可提前获取并显示）
        self.weather_str = get_weather_info()
        # 这里简单地在窗口标题栏显示天气，可自行修改
        self.root.title(f"今日登报 - 天气：{self.weather_str}")

        # 是否冻结画面
        self.is_freeze = False
        # 倒计时秒数，如果大于0则表示正在倒计时
        self.countdown_value = 0

        # 用于保存拍摄时的画面
        self.captured_frame = None

        # 启动循环更新摄像头画面
        self.update_frame()

    def update_frame(self):
        """
        实时更新摄像头画面 / 处理倒计时逻辑。
        """
        # 如果处于冻结状态，不再从摄像头读取新帧，而是一直显示 self.captured_frame
        if self.is_freeze and self.captured_frame is not None:
            # 把 captured_frame (BGR->RGB) 转成 Tk
            frame_rgb = cv2.cvtColor(self.captured_frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (self.cam_width, self.cam_height))
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.cam_label.imgtk = imgtk
            self.cam_label.configure(image=imgtk)
        else:
            # 正常读取摄像头画面
            ret, frame = self.cap.read()
            if ret:
                # 如果在倒计时中，就在画面上叠加倒计时数字
                if self.countdown_value > 0:
                    text = str(self.countdown_value)
                    # 在画面上写倒计时数字（OpenCV方式）
                    cv2.putText(frame, text, 
                                (int(self.cam_width/2 - 20), int(self.cam_height/2)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 
                                2, (0, 0, 255), 5)

                # 显示到 cam_label
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_rgb = cv2.resize(frame_rgb, (self.cam_width, self.cam_height))
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.cam_label.imgtk = imgtk
                self.cam_label.configure(image=imgtk)

        # 递归调用自己
        self.root.after(50, self.update_frame)

    def on_capture(self):
        """
        点击“拍照”按钮：开始 3 秒倒计时。
        """
        # # 如果已经在冻结状态，或正在倒计时中，就忽略
        # if self.is_freeze or self.countdown_value > 0:
        #     return

        self.is_freeze = False

        # 先将“打印”按钮置为禁用
        self.btn_print.configure(state="disabled")
        # 同时“拍照”按钮也禁用
        self.btn_capture.configure(state="disabled")

        # 设置倒计时起始数值
        self.countdown_value = 3
        self.update_countdown()

    def update_countdown(self):
        """
        每秒更新一次倒计时显示
        """
        if self.countdown_value > 0:
            self.countdown_value -= 1
            self.root.after(1000, self.update_countdown)
        else:
            # 倒计时结束，执行拍照并冻结画面
            self.capture_and_freeze()

    def capture_and_freeze(self):
        """
        倒计时结束后，拍照并冻结当前画面
        """
        ret, frame = self.cap.read()
        if ret:
            # 保存当前帧到内存
            self.captured_frame = frame
            # 也可以先行保存到文件
            cv2.imwrite("captured.jpg", frame)
            print("拍照完成，已保存到 captured.jpg")

            # 冻结画面
            self.is_freeze = True

            # 启用“打印”按钮
            self.btn_print.configure(state="normal")
            # 同时“拍照”按钮也启用
            self.btn_capture.configure(state="normal")

    def on_print(self):
        """
        点击“打印”按钮，只有在冻结状态下才可点击。
        - 生成报纸图
        - 调用打印或保存
        - 恢复摄像头动态捕捉
        """
        if not self.is_freeze:
            return

        # 先把冻结画面保存一下（也可用上面拍照时保存的 captured.jpg）
        photo_path = "captured.jpg"

        # 调用你的合成报纸图逻辑
        final_path = create_newspaper_image(photo_path, self.weather_str)
        print("最终报纸图片：", final_path)

        # TODO：此处可调用打印机逻辑
        print("正在调用打印机...")

        # 打印后一直处于静止状态
        # self.is_freeze = False
        self.btn_print.configure(state="disabled")  # 打印完立刻禁用


def main():
    root = tk.Tk()
    app = NewspaperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
