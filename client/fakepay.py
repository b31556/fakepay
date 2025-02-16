import json
import hmac
import hashlib
import random
import requests
import os

SERVER_SECRET_KEY="my_secret_key99" # only cahange if self hosted

MERCHANT_SECRET_KEY=str(os.urandom(21))  # use a static if you wanna acess payments after restart

MERCHANT="Example"  # set this to your comapy or project name

SERVER = "http://nationscity:5001"  # only change if self hosted


transactions={}
def create_signature(data):
    """inner function"""
    message = json.dumps(data, separators=(",", ":"))
    signature = hmac.new(SERVER_SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature

def start_payment(email,name,amount,orderid,secess_redirect_url,fail_redirect_url,cancel_redirect_url,merchant=MERCHANT,lang="EN",currency="USD"):
    """starts a payment and returns the url to send the user to"""
    transaction_id=random.randint(1000000000,9999999999)
    data = {
    "merchant": merchant,   # company name
    "orderRef": transaction_id,   # more then 6 digit numric uniqe id for the transaction
    "customerEmail": email,
    "customerName": name,
    "language": "EN",
    "currency": "USD",
    "total": amount,
    "timeout": 60*5,     # 5 minutes should be enaugh
    "methods": ["CARD"], 
    "url": {   # redirect urls     
        "success":secess_redirect_url,
        "fail": fail_redirect_url,
        "cancel": cancel_redirect_url
    },
    "merchant_secret": MERCHANT_SECRET_KEY
    }

    signature = create_signature(data)
    headers = {"Signature": signature, "Content-Type": "application/json"}
    response = requests.post(f"{SERVER}/api/payment/order/make", json=data, headers=headers)
    
    transactions[orderid] = transaction_id    

    json= response.json()
    return json.get("success","/error").get("url","/error")

def getstatus(orderid,merchant=MERCHANT):
    """retrives the satus of a transaction
    Args:
    - orderid: int  orderid
    
    return str status, one of the following success, fail, cancel, notfound"""
    transaction_id=transactions.get(int(orderid))
    if transaction_id is None:
        return "Transaction not found"
    
    data={"merchant":merchant,"transactionid":transaction_id,"merchant_secret":MERCHANT_SECRET_KEY}
    signature = create_signature(data)
    headers = {"Signature": signature, "Content-Type": "application/json"}
    response = requests.post(f"{SERVER}/api/payment/order/status", json=data, headers=headers)
    return response.text if not "{" in response.text else "notfound"