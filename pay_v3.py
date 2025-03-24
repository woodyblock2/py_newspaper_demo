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
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# ========== 微信商户平台申请/配置的信息 ==========
WECHATPAY_MCHID = "1900000001"
WECHATPAY_APPID = "mock_appid"
WECHATPAY_APIv3_KEY = "APIv3密钥"
# 商户私钥路径 (pem)
MERCHANT_PRIVATE_KEY_PATH = "resource/merchant_key.pem"
# 微信支付平台证书(公钥)（用于回调验签，示例中仅做演示）
WECHATPAY_CERT_PATH = "resource/wechatpay_cert.pem"
MOCK_HOST = "http://127.0.0.1:8000"
# ==================================================

def load_merchant_private_key(key_path):
    try:
        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
            )
        return private_key
    except FileNotFoundError:
        print("[PayV3] 未找到私钥文件，生成临时测试密钥")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        return private_key

def sign_with_rsa_sha256(private_key, message):
    """
    使用 RSA-SHA256 算法，用商户私钥对 message 进行签名
    """
    signature = private_key.sign(
        data=message.encode("utf-8"),
        padding=padding.PKCS1v15(),
        algorithm=hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")

def generate_authorization(method, url, body, mchid, serial_no, private_key):
    """
    生成 V3 接口请求头 Authorization
    """
    timestamp = str(int(time.time()))
    nonce_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
    message = "\n".join([method, url, timestamp, nonce_str, body]) + "\n"
    signature = sign_with_rsa_sha256(private_key, message)

    auth = f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",nonce_str="{nonce_str}",timestamp="{timestamp}",serial_no="{serial_no}",signature="{signature}"'
    return auth

def native_unified_order(out_trade_no, total_fee, description="大头贴"):
    """
    V3 Native 下单接口: POST /v3/pay/transactions/native
    """
    private_key = load_merchant_private_key(MERCHANT_PRIVATE_KEY_PATH)
    merchant_cert_serial_no = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    url = f"{MOCK_HOST}/v3/pay/transactions/native"

    amount_dict = {
        "total": total_fee,
        "currency": "CNY"
    }
    data = {
        "mchid": WECHATPAY_MCHID,
        "appid": WECHATPAY_APPID,
        "description": description,
        "out_trade_no": out_trade_no,
        "notify_url": "https://www.example.com/wxpay/callback",
        "amount": amount_dict,
    }
    body_str = json.dumps(data, ensure_ascii=False)

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

    try:
        resp = requests.post(url, headers=headers, data=body_str, timeout=10)
        if resp.status_code in [200, 201]:
            resp_json = resp.json()
            return resp_json.get("code_url")
        else:
            print("[PayV3] 下单接口返回非200:", resp.status_code, resp.text)
    except Exception as e:
        print("[PayV3] 请求下单接口异常:", e)
    return None

def native_query_order(out_trade_no):
    """
    V3 查询订单: GET /v3/pay/transactions/out-trade-no/{out_trade_no}?mchid=xxx
    """
    private_key = load_merchant_private_key(MERCHANT_PRIVATE_KEY_PATH)
    merchant_cert_serial_no = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={WECHATPAY_MCHID}"
    # url = "https://api.mch.weixin.qq.com" + path
    url = MOCK_HOST + path # TODO: 临时测试使用


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

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            resp_json = resp.json()
            return resp_json.get("trade_state")
        else:
            print("[PayV3] 查询订单接口返回:", resp.status_code, resp.text)
    except Exception as e:
        print("[PayV3] 查询订单接口异常:", e)
    return None
