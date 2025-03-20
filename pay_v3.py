# pay_v3.py

import time
import random
import string
import json
import uuid
from datetime import datetime
import requests
import base64
import hashlib

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# ========== 微信商户平台申请/配置好的信息 ========== #
WECHATPAY_MCHID = "商户号"
WECHATPAY_APPID = "AppID"
WECHATPAY_APIv3_KEY = "APIv3密钥"
# 商户私钥路径 (pem)
MERCHANT_PRIVATE_KEY_PATH = "resource/merchant_key.pem"
# 微信支付平台证书(公钥), 用于回调验签(这里仅做示例, 如果要验证回调签名需要)
WECHATPAY_CERT_PATH = "resource/wechatpay_cert.pem"
MOCK_HOST = "http://127.0.0.1:8000"
# ====================================================== #


def load_merchant_private_key(key_path):
    """
    加载商户私钥文件
    """
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )
    return private_key


def sign_with_rsa_sha256(private_key, message):
    """
    使用RSA-SHA256算法，用商户私钥对message进行签名
    """
    signature = private_key.sign(
        data=message.encode("utf-8"),
        padding=padding.PKCS1v15(),
        algorithm=hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")


def generate_authorization(method, url, body, mchid, serial_no, private_key):
    """
    生成 V3 接口所需的请求头 Authorization
    - method: "POST" / "GET" ...
    - url: 不含域名的path，比如 "/v3/pay/transactions/native"
    - body: 请求body (JSON字符串)，如果是GET可以是空""
    - mchid: 商户号
    - serial_no: 商户证书序列号(在商户平台可看到)
    - private_key: 商户私钥对象
    """
    timestamp = str(int(time.time()))
    nonce_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
    # 拼接待签名串
    message = "\n".join([method, url, timestamp, nonce_str, body]) + "\n"
    signature = sign_with_rsa_sha256(private_key, message)

    auth = f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",nonce_str="{nonce_str}",timestamp="{timestamp}",serial_no="{serial_no}",signature="{signature}"'
    return auth


def native_unified_order(out_trade_no, total_fee, description="大头贴"):
    """
    V3 Native下单接口: POST /v3/pay/transactions/native
    - out_trade_no: 商户订单号(确保唯一)
    - total_fee: 价格(单位: 分)
    - description: 商品描述
    return: code_url or None
    """
    # 1. 加载私钥、获取序列号(需要你自己从商户平台或pem证书中读取)
    private_key = load_merchant_private_key(MERCHANT_PRIVATE_KEY_PATH)
    # 序列号可通过openssl命令或后台查看，这里先写死做示例:
    merchant_cert_serial_no = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

    # url = "https://api.mch.weixin.qq.com/v3/pay/transactions/native"
    url = f"{MOCK_HOST}/v3/pay/transactions/native"

    # 2. 请求体 JSON
    amount_dict = {
        "total": total_fee,        # int类型: 单位分
        "currency": "CNY"
    }
    payer_dict = {
        # Native支付可能不需要传 payer 里的 openid, 但JSAPI要
    }
    data = {
        "mchid": WECHATPAY_MCHID,
        "appid": WECHATPAY_APPID,
        "description": description,
        "out_trade_no": out_trade_no,
        "notify_url": "https://www.example.com/wxpay/callback",  # 没有公网也要写
        "amount": amount_dict,
    }
    body_str = json.dumps(data, ensure_ascii=False)

    # 3. 准备请求头
    authorization = generate_authorization(
        method="POST",
        url="/v3/pay/transactions/native",
        body=body_str,
        mchid=WECHATPAY_MCHID,
        serial_no=merchant_cert_serial_no,
        private_key=private_key
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization
    }

    # 4. 发起请求
    try:
        resp = requests.post(url, headers=headers, data=body_str, timeout=10)
        if resp.status_code == 200 or resp.status_code == 201:
            resp_json = resp.json()
            # 返回中会包含 code_url
            return resp_json.get("code_url")
        else:
            print("下单接口返回非200:", resp.status_code, resp.text)
    except Exception as e:
        print("请求下单接口异常:", e)
    return None


def native_query_order(out_trade_no):
    """
    V3 查询订单: GET /v3/pay/transactions/out-trade-no/{out_trade_no}?mchid=xxx
    return: 订单状态trade_state, 可能是 SUCCESS, NOTPAY, etc.
    """
    private_key = load_merchant_private_key(MERCHANT_PRIVATE_KEY_PATH)
    merchant_cert_serial_no = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    
    # 1. 拼接URL:
    path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={WECHATPAY_MCHID}"
    url = "https://api.mch.weixin.qq.com" + path
    # mock 测试
    # path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid=1900000001"
    # url = MOCK_HOST + path

    # 2. 构造签名(GET请求body为空)
    authorization = generate_authorization(
        method="GET",
        url=path,
        body="",
        mchid=WECHATPAY_MCHID,
        serial_no=merchant_cert_serial_no,
        private_key=private_key
    )
    headers = {
        "Authorization": authorization
    }

    # 3. 发起GET请求
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            resp_json = resp.json()
            return resp_json.get("trade_state")  # SUCCESS, NOTPAY, ...
        else:
            print("查询订单接口返回:", resp.status_code, resp.text)
    except Exception as e:
        print("查询订单接口异常:", e)

    return None
