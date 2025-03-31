import tkinter as tk
import cv2
import time
import qrcode
from PIL import Image, ImageTk
from datetime import datetime
from weather_utils import get_weather_info
from image_utils import create_newspaper_image, load_template_config
from pay_v3 import native_unified_order, native_query_order, native_close_order

class NewspaperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("今日登报 Demo")
            # 读取模板位置信息
        template_config = load_template_config("template1")
        TEMPLATE_PATH = template_config["path"]
        TEMPLATE_WIN_WIDTH = template_config["win_width"]
        TEMPLATE_WIN_HEIGHT = template_config["win_height"]
        TEMPLATE_CAM_WIDTH = template_config["cam_width"]
        TEMPLATE_CAM_HEIGHT = template_config["cam_height"]
        TEMPLATE_POS_X = template_config["cam_pos_x"]
        TEMPLATE_POS_Y = template_config["cam_pos_y"]

        # 根据模板图设置窗口大小
        self.WIN_WIDTH = TEMPLATE_WIN_WIDTH
        self.WIN_HEIGHT = TEMPLATE_WIN_HEIGHT
        self.root.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}")

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[MainGUI] 无法打开摄像头！")
            return

        # 读取模板图并转换为 Tkinter 图片
        self.background_image = cv2.cvtColor(cv2.imread(TEMPLATE_PATH), cv2.COLOR_BGR2RGB)
        self.bg_img = Image.fromarray(self.background_image)
        self.bg_tk = ImageTk.PhotoImage(self.bg_img)

        # 用 Label 展示背景图
        self.bg_label = tk.Label(self.root, image=self.bg_tk)
        self.bg_label.place(x=0, y=0, width=self.WIN_WIDTH, height=self.WIN_HEIGHT)

        # 摄像头预览区域尺寸及位置（根据模板确定）
        self.cam_width = TEMPLATE_CAM_WIDTH
        self.cam_height = TEMPLATE_CAM_HEIGHT
        self.cam_pos_x = TEMPLATE_POS_X
        self.cam_pos_y = TEMPLATE_POS_Y

        # 在背景上叠加一个 Label 用于显示摄像头实时画面
        self.cam_label = tk.Label(self.bg_label)
        self.cam_label.place(x=self.cam_pos_x, y=self.cam_pos_y, width=self.cam_width, height=self.cam_height)

        # 按钮 “支付”
        self.btn_pay = tk.Button(self.root, text="支付", command=self.on_pay)
        self.btn_pay.place(x=330, y=10, width=80, height=30)
        # 按钮 “重拍”
        self.btn_capture = tk.Button(self.root, text="重拍", command=self.on_capture)
        self.btn_capture.place(x=450, y=10, width=80, height=30)
        # 按钮 “打印”
        self.btn_print = tk.Button(self.root, text="打印", command=self.on_print)
        self.btn_print.place(x=570, y=10, width=80, height=30)

        # 初始状态：仅“支付”按钮可用，其它禁用
        self.btn_capture["state"] = "disabled"
        self.btn_print["state"] = "disabled"

        # 获取天气信息并更新窗口标题
        self.weather_str = get_weather_info()
        self.root.title(f"今日登报 - 天气：{self.weather_str}")

        # 摄像头预览冻结状态及倒计时设置
        self.is_freeze = False
        self.countdown_value = 0
        self.captured_frame = None

        # 二维码显示 Label（调整为窗口中心显示）
        self.qr_label = tk.Label(self.root)
        qr_x = (self.WIN_WIDTH - 350) // 2
        qr_y = (self.WIN_HEIGHT - 350) // 2
        self.qr_label.place(x=qr_x, y=qr_y, width=350, height=350)
        self.qr_label.place_forget() # 暂时隐藏

        # 订单相关信息
        self.current_trade_no = None
        self.is_polling = False

        # 启动摄像头画面更新循环
        self.update_frame()

    def update_frame(self):
        """
        实时更新摄像头画面，并处理倒计时显示
        """
        if self.is_freeze and self.captured_frame is not None:
            frame_rgb = cv2.cvtColor(self.captured_frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (self.cam_width, self.cam_height))
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.cam_label.imgtk = imgtk
            self.cam_label.configure(image=imgtk)
        else:
            ret, frame = self.cap.read()
            if ret:
                if self.countdown_value > 0:
                    text = str(self.countdown_value)
                    cv2.putText(frame, text, 
                                (int(self.cam_width/2 - 20), int(self.cam_height/2)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_rgb = cv2.resize(frame_rgb, (self.cam_width, self.cam_height))
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.cam_label.imgtk = imgtk
                self.cam_label.configure(image=imgtk)
        self.root.after(50, self.update_frame)

    def on_pay(self):
        """
        点击“支付”按钮：
        1. 生成订单号，调用 Native 下单接口，生成支付二维码
        2. 显示二维码，并开始轮询订单状态
        """
        self.pay_countdown_value = 29 # 支付倒计时秒数
        self.is_polling = False
        self.current_trade_no = datetime.now().strftime("%Y%m%d%H%M%S") + str(int(time.time()))
        print(f"[MainGUI] 生成订单号：{self.current_trade_no}")
        self.pay_start_time = time.time()  # 记录开始支付的时间

        code_url = native_unified_order(out_trade_no=self.current_trade_no,
                                        total_fee=10,
                                        description="友好广场大头贴测试")
        if not code_url:
            print("[MainGUI] 下单失败，无法生成二维码")
            return

        # 生成二维码
        qr_img = qrcode.make(code_url)
        qr_img.save("pay_qr.png")
        print("[MainGUI] 二维码已生成并保存到 pay_qr.png")
        qr_tk = ImageTk.PhotoImage(qr_img)
        self.qr_label.config(image=qr_tk)
        self.qr_label.image = qr_tk
        # 显示二维码 Label（重新放置到界面上）
        qr_x = (self.WIN_WIDTH - 350) // 2
        qr_y = (self.WIN_HEIGHT - 350) // 2
        self.qr_label.place(x=qr_x, y=qr_y, width=350, height=350)


        # 开始轮询订单状态
        self.is_polling = True
        self.poll_payment_status()
        self.update_pay_countdown()


    def poll_payment_status(self):
        """
        轮询查询订单状态，检测是否支付成功或超时
        """
        if not self.is_polling:
            return

        # 检查是否超过30秒
        if time.time() - self.pay_start_time > 30: # 支付倒计时秒数
            print("[MainGUI] 支付超时，调用关闭订单接口")
            ret = native_close_order(self.current_trade_no)
            if ret: 
                print("[MainGUI] 订单关闭成功")
            else:
                print("[MainGUI] 订单关闭失败")
            # 清除二维码显示
            self.qr_label.place_forget()
            # 恢复初始状态：仅“支付”按钮可点击
            self.btn_pay.configure(state="normal")
            self.btn_capture.configure(state="disabled")
            self.btn_print.configure(state="disabled")
            self.is_polling = False
            # 如果pay_qr.png存在，则删除pay_qr.png TODO
            return

        # 继续轮询查询订单状态
        state = native_query_order(self.current_trade_no)
        print(f"[MainGUI] 轮询订单状态：{state}")
        if state == "SUCCESS":
            print("[MainGUI] 用户支付成功！")
            self.is_polling = False
            self.qr_label.place_forget()  # 支付成功后隐藏二维码区域
            self.auto_capture_after_payment()
            self.btn_pay.configure(state="disabled")
            self.btn_capture.configure(state="normal")
        elif state in ["NOTPAY", "USERPAYING", None]:
            self.root.after(2000, self.poll_payment_status)
        else:
            print(f"[MainGUI] 订单状态：{state}，停止轮询")
            self.is_polling = False


    def auto_capture_after_payment(self):
        """
        订单支付成功，自动拍照
        """
        print("[MainGUI] 3秒后自动拍照！")
        self.countdown_value = 3
        self.btn_capture.configure(state="disabled")
        self.btn_print.configure(state="disabled")
        self.is_freeze = False
        self.update_countdown()

    def on_capture(self):
        """
        点击“重拍”按钮，开始 3 秒倒计时
        """
        print(f"测试输出 self.is_freeze: {self.is_freeze}")
        print(f"测试输出 self.countdown_value: {self.countdown_value}")
        # if self.is_freeze or self.countdown_value > 0:
        #     return
        self.is_freeze = False
        self.btn_print.configure(state="disabled")
        self.btn_capture.configure(state="disabled")
        self.countdown_value = 3
        self.update_countdown()

    def update_countdown(self):
        """
        每秒更新一次倒计时显示，倒计时结束后拍照并冻结画面
        """
        if self.countdown_value > 0:
            print(f"[MainGUI] 倒计时：{self.countdown_value} 秒")
            self.countdown_value -= 1
            self.root.after(1000, self.update_countdown)
        else:
            self.capture_and_freeze()


    def update_pay_countdown(self):
        """
        每秒更新一次倒计时，用来记录支付倒计时
        """
        if self.pay_countdown_value > 0:
            print(f"[MainGUI] 倒计时：{self.pay_countdown_value} 秒")
            self.pay_countdown_value -= 1
            self.root.after(1000, self.update_pay_countdown)
        else:
            return


    def capture_and_freeze(self):
        """
        倒计时结束后拍照并冻结当前画面
        """
        ret, frame = self.cap.read()
        if ret:
            self.captured_frame = frame
            cv2.imwrite("captured.jpg", frame)
            print("[MainGUI] 拍照完成，已保存到 captured.jpg")
            self.is_freeze = True
            self.btn_print.configure(state="normal")
            self.btn_capture.configure(state="normal")

    def on_print(self):
        """
        点击“打印”按钮（冻结状态下可点击）：
        1. 合成报纸图
        2. 调用打印逻辑（此处仅模拟）
        3. 恢复初始状态
        """
        if not self.is_freeze:
            return
        photo_path = "captured.jpg"
        final_path = create_newspaper_image(photo_path, self.weather_str)
        print(f"[MainGUI] 最终报纸图片已生成：{final_path}")
        print("[MainGUI] 正在调用打印机...（模拟打印）")
        # 恢复初始状态：启用“支付”，禁用“重拍”和“打印”
        self.btn_pay.configure(state="normal")
        self.btn_capture.configure(state="disabled")
        self.btn_print.configure(state="disabled")
        # 恢复摄像头实时预览
        self.is_freeze = False

def main():
    root = tk.Tk()
    app = NewspaperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
