# fake_server.py
import time
# import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# 暂时用一个全局字典来缓存订单状态
# orders[out_trade_no] = {
#   "data": {...下单是请求JSON...}
#   "status": "NOTPAY"
# }
orders = {}

def auto_set_success(out_trade_no, delay=0):
    """
    测试用：下单后自动模拟用户支付成功，
    等待 delay 秒后把订单状态设置为 SUCCESS
    """
    time.sleep(delay)
    if out_trade_no in orders and orders[out_trade_no]["status"] != "SUCCESS":
        print(f"[MockServer] 订单 {out_trade_no} 订单模拟成功支付")
        orders[out_trade_no]["status"] = "SUCCESS"

@app.route("/v3/pay/transactions/native", methods=["POST"])
def mock_unified_order():
    """
    模拟wechat pay v3 Native下单
    - 收到JSON信息
    - 返回 code_url
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "invalid request"}), 400
    
    out_trade_no = body.get("out_trade_no")
    if not out_trade_no:
        return jsonify({"error": "missing out_trade_no"}), 400
    
    # 缓存订单信息
    orders[out_trade_no] = {"data": body, "status": "NOTPAY"}
    print(f"[MockServer] 收到订单请求 out_trade_no={out_trade_no}, 订单已缓存 status=NOTPAY")

    # 返回一个模拟的code_url
    response_data = {
        "code_url": f"weixin://wxpay/bizpayurl?mock_pay={out_trade_no}"
    }
    return jsonify(response_data), 200

@app.route("/v3/pay/transactions/out-trade-no/<out_trade_no>", methods=["GET"])
def mock_query_order(out_trade_no):
    """
    模拟查询订单状态：
    GET /v3/pay/transactions/out-trade-no/<out_trade_no>?mchid=xxxx
    """
    mchid = request.args.get("mchid", None)
    if out_trade_no not in orders:
        return jsonify({"error": "order not found"}), 404
    
    order_info = orders[out_trade_no]
    status = order_info["status"]
    # 构造响应
    resp = {
        "appid": order_info["data"].get("appid","mock_appid"),
        "mchid": mchid or "mock_mchid",
        "out_trade_no": out_trade_no,
        "trade_state": status,
        "trade_state_desc": "模拟下单",
        "success_time": None
    }
    if status == "SUCCESS":
        resp["success_time"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    return jsonify(resp), 200

# 可选: 人工模拟支付成功
@app.route("/fakepay/<out_trade_no>", methods=["POST"])
def mock_pay_success(out_trade_no):
    """
    如果想手动模拟“用户点击支付”，可以调这个接口
      curl -X POST http://127.0.0.1:8000/fakepay/xxx
    把订单状态变成 SUCCESS
    """
    if out_trade_no not in orders:
        return jsonify({"error": "order not found"}), 404
    orders[out_trade_no]["status"] = "SUCCESS"
    print(f"[MockServer] 手动将订单 {out_trade_no} 状态置为 SUCCESS")
    return jsonify({"message": "ok"}), 200


# @app.route("/wxpay/callback", methods=["POST"])
# def wxpay_callback():
#     # 打印收到的回调体
#     body = request.get_json()
#     print("收到微信支付回调:", body)
#     # 实际上，这里需要做 v3 回调验签: 
#     # 1. 提取头部 Wechatpay-Signature, Wechatpay-Timestamp, Wechatpay-Nonce
#     # 2. 用wechatpay_cert.pem公钥校验签名
#     # 3. 解密加密资源(resource)获取订单信息
#     # 4. 校验订单号 / 金额 / 状态
#     # 5. 返回200 OK 并返回特定JSON
#     #
#     # 略...

#     # 返回成功
#     return jsonify({"code": "SUCCESS", "message": "成功"})

if __name__ == "__main__":
    # 本地跑
    app.run(host="127.0.0.1", port=8000, debug=True)
