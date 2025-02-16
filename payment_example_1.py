import requests
import json
import hmac
import hashlib
import os
import random
import time

SERVER_SECRET_KEY = "my_secret_key99"  # only touch if using self hosted

MERCHANT_SERVER_SECRET_KEY = str(os.urandom(20))   # you can use a static token if you wish to acess the payments after restart

def create_signature(data):
    """HMAC-SHA256 aláírás létrehozása"""
    message = json.dumps(data, separators=(",", ":"))
    signature = hmac.new(SERVER_SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature

def start_payment(email,name,amount,orderid):
    transaction_id=random.randint(1000000000,9999999999)
    data = {
    "merchant": "Pincer",   # company name
    "orderRef": transaction_id,   # more then 6 digit numric uniqe id for the transaction
    "customerEmail": email,
    "customerName": name,
    "language": "HU",
    "currency": "HUF",
    "total": amount,
    "timeout": 60*5,     # 5 minutes should be enaugh
    "methods": ["CARD"], 
    "url": {   # redirect urls     
        "success": f"http://127.0.0.1:8080/callback/{orderid}/success",
        "fail": f"http://127.0.0.1:8080/callback/{orderid}/fail",
        "cancel": f"http://127.0.0.1:8080/callback/{orderid}/cancel",
    },
    "merchant_secret": MERCHANT_SERVER_SECRET_KEY
    }

    signature = create_signature(data)
    headers = {"Signature": signature, "Content-Type": "application/json"}
    response = requests.post("http://127.0.0.1:5001/api/payment/order/make", json=data, headers=headers)
    
    print("Szerver válasza:", response.json())

    while True:
        data={
            "merchant": "Pincer",
            "transactionid": transaction_id,
            "merchant_secret" : MERCHANT_SERVER_SECRET_KEY
        }
        signature = create_signature(data)
        headers = {"Signature": signature, "Content-Type": "application/json"}
        try:
            response = requests.post(f"http://127.0.0.1:5001/api/payment/order/status", json=data, headers=headers)
            print(response.text)
        except:
            print("cant acess")
        
        time.sleep(1)

if __name__ == "__main__":
    start_payment("me@me.com","Example Tom",900.50,random.randint(10,99))
