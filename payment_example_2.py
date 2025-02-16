import flask
import requests
import json
import hmac
import hashlib
import os
import random
import time
import requests

SERVER_SECRET_KEY = "my_secret_key99"  # only touch if using self hosted

MERCHANT_SERVER_SECRET_KEY = str(os.urandom(20))   # you can use a static token if you wish to acess the payments after restart

MERCHANT = "Example"   

SERVER = "https://fakepay.mooo.com"




app=flask.Flask("example_app")

transactions={}

def create_signature(data):
    """HMAC-SHA256 aláírás létrehozása"""
    message = json.dumps(data, separators=(",", ":"))
    signature = hmac.new(SERVER_SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature

def start_payment(email,name,amount,orderid):
    transaction_id=random.randint(1000000000,9999999999)
    data = {
    "merchant": MERCHANT,   # company name
    "orderRef": transaction_id,   # more then 6 digit numric uniqe id for the transaction
    "customerEmail": email,
    "customerName": name,
    "language": "EN",
    "currency": "USD",
    "total": amount,
    "timeout": 60*5,     # 5 minutes should be enaugh
    "methods": ["CARD"], 
    "url": {   # redirect urls     
        "success": f"http://localhost:5000/callback/{orderid}/success",
        "fail": f"http://localhost:5000/callback/{orderid}/fail",
        "cancel": f"http://localhost:5000/callback/{orderid}/cancel",
    },
    "merchant_secret": MERCHANT_SERVER_SECRET_KEY
    }

    signature = create_signature(data)
    headers = {"Signature": signature, "Content-Type": "application/json"}
    response = requests.post(f"{SERVER}/api/payment/order/make", json=data, headers=headers)
    
    transactions[orderid] = transaction_id    

    json= response.json()
    return json.get("success","/error").get("url","/error")


def answer(orderid):
    transaction_id=transactions.get(int(orderid))
    if transaction_id is None:
        return "Transaction not found"
    
    data={"merchant":MERCHANT,"transactionid":transaction_id,"merchant_secret":MERCHANT_SERVER_SECRET_KEY}
    signature = create_signature(data)
    headers = {"Signature": signature, "Content-Type": "application/json"}
    response = requests.post(f"{SERVER}/api/payment/order/status", json=data, headers=headers)
    return response.text




@app.route("/")
def index():
    return flask.render_template("example/index.html")

@app.route("/start_payment")
def start_payment_page():
    name=flask.request.args.get("name","guest")
    email=flask.request.args.get("email","guest@pincer.com")
    amount=int(flask.request.args.get("amount",0))
    order_id=random.randint(100,999)
    return start_payment(email,name,amount,order_id)




@app.route("/callback/<orderid>/success")
def callback_success(orderid):
    return answer(orderid)
@app.route("/callback/<orderid>/fail")
def callback_fail(orderid):
    return answer(orderid)
@app.route("/callback/<orderid>/cancel")
def callback_cancel(orderid):
    return answer(orderid)

if __name__ == "__main__":
    app.run()
