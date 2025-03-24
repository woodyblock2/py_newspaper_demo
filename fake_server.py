# fake_server.py
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# 用一个全局字典来缓存订单状态
# orders[out_trade_no] = {
#   "data": {...下单时请求的JSON...},
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
        print(f"[MockServer] 订单 {out_trade_no} 模拟成功支付")
        orders[out_trade_no]["status"] = "SUCCESS"

@app.route("/v3/pay/transactions/native", methods=["POST"])
def mock_unified_order():
    """
    模拟微信支付 v3 Native 下单接口
    - 接收 JSON 信息
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
    print(f"[MockServer] 收到订单请求 out_trade_no={out_trade_no}，状态设置为 NOTPAY")

    # 返回一个模拟的 code_url，其中使用局域网 IP（注意：实际测试时需要确保手机能访问此 IP）
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
        "appid": order_info["data"].get("appid", "mock_appid"),
        "mchid": mchid or "mock_mchid",
        "out_trade_no": out_trade_no,
        "trade_state": status,
        "trade_state_desc": "模拟下单",
        "success_time": None
    }
    if status == "SUCCESS":
        resp["success_time"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    return jsonify(resp), 200

# 手动模拟支付成功（可选）
@app.route("/fakepay/<out_trade_no>", methods=["POST"])
def mock_pay_success(out_trade_no):
    """
    手动将订单状态置为 SUCCESS
      curl -X POST http://127.0.0.1:8000/fakepay/xxx
    """
    if out_trade_no not in orders:
        return jsonify({"error": "order not found"}), 404
    orders[out_trade_no]["status"] = "SUCCESS"
    print(f"[MockServer] 手动将订单 {out_trade_no} 状态置为 SUCCESS")
    return jsonify({"message": "ok"}), 200

@app.route("/simulate_payment/<out_trade_no>", methods=["GET", "POST"])
def simulate_payment(out_trade_no):
    """
    模拟支付页面：
    GET：显示支付模拟页面
    POST：根据用户选择更新订单状态
    """
    if request.method == "GET":
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>模拟支付</title>
        </head>
        <body>
            <h2>订单号: {out_trade_no}</h2>
            <form action="/simulate_payment/{out_trade_no}" method="post">
                <button name="action" value="success" type="submit">完成支付</button>
                <button name="action" value="fail" type="submit">放弃支付</button>
            </form>
        </body>
        </html>
        '''
        return html
    else:
        action = request.form.get("action")
        if out_trade_no not in orders:
            return jsonify({"error": "order not found"}), 404
        if action == "success":
            orders[out_trade_no]["status"] = "SUCCESS"
            print(f"[MockServer] 模拟支付：订单 {out_trade_no} 已支付成功")
            return f"订单 {out_trade_no} 已支付成功"
        else:
            orders[out_trade_no]["status"] = "CLOSED"
            print(f"[MockServer] 模拟支付：订单 {out_trade_no} 已取消支付")
            return f"订单 {out_trade_no} 已取消支付"

@app.route("/order_list", methods=["GET"])
def order_list():
    """
    显示订单列表页面，每一行显示订单号、状态，
    并提供“确认支付”和“放弃支付”两个按钮。
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>订单列表</title>
        <style>
            table { border-collapse: collapse; width: 80%; margin: 20px auto; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            button { margin: 0 5px; }
        </style>
    </head>
    <body>
        <h2 style="text-align:center;">订单列表</h2>
        <table>
            <tr>
                <th>订单号</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
    """
    for out_trade_no, order in orders.items():
        status = order.get("status", "未知")
        html += f"""
            <tr>
                <td>{out_trade_no}</td>
                <td>{status}</td>
                <td>
                    <form style="display:inline;" method="post" action="/update_order/{out_trade_no}">
                        <input type="hidden" name="action" value="confirm">
                        <button type="submit">确认支付</button>
                    </form>
                    <form style="display:inline;" method="post" action="/update_order/{out_trade_no}">
                        <input type="hidden" name="action" value="cancel">
                        <button type="submit">放弃支付</button>
                    </form>
                </td>
            </tr>
        """
    html += """
        </table>
    </body>
    </html>
    """
    return html

@app.route("/update_order/<out_trade_no>", methods=["POST"])
def update_order(out_trade_no):
    """
    根据表单提交的操作，更新指定订单的状态：
    - action=confirm 将订单状态更新为 SUCCESS
    - action=cancel  将订单状态更新为 CLOSED
    """
    action = request.form.get("action")
    if out_trade_no not in orders:
        return f"订单 {out_trade_no} 不存在", 404

    if action == "confirm":
        orders[out_trade_no]["status"] = "SUCCESS"
        print(f"[MockServer] 订单 {out_trade_no} 确认支付成功")
        message = f"订单 {out_trade_no} 已确认支付成功"
    elif action == "cancel":
        orders[out_trade_no]["status"] = "CLOSED"
        print(f"[MockServer] 订单 {out_trade_no} 已取消支付")
        message = f"订单 {out_trade_no} 已取消支付"
    else:
        message = "未知操作"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>更新订单状态</title>
    </head>
    <body>
        <p>{message}</p>
        <p><a href="/order_list">返回订单列表</a></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    # 本地运行时监听 127.0.0.1:8000
    app.run(host="127.0.0.1", port=8000, debug=True)
    print("http://127.0.0.1:8000/order_list")
