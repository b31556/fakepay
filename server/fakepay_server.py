import flask
from flask import request, jsonify
import json
import hmac
import hashlib
import random
import os
import time

SECRET_KEY = "my_secret_key99"

DOMAIN = "fakepay.mooo.com"

USE_HTTPS = True  # True is strongly recommended, only use False for development

app = flask.Flask("fakepay")

current_payments=[]


class Payment:
    def __init__(self, amount, currency, payment_method, order_id, merchant, timeout, email, name, lang, urls, merchant_secret):
        self.amount = amount
        self.currency = currency
        self.payment_method = payment_method
        self.order_id = order_id
        self.innerid = random.randint(1000000,9999999)
        self.code = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(21))
        self.merchant=merchant
        self.timestamp = time.time()
        self.timeout=timeout
        self.email=email
        self.name=name
        self.lang=lang
        self.urls=urls
        self.merchant_secret = merchant_secret
        self._status="pending"

    def generateurl(self):
        return ("https://" if USE_HTTPS else "http://")+DOMAIN+"/pay/"+str(self.code)
    
    def render_html(self):
        if self.is_timedout():
            return flask.redirect(self.urls["fail"])
        return flask.render_template("payment.html", 
                                     amount=self.amount,
                                     currency=self.currency,
                                     payment_method=self.payment_method,
                                     order_id=self.order_id,
                                     merchant=self.merchant,
                                     timestamp=self.timestamp,
                                     email=self.email,
                                     name=self.name,
                                     lang=self.lang,
                                     urls=self.urls,
                                     code=self.code)
    
    def is_timedout(self):
        return time.time() - self.timestamp > self.timeout

    def status(self):
        if self._status=="done":
            return "done"
        if self.is_timedout():
            self._status="timedout"
            return "timedout"
        else:
            return self._status

    def done(self):
        self._status="done"
                                     

    

def verify_signature(data, signature):
    """Ellenőrzi az aláírást"""
    message = json.dumps(data, separators=(",", ":"))
    expected_signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

@app.route("/")
def rettogit():
    return flask.redirect("https://github.com/b31556/fakepay")


@app.route("/api/payment/order/status", methods=["POST"])
def payment_order_status():
    """Megjeleníti a fizetési státust"""
    data = flask.request.json
    signature = request.headers.get("Signature")

    if not signature or not verify_signature(data, signature):
        return jsonify({"error": "Érvénytelen"}), 403
    
    if "merchant" in data and "merchant_secret" in data and "transactionid" in data:
        for payment in current_payments:
            if payment.merchant == data["merchant"] and payment.order_id == data["transactionid"] and payment.merchant_secret == data["merchant_secret"]:
                return payment.status()
        return jsonify({"error": "Not found or unautorized"}), 404
    else:
        return jsonify({"error": "Missing datas"}), 400


@app.route("/api/payment/order/make", methods=["POST"])
def payment_order():
    data = request.json
    signature = request.headers.get("Signature")

    if not signature or not verify_signature(data, signature):
        return jsonify({"error": "Érvénytelen"}), 403
    
    if all(key in data for key in ["merchant_secret","total", "currency", "methods", "orderRef", "merchant", "timeout", "customerEmail", "customerName", "language", "url"]) and "fail" in data["url"] and "success" in data["url"] and "cancel" in data["url"]:
        
        


        payment = Payment(
        amount=data["total"],
        currency=data["currency"],
        payment_method=data["methods"][0],
        order_id=data["orderRef"],
        merchant=data["merchant"],
        timeout=data["timeout"],
        email=data["customerEmail"],
        name=data["customerName"],
        lang=data["language"],
        urls=data["url"],
        merchant_secret=data["merchant_secret"]
        
        )
        current_payments.append(payment)

        return jsonify({"success":{"url":payment.generateurl()}})

    else:
        return jsonify({"error": "Érvénytelen, missing datas"}), 400




@app.route("/pay/<code>")
def pay(code):
    for payment in current_payments:
        if payment.code == code:
            if payment.status=="success":
                return flask.redirect(payment.url["success"])
            if not payment.is_timedout():
                return payment.render_html()
            else:
                return flask.render_template("timeout.html",backlink=payment.urls["fail"], 
                                     amount=payment.amount,
                                     currency=payment.currency,
                                     payment_method=payment.payment_method,
                                     order_id=payment.order_id,
                                     merchant=payment.merchant,
                                     timestamp=payment.timestamp,
                                     email=payment.email,
                                     name=payment.name,
                                     lang=payment.lang,
                                     urls=payment.urls
                )
        
    return "404", 404

@app.route("/done_payment/<code>")
def done_payment(code):
    for payment in current_payments:
        if payment.code == code:
            if payment.status=="cancelled":
                return flask.redirect(payment.url["cancel"])
            if payment.status=="success":
                return flask.redirect(payment.url["success"])
            payment.done()

@app.route("/callback/canceled/<code>")
def callback_canceled(code):
    for payment in current_payments:
        if payment.code == code:
            if payment.status=="cancelled":
                return flask.redirect(payment.url["cancel"])
            if payment.status=="success":
                return flask.redirect(payment.url["success"])
            payment._status="cancelled"
            return flask.redirect(payment.urls["cancel"])

@app.route("/callback/confirmed/<code>")
def callback_confirmed(code):
    for payment in current_payments:
        if payment.code == code:
            if payment.status=="cancelled":
                return flask.redirect(payment.url["cancel"])
            if payment.status=="success":
                return flask.redirect(payment.url["success"])
            if payment.is_timedout():
                return flask.render_template("timeout.html",backlink=payment.urls["fail"], 
                                     amount=payment.amount,
                                     currency=payment.currency,
                                     payment_method=payment.payment_method,
                                     order_id=payment.order_id,
                                     merchant=payment.merchant,
                                     timestamp=payment.timestamp,
                                     email=payment.email,
                                     name=payment.name,
                                     lang=payment.lang,
                                     urls=payment.urls)
            payment._status="success"
            return flask.render_template("loading.html",redirecturl=payment.urls["success"],lang=payment.lang)


 
if __name__=="__main__":
    app.run("0.0.0.0",5001,debug=True,use_reloader=False)

