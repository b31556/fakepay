import flask
from flask import request, jsonify
import json
import hmac
import hashlib
import random
import time
import threading

SECRET_KEY = "my_secret_key99"
DOMAIN = "fakepay.mooo.com"
USE_HTTPS = True  # seriously, don't set this to False outside localhost

app = flask.Flask("fakepay")

# GLOBAL PAYMENT STORE + LOCK
current_payments = []
payments_lock = threading.Lock()


class Payment:
    def __init__(self, amount, currency, payment_method, order_id, merchant, timeout, email, name, lang, urls, merchant_secret):
        self.amount = amount
        self.currency = currency
        self.payment_method = payment_method
        self.order_id = order_id
        self.innerid = random.randint(1000000, 9999999)
        self.code = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(21))
        self.merchant = merchant
        self.timestamp = time.time()
        self.timeout = timeout
        self.email = email
        self.name = name
        self.lang = lang
        self.urls = urls
        self.merchant_secret = merchant_secret
        self._status = "pending"

    def generateurl(self):
        return ("https://" if USE_HTTPS else "http://") + DOMAIN + "/pay/" + str(self.code)

    def render_html(self):
        if self.is_timedout():
            return flask.redirect(self.urls["fail"])
        return flask.render_template("payment.html", **self.__dict__)

    def is_timedout(self):
        return time.time() - self.timestamp > self.timeout

    def status(self):
        if self._status == "done":
            return "done"
        if self.is_timedout():
            self._status = "timedout"
            return "timedout"
        return self._status

    def done(self):
        self._status = "done"


def verify_signature(data, signature):
    message = json.dumps(data, separators=(",", ":"))
    expected_signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


@app.route("/")
def rettogit():
    return flask.redirect("https://github.com/b31556/fakepay")


@app.route("/api/payment/order/status", methods=["POST"])
def payment_order_status():
    data = request.json
    signature = request.headers.get("Signature")

    if not signature or not verify_signature(data, signature):
        return jsonify({"error": "Érvénytelen"}), 403

    if {"merchant", "merchant_secret", "transactionid"} <= data.keys():
        with payments_lock:
            for payment in current_payments:
                if (
                    payment.merchant == data["merchant"]
                    and payment.order_id == data["transactionid"]
                    and payment.merchant_secret == data["merchant_secret"]
                ):
                    return jsonify({"status": payment.status()})
        return jsonify({"error": "Not found or unauthorized"}), 404

    return jsonify({"error": "Missing datas"}), 400


@app.route("/api/payment/order/make", methods=["POST"])
def payment_order():
    data = request.json
    signature = request.headers.get("Signature")

    if not signature or not verify_signature(data, signature):
        return jsonify({"error": "Érvénytelen"}), 403

    required_keys = ["merchant_secret", "total", "currency", "methods", "orderRef", "merchant",
                     "timeout", "customerEmail", "customerName", "language", "url"]
    if all(k in data for k in required_keys) and {"fail", "success", "cancel"} <= data["url"].keys():

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

        with payments_lock:
            current_payments.append(payment)

        return jsonify({"success": {"url": payment.generateurl()}})

    return jsonify({"error": "Érvénytelen, missing datas"}), 400


def find_payment(code):
    with payments_lock:
        for payment in current_payments:
            if payment.code == code:
                return payment
    return None


@app.route("/pay/<code>")
def pay(code):
    payment = find_payment(code)
    if not payment:
        return "404", 404

    if payment.status() == "success":
        return flask.redirect(payment.urls["success"])
    elif not payment.is_timedout():
        return payment.render_html()
    else:
        return flask.render_template("timeout.html", backlink=payment.urls["fail"], **payment.__dict__)


@app.route("/done_payment/<code>")
def done_payment(code):
    payment = find_payment(code)
    if not payment:
        return "404", 404
    if payment.status() == "cancelled":
        return flask.redirect(payment.urls["cancel"])
    if payment.status() == "success":
        return flask.redirect(payment.urls["success"])
    payment.done()
    return flask.redirect(payment.urls["success"])


@app.route("/callback/canceled/<code>")
def callback_canceled(code):
    payment = find_payment(code)
    if not payment:
        return "404", 404
    if payment.status() == "success":
        return flask.redirect(payment.urls["success"])
    payment._status = "cancelled"
    return flask.redirect(payment.urls["cancel"])


@app.route("/callback/confirmed/<code>")
def callback_confirmed(code):
    payment = find_payment(code)
    if not payment:
        return "404", 404
    if payment.status() == "cancelled":
        return flask.redirect(payment.urls["cancel"])
    if payment.status() == "success":
        return flask.redirect(payment.urls["success"])
    if payment.is_timedout():
        return flask.render_template("timeout.html", backlink=payment.urls["fail"], **payment.__dict__)
    payment._status = "success"
    return flask.render_template("loading.html", redirecturl=payment.urls["success"], lang=payment.lang)
