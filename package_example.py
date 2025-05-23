import flask
import os
import random

from fakepay import start_payment, getstatus


MERCHANT = "Example"   


app=flask.Flask("example_app")


def answer(orderid):
    return getstatus(orderid, MERCHANT)


@app.route("/start_payment")
def start_payment_page():
    name=flask.request.args.get("name","guest")
    email=flask.request.args.get("email","guest@pincer.com")
    amount=int(flask.request.args.get("amount",98))
    order_id=random.randint(100,999)
    return start_payment(email,name,amount,order_id,f"http://localhost:5000/callback/{order_id}/success",f"http://localhost:5000/callback/{order_id}/fail",f"http://localhost:5000/callback/{order_id}/cancel", MERCHANT)


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
