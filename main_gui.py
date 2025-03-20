import tkinter as tk
import cv2
import time
import qrcode
from PIL import Image, ImageTk
from datetime import datetime
from weather_utils import get_weather_info
from image_utils import create_newspaper_image, TEMPLATE_PATH
from pay_v3 import native_unified_order, native_query_order

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

        # 按鈕 “支付”
        self.btn_pay = tk.Button(self.root, text="支付", command=self.on_capture)
        self.btn_pay.place(x=330, y=10, width=80, height=30)
        # 按鈕 “拍照”
        self.btn_capture = tk.Button(self.root, text="拍照", command=self.on_capture)
        self.btn_capture.place(x=450, y=10, width=80, height=30)
        # 按鈕 “打印”
        self.btn_print = tk.Button(self.root, text="打印", command=self.on_print)
        self.btn_print.place(x=570, y=10, width=80, height=30)

        # 初始时，“拍照” “打印”按钮禁用
        self.btn_capture["state"] = "disabled"
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

        # 二维码Label
        self.qr_label = tk.Label(self.root)
        self.qr_label.place(x=650, y=50, width=200, height=200)
        # 订单相关
        self.current_trade_no = None
        self.is_polling = False

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

    def on_pay(self):
        """
        1。生成单号
        2. 调用 V3 native 下单
        3. 显示二维码
        4. 开始轮询订单状态
        """
        self.is_polling = False
        # 订单号
        self.current_trade_no = datetime.now().strftime("%Y%m%d%H%M%S")
        self.current_trade_no += str(int(time.time())) # 拼接时间戳

        # 下单
        code_url = native_unified_order(out_trade_no=self.current_trade_no,
                                        total_fee=9.9,
                                        description="报纸大头贴")
        if not code_url:
            print("下单失败，无法生成二维码")
            return
        
        # 生成二维码
        qr_img = qrcode.make(code_url)
        qr_img.save("pay_qr.png")
        # 显示到画面
        qr_tk = ImageTk.PhotoImage(qr_img)
        self.qr_label.config(image=qr_tk)
        self.qr_label.image = qr_tk

        # 开始轮询订单状态
        self.is_polling = True
        # self.po

    def poll_payment_status(self):
        """
        轮询订单状态
        """
        if not self.is_polling:
            return
        state = native_query_order(self.current_trade_no)
        if state == "SUCCESS":
            print("用户支付成功!")
            self.is_polling = False
            # 清除二维码
            self.qr_label.config(image=None)
            self.qr_label.image = None
            # 自动触发拍照
            self.auto_capture_after_payment()
        elif state in ["NOTPAY", "USERPAYING", None]:
            # 继续轮询
            self.root.after(2000, self.poll_payment_status)
        else:
            # 其他状态(CLOSED, PAYERROR等)
            print("订单状态:", state, "停止轮询")
            self.is_polling = False

    def auto_capture_after_payment(self):
        print("3秒后自动拍照!")
        self.countdown_value = 3
        self.btn_capture["state"] = "disabled"
        self.btn_print["state"] = "disabled"
        self.is_freeze = False
        self.update_countdown()

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
