from logging import exception
import eventlet.wsgi
from flask import request, jsonify, send_from_directory
from fuprox import db, app
from fuprox.models.models import (Branch, BranchSchema, Service, ServiceSchema, Company, CompanySchema, Help,
                                  HelpSchema, ServiceOffered, ServiceOfferedSchema, Booking, BookingSchema,
                                  TellerSchema, Teller, Payments, PaymentSchema, Mpesa, MpesaSchema, Recovery,
                                  RecoverySchema, ImageCompanySchema, ImageCompany, AccountStatus, AccountStatusSchema,
                                  Customer, CustomerSchema)
from fuprox.utils.payments import authenticate, stk_push
import secrets

# from fuprox.utilities import user_exists
from fuprox import bcrypt
from sqlalchemy import desc
import logging
import sqlalchemy
import socketio
import requests
import time
from datetime import datetime, timedelta
import json
import re
import smtplib, ssl
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fuprox.utils.email import body, password_changed, code_body
import random, requests
from pathlib import Path
import os
import subprocess
import itertools

link = "http://localhost:4000"
link_icon = "159.65.144.235"
# online socket link
socket_link = "http://159.65.144.235:5000/"
socket_link_2 = "http://159.65.144.235:6000/"

#  offline socket link
# socket_link = "http://localhost:5000/"
# standard Python
sio = socketio.Client()

# from fuprox.utilities import user_exists

# adding some product schemas
user_schema = CustomerSchema()
users_schema = CustomerSchema(many=True)

company_icon = ImageCompanySchema()
companies_icon = ImageCompanySchema(many=True)

service_ = ServiceSchema()
service_s = ServiceSchema(many=True)

# branch schema
branch_schema = BranchSchema()
branches_schema = BranchSchema(many=True)

# service offered schema
service_offered_schema = ServiceOfferedSchema()
services_offered_schema = ServiceOfferedSchema(many=True)

# service schema
service_schema = ServiceSchema()
services_schema = ServiceSchema(many=True)

booking_schema = BookingSchema()
bookings_schema = BookingSchema(many=True)

# getting companiy schema
company_schema = CompanySchema()
companies_schema = CompanySchema(many=True)

# help
help_schema = HelpSchema()
helps_schema = HelpSchema(many=True)

# service Offered
service_offer_schema = ServiceOfferedSchema()
service_offers_schema = ServiceOfferedSchema(many=True)

# teller schema
teller_schema = TellerSchema()
tellers_schema = TellerSchema(many=True)

# payment  schema
payment_schema = PaymentSchema()
payments_schema = PaymentSchema(many=True)

# mpesa_schema
mpesa_schema = MpesaSchema()
mpesas_schema = MpesaSchema(many=True)

# recovery_schema
recovery_schema = RecoverySchema()
recoverys_schema = RecoverySchema(many=True)

# account schema
account_schema = AccountStatusSchema()
accounts_schema = AccountStatusSchema(many=True)


def get_icon_by_company(company_name):
    company = Company.query.filter_by(name=company_name).first()
    if company:
        lookup = ImageCompany.query.filter_by(company=company.id).first()
    else:
        lookup = dict()
    return lookup


def get_icon_by_id(id):
    company = Company.query.get(id)
    lookup = ImageCompany.query.filter_by(company=company.id).first()
    return lookup


def add_user_account(user):
    try:
        lookup = AccountStatus(user)
        db.session.add(lookup)
        db.session.commit()
        
        # get user data
        lookup = AccountStatus.query.filter_by(user=user).first()
        return account_schema.dump(lookup)
    except sqlalchemy.exc.IntegrityError:
        lookup = AccountStatus.query.filter_by(user=user).first()
        return account_schema.dump(lookup)


def activate_account(usr):
    user = Customer.query.filter_by(email=usr).first()
    if user:
        lookup = AccountStatus.query.filter_by(user=user.id).first()
        if lookup:
            l = AccountStatus.query.filter_by(user=user.id).first()
            l.active = True
            db.session.commit()
            
            return account_schema.dump(lookup)
        else:
            return None
    else:
        return None


def user_is_active(usr):
    user = Customer.query.filter_by(email=usr).first()
    if user:
        lookup = AccountStatus.query.filter_by(user=user.id).first()
        if lookup:
            if bool(lookup.active):
                return True
            else:
                return False
        else:
            return False
    else:
        return False


# :::::::::::::::: Routes for graphs for the fuprox_no_queu_backend ::::
@app.route("/graph/data/doughnut", methods=["POST"])
def graph_data():
    # get all booking sorting by
    serviced_lookup = Booking.query.with_entities(Booking.date_added).filter_by(serviced=True).all()
    serviced_data = bookings_schema.dump(serviced_lookup)

    unserviced_lookup = Booking.query.with_entities(Booking.date_added).filter_by(serviced=False).all()
    unserviced_data = bookings_schema.dump(unserviced_lookup)
    print(unserviced_data)

    final = {
        "serviced": len(serviced_data),
        "unserviced": len(unserviced_data)
    }
    return final


@app.route('/graph/data/timeline', methods=["POST"])
def timeline():
    now = datetime.now()
    offset = timedelta.days(-15)
    # the offset for new date
    limit_date = (now + offset)
    date_lookup = Booking.query("date_added") \
        .filter(Booking.date_added.between(limit_date, now)).all()
    #  sort data using pandas
    date_data = bookings_schema.dump(date_lookup)
    return date_data


# activate account

@app.route("/user/account/activate", methods=["POST"])
def user_activate():
    email = request.json["email"]
    code = request.json["code"]
    if validate_email(email):
        user = Customer.query.filter_by(email=email).first()
        user_data = user_schema.dump(user)

        if user_data:
            # getting code for the suer
            code_ = AccountStatus.query.filter_by(user=user_data["id"]).first()
            if code_:
                print("<><><><><>", user_is_active(user_data["email"]))
                if not user_is_active(user_data["email"]):
                    if code == code_.code:
                        final = activate_account(user_data["email"])
                        if final:
                            data = {
                                "user": True,
                                "msg": "User account successfully activated active. Please Login"
                            }
                        else:
                            data = {
                                "user": None,
                                "msg": "Error! Could Not Activate account."
                            }
                    else:
                        data = {
                            "user": None,
                            "msg": "Error! Code Not valid."
                        }
                else:
                    data = {
                        "user": None,
                        "msg": "User is active. Please Login"
                    }
            else:
                data = {
                    "user": None,
                    "msg": "Error! Please, Recheck Code and reenter If error Persist contact Admin."
                }
        else:
            data = {
                "user": None,
                "msg": "User Not Found."
            }
    else:
        data = {
            "user": None,
            "msg": "Email Not valid."
        }
    return data


@app.route("/user/dev/reset", methods=["POST"])
def get_dev():
    email = request.json["email"]
    lookup = Customer.query.filter_by(email=email).first()
    if lookup:
        lookup.email = f"{secrets.token_hex(4)}@gmail.com"
        db.session.commit()
        
        return jsonify(user_schema.dump(lookup))
    else:
        return jsonify({
            "error": "Email not found"
        })


# :::: end
@app.route("/user/login", methods=["POST"])
def get_user():
    email = request.json["email"]
    password = request.json["password"]
    if validate_email(email):
        user = user_exists(email, password)
        if user["user_data"]["email"]:
            if user_is_active(user['user_data']["email"]):
                data = user
            else:
                data = {
                    "user": None,
                    "msg": "User is not active. Please check email for code to activate account."
                }
        else:
            data = {
                "user": None,
                "msg": "Error! User/Password Issue."
            }
    else:
        data = {
            "user": None,
            "msg": "Email Not valid."
        }
    return data


@app.route("/user/signup", methods=["POST"])
def adduser():
    email = request.json["email"]
    password = request.json["password"]
    dummy_phone = random.getrandbits(12)
    # get user data
    lookup = Customer.query.filter_by(email=email).first()
    user_data = user_schema.dump(lookup)
    if validate_email(email):
        if not user_data:
            # hashing the password
            hashed_password = bcrypt.generate_password_hash(password)
            user = Customer(email, dummy_phone, hashed_password)
            try:
                db.session.add(user)
                db.session.commit()
                
                data = user_schema.dump(user)

                # import time
                # time.sleep(60)
                code_data = add_user_account(data["id"])
                send_email(email, "You acccount activation code", code_body(code_data["code"]))

            except sqlalchemy.exc.DataError as e:
                data = {
                    "user": None,
                    "msg": "Error Adding user."
                }
            if data:
                sio.emit("sync_online_user", {"user_data": data})
        else:
            data = {
                "user": None,
                "msg": "User with that email Exists."
            }
    else:
        data = {
            "user": None,
            "msg": "Email Not Valid."
        }
    return data


@app.route("/password/forgot/email", methods=["POST"])
def password_forgot():
    email = request.json["email"]
    if validate_email(email):
        if email_exists(email):
            code = random_four()
            user = Customer.query.filter_by(email=email).first()
            if save_code(user.id, code):
                """
                to = request.json["to"]
                subject = request.json["subject"]
                body = request.json["body"]

                data = {
                    "to" : "denniskiruku@gmail.com",
                    "subject" : "king from",
                    "body" : body(code)

                }
                requests.post("http://127.0.0.1:4000/email",json=data)


                """

                send_email(user.email, "Password Recovery", body(code))
                return {
                    "user": True,
                    "msg": "Email Sent Successfully"
                }

            else:
                return {
                    "user": None,
                    "msg": "Error generating Code"
                }
        else:
            return {
                "user": None,
                "msg": "User with that email Does Not Exist."
            }
    else:
        return {
            "user": None,
            "msg": "Email Not Valid."
        }


@app.route("/password/forgot/code", methods=["POST"])
def code_is_valid():
    code = request.json["code"]
    lookup = Recovery.query.filter_by(code=code).first()
    if lookup and lookup.used == 0:
        return {
            "code": True,
            "msg": "Code Valid"
        }
    else:
        return {
            "user": None,
            "msg": "Code not valid."
        }


@app.route("/password/forgot/change", methods=["POST"])
def password_change():
    email = request.json["email"]
    code = request.json["code"]
    password = request.json["password"]
    if validate_email(email):
        if email_exists(email):
            user = Customer.query.filter_by(email=email).first()
            lookup = Recovery.query.filter_by(code=code).first()
            if lookup and lookup.code == code and lookup.used == 0:
                hashed_password = bcrypt.generate_password_hash(password)
                user.password = hashed_password
                db.session.commit()
                
                # mark code as used
                lookup.used = True
                db.session.commit()
                
                # send password change email
                send_email(user.email, "Password Successfully Changed", password_changed())

                return user_schema.dump(user)
            else:
                return {
                    "user": None,
                    "msg": "Code Not found/ Code used error."
                }
        else:
            return {
                "user": None,
                "msg": "User with that email Does Not Exist."
            }
    else:
        return {
            "user": None,
            "msg": "Email Not Valid."
        }


@app.route("/email", methods=["POST"])
def email_():
    to = request.json["to"]
    subject = request.json["subject"]
    body = request.json["body"]
    return send_email(to, subject, body)


'''
reset ticket counter
'''


@app.route("/reset/ticket/counter", methods=["POST"])
def reset_ticket():
    lookup = Booking.query.all()
    for booking in lookup:
        booking.nxt = 4004
        db.session.commit()
        
    #  here we are going to filter all tickets with the status [nxt == 4004]
    reset_data = get_all_bookings_no_branch()
    if reset_data:
        # there was some data reset
        final = loop_data_check_reset_tickets(reset_data)
    else:
        # No data to reset
        final = list()
    return jsonify(final)


def get_all_bookings_no_branch():
    data = Booking.query.filter_by(nxt=1001).all()
    return bookings_schema.dump(data)


def loop_data_check_reset_tickets(data):
    ticket_reset = list()
    for item in data:
        if item.nxt == 4004:
            ticket_reset.append(item)
    return ticket_reset


def save_code(user, code):
    lookup = Recovery(user, code)
    db.session.add(lookup)
    db.session.commit()
    
    return recovery_schema.dump(lookup)


def random_four():
    rand = random.getrandbits(30)
    numbers = str(rand)
    final = [numbers[i:i + 4] for i in range(0, len(numbers), 4)]
    final = f"{final[0]}-{final[1]}"
    return final


def email_exists(email):
    lookup = Customer.query.filter_by(email=email).first()
    return user_schema.dump(lookup)


def send_email(_to, subject, body):
    _from = "admin@fuprox.com"
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = _from
    message["To"] = _to

    # Turn these into plain/html MIMEText objects
    part = MIMEText(body, "html")
    # Add HTML/plain-text parts to MIMEMultipart message
    message.attach(part)
    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("mail.fuprox.com", 465, context=context) as server:
        server.login(_from, "Japanitoes")
        if server.sendmail(_from, _to, message.as_string()):
            return True
        else:
            return False


def validate_email(email):
    regex = re.compile(r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,'
                       r'3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$')
    return re.match(regex, email)


@app.route("/user/logout")
def user_logout():
    # remove the user token from the database
    token = request.json["token"]
    # remove token from db
    pass


@app.route("/branch/get")
def get_all_branches():
    branches = Branch.query.all()
    # loop over the
    res = branches_schema.dump(branches)
    lst = list()
    # here we are going to make a teller request to the socket
    # sio.emit("teller",{"branch_id":res})
    for item in res:
        final = bool()

        if branch_is_medical(item["id"]):
            final = True
        else:
            final = False

        item["is_medical"] = final
        icon = get_icon_by_company(item["company"])
        if icon:
            item["icon"] = f"http://{link_icon}:4000/icon/{icon.image}"
        else:
            item["icon"] = f"http://{link_icon}:4000/icon/default.png"
        lst.append(item)

    return jsonify({"branches": lst})


@app.route('/icon/<string:icon>', methods=["GET"])
def get_icon(icon):
    home = str(Path.home())
    icon_path = os.path.join(home, "fuprox_api", "icons")
    return send_from_directory("icons", filename=icon)


@app.route("/branch/get/single", methods=["GET", "POST"])
def get_user_branches():
    branch_id = request.json["branch_id"]
    branch_data = branch_get_single(branch_id)
    if branch_data:
        # if branch_data["status"] :
        #     branch_data.update({"icon": f"http://{link_icon}:4000/icon/default.png"})
        # else :
        print("here")
        print(branch_data)
        data = get_icon_by_company(branch_data["company"])
        try:
            branch_data.update({"icon": f"http://{link_icon}:4000/icon/{data['image']}"})
        except KeyError:
            branch_data.update({"icon": f"http://{link_icon}:4000/icon/default.png"})

    else:
        branch_data
    return jsonify(branch_data)


def branch_get_single(branch_id):
    # make a database selection
    data = Branch.query.filter_by(id=branch_id).first()
    res = branch_schema.dump(data)
    if res:
        final = bool()
        company_ = ""
        # get company_data
        if data:
            company = get_company_by_branch(res["company"])
            if company:
                company_ = company["id"]
        if res:
            if branch_is_medical(res["id"]):
                final = True
            else:
                final = False
        res["is_medical"] = final
        res["company"] = company_
    else:
        res = {}
    return res


def get_company_by_branch(branch_name):
    lookup = Company.query.filter_by(name=branch_name).first()
    company_data = company_schema.dump(lookup)
    return company_data


@app.route("/branch/add", methods=["POST"])
def add_branches():
    name = request.json["name"]
    company = request.json["company"]
    longitude = request.json["longitude"]
    latitude = request.json["latitude"]
    service = request.json["service"]
    opens = request.json["opens"]
    closes = request.json["closes"]
    description = request.json["description"]

    branch = Branch(name, company, longitude, latitude, opens, closes, service, description)
    db.session.add(branch)
    db.session.commit()
    
    return branch_schema.jsonify(branch)


@app.route("/service/add", methods=["GET", "POST"])
def add_service():
    name = request.json["name"]
    description = request.json["description"]
    service = Service(name, description)
    db.session.add(service)
    db.session.commit()
    
    return service_schema.jsonify(service)


@app.route("/service/get", methods=["GET", "POST"])
def get_service():
    services = Service.query.all()
    res = services_schema.dump(services)
    final = [i for n, i in enumerate(res) if i not in res[n + 1:]]
    return jsonify(final)


# booking start
# get single booking
@app.route("/book/get", methods=["POST"])
def get_book():
    # get booking id
    booking_id = request.json["booking_id"]
    user_id = request.json["user_id"]
    user = Customer.query.get(int(user_id))
    booking = Booking.query.get(int(booking_id))
    if user and booking:
        if user.id and booking.user :
            # return the ticket
            data = Booking.query.get(booking_id)
            final = booking_schema.dump(data)
            if final:
                name = ServiceOffered.query.filter_by(name=final["service_name"]).first()
                data = service_offer_schema.dump(name)
                res = {
                    "active": final["active"],
                    "branch_id": final["branch_id"],
                    "booking_id": final["id"],
                    "service_name": final["service_name"],
                    "serviced": final["serviced"],
                    "user_id": final["user"],
                    "start": final["start"],
                    "code": data["code"] + final["ticket"]
                }
            else:
                res = {"msg": "user/booking mismatch"}
        else:
            res = {"msg": "user/booking mismatch"}
    else:
        res = {"msg": "user/booking mismatch"}
    return jsonify({"booking_data": res})


#  other details
mpesa_transaction_key = ""
phone_number = int()


@app.route("/book/make", methods=["POST"])
def make_book():
    is_instant = True if request.json["is_instant"] else False
    phonenumber = request.json["phonenumber"]
    # setting the token
    global mpesa_transaction_key
    mpesa_transaction_key = secrets.token_hex(10)

    payment = Payments("texts", mpesa_transaction_key)
    db.session.add(payment)
    db.session.commit()
    
    # callback_url = f"http://{link_icon}:65123/mpesa/b2c/v1"

    # token_data = authenticate()
    # token = json.loads(token_data)["access_token"]
    # business_shortcode = "174379"
    # lipa_na_mpesapasskey = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
    # party_b = business_shortcode

    # if is_instant:
    #     # we are going to request pay
    #     amount = 10
    #     stk_push(token, business_shortcode, lipa_na_mpesapasskey, amount, party_b, phonenumber,
    #              callback_url)
    # else:
    #     # we are going to request pay
    #     amount = 5
    #     stk_push(token, business_shortcode, lipa_na_mpesapasskey, amount, party_b, phonenumber,
    #              callback_url)
    # token will be used to check if transaction is successful
    return jsonify({"token": mpesa_transaction_key})


@app.route("/verify/payment", methods=["POST"])
def make_book_():
    token = request.json["token"]
    service_name = request.json["service_name"]
    start = request.json["start"]
    branch_id = request.json["branch_id"]
    user_id = request.json["user_id"]
    amount = request.json["amount"]

    # we are going to use the payments table to display;
    # lookup = Payments.query.filter_by(token=token).first()
    # print(lookup)
    # main object
    # payment_data = payment_schema.dump(lookup)
    # print(">>>.",payment_data)
    # end
    # if payment_data:
    #     main = json.loads(payment_data["body"])
    #     parent = main["Body"]["stkCallback"]
    #     result_code = parent["ResultCode"]
    #     result_desc = parent["ResultDesc"]
    #     if int(result_code) == 0:
    #         callback_meta = parent["CallbackMetadata"]["Item"]
    #         amount = callback_meta[0]["Value"]
    #         # succesful payment
    #         if int(amount) == 10:
    #             # final = make_booking(service_name, start, branch_id, instant=True, user=user_id)
    #             final = create_booking(service_name, start, branch_id, True, user_id)
    #             sio.emit("online", final)
    #         elif int(amount) == 5:
    #             # final = make_booking(service_name, start, branch_id, instant=False, user=user_id)
    #             final = create_booking(service_name, start, branch_id, False, user_id)
    #             sio.emit("online", final)
    #     else:
    #         # error with payment
    #         final = {"msg": "Error With Payment", "error": result_desc}
    # else:
    #     final = {"msg": False, "result": "Token Invalid"}
    if int(amount) == 10:
        final = create_booking(service_name, start, branch_id, True, user_id)
        sio.emit("online", final)
    elif int(amount) == 5:
        final = create_booking(service_name, start, branch_id, False, user_id)
        sio.emit("online", final)
    return jsonify(final)


@app.route("/token/status", methods=["POST"])
def check_payment_status():
    token = request.json["token"]
    return jsonify({"valid": verify_payment(token), "data": get_payment(token)})


def get_payment(token):
    lookup = Mpesa.query.filter_by(local_transactional_key=token).first()
    data = mpesa_schema.dump(lookup)
    return data


def verify_payment(token):
    data = get_payment(token)
    if data:
        result_code = data["result_code"]
        if int(result_code) == 0:
            # succesful payment
            final = {"msg": True}
        else:
            # error with payment
            final = {"msg": False}
    else:
        final = {"msg": False, "result": "No payment info about that payment"}
    return final


# check if it is instant
def is_instant(token):
    data = get_payment(token)
    if data:
        amount = data["amount"]
        # result_message = data["result_desc"]
        # "result":result_message
        if amount == '10' or amount == "10.0" or amount == 10 or amount == 10.0:
            # succesful payment
            final = {"msg": True}
        else:
            # error with payment
            final = {"msg": False}
    else:
        final = {"msg": False, "result": "No payment info about that payment"}
    return final


number = phone_number


# rework of payment
@app.route("/payment/status", methods=["POST"])
def payment_on():
    res = request.json
    lookup = Payments(res, mpesa_transaction_key)
    db.session.add(lookup)
    db.session.commit()
    
    # geting the object in the db by this key
    lookup = Payments.query.filter_by(token=mpesa_transaction_key).first()
    data = payment_schema.dump(lookup)
    if data:
        final = dict(data)['body']
        data_ = payment_res(final)
    else:
        data_ = {"msg": "Token Invalid"}
    return data_


# @app.route("/test", methods=["POST"])
# def tests():
#     token = request.json["token"]
#     lookup = Payments.query.filter_by(token=token).first()
#     data = payment_schema.dump(lookup)
#
#     if data:
#         # updated
#         final = dict(data)['body']
#         data_ = payment_res(final)
#     else:
#         data_ = {"msg": "Token Invalid"}
#     return data_


# # dealing with payment status
# @app.route("/payment/status", methods=["POST"])
def payment_res(parsed):
    parsed = json.loads(parsed)
    parent = parsed["Body"]["stkCallback"]
    merchant_request_id = parent["MerchantRequestID"]
    checkout_request_id = parent["CheckoutRequestID"]
    result_code = parent["ResultCode"]
    result_desc = parent["ResultDesc"]
    lookup = Mpesa(merchant_request_id, checkout_request_id, result_code, result_code)

    # setting a unique for the database
    lookup.local_transactional_key = mpesa_transaction_key
    lookup.merchant_request_id = merchant_request_id
    lookup.checkout_request_id = checkout_request_id
    lookup.result_code = result_code
    lookup.result_desc = result_desc

    # # success details
    if int(result_code) == 0:
        # we are going to get the callbackmetadata
        callback_meta = parent["CallbackMetadata"]["Item"]
        amount = callback_meta[0]["Value"]
        receipt_number = callback_meta[1]["Value"]
        transaction_date = callback_meta[2]["Value"]
        phone_number = callback_meta[3]["Value"]

        # we are also going to add the rest of the data before commit
        lookup.amount = amount
        lookup.receipt_number = receipt_number
        lookup.transaction_date = transaction_date
        lookup.phone_number = phone_number
        db.session.add(lookup)
        db.session.commit()
    else:
        # herw we are going to se the number
        lookup.phone_number = number
        # here we are  just going to commit
        db.session.add(lookup)
        db.session.commit()
    db.session.commit()
    # add give data back to the user
    final = mpesa_schema.dump(lookup)
    return final


@app.route("/book/get/all", methods=["GET", "POST"])
def get_all_bookings():
    user_id = request.json["user_id"]
    if is_user(user_id):
        res = get_user_bookings(user_id)
        tickets = list()
        for booking in res:
            tickets.append(generate_ticket(booking["id"]))
        res = tickets
    else:
        res = {"msg": "user does not exist"}, 500
    return jsonify({"booking_data": res})


@app.route("/book/get/user", methods=["POST"])
def get_user_bookings_():
    # getting post data
    user_id = request.json["user_id"]
    if user_id:
        # make a database selection
        data = Booking.query.filter_by(user=user_id).all()
        final = bookings_schema.dump(data)
    else:
        final = None
    return jsonify({"booking_data": final})


# booking end
@app.route("/company/get")
def get_companies():
    companies = Company.query.all()
    company_data = companies_schema.dump(companies)
    lst = list()
    for company in company_data:
        icon = get_icon_by_company(company["name"])
        if icon:
            company.update({"icon": f"http://{link_icon}:4000/icon/{icon.image}"})
            lst.append(company)
        else:
            company.update({"icon": f"http://{link_icon}:4000/icon/default.png"})
            lst.append(company)
    return jsonify(lst)


# getting branch by company
@app.route("/branch/by/company", methods=["POST"])
def get_by_branch():
    company = request.json["company"]
    # check the company name from id
    company_lookup = Company.query.get(company)
    company_data = company_schema.dump(company_lookup)
    lst = list()
    if company_data:
        branch = Branch.query.filter_by(company=company_data["name"]).all()
        data = branches_schema.dump(branch)
        for item in data:
            final = bool()
            if branch_is_medical(item["id"]):
                final = True
            else:
                final = False
            item["is_medical"] = final
            icon = get_icon_by_company(item["company"])
            print(item["company"])
            print("icons :::: >>", icon)
            if icon:
                item["icon"] = f"http://{link_icon}:4000/icon/{icon.image}"
            else:
                item["icon"] = f"http://{link_icon}:4000/icon/default.png"
            lst.append(item)
    return jsonify(lst)


@app.route("/branch/by/service", methods=["POST"])
def get_by_service():
    service = request.json["service"]
    branch = Branch.query.filter_by(service=service).all()
    data = branches_schema.dump(branch)
    lst = list()
    for item in data:
        if branch_is_medical(item["id"]):
            final = True
        else:
            final = False
        item["is_medical"] = final
        icon = get_icon_by_company(item["company"])
        if icon:
            item["icon"] = f"http://{link_icon}:4000/icon/{icon.image}"
        else:
            item["icon"] = f"http://{link_icon}:4000/icon/default.png"
        lst.append(item)
    return jsonify(data)


@app.route("/company/by/id", methods=["POST"])
def company_service():
    service = request.json["id"]
    company = Company.query.get(service)
    data = company_schema.dump(company)
    icon = get_icon_by_id(company.id)
    if icon:
        data.update({"icon": f"http://{link_icon}:4000/icon/{icon.image}"})
    else:
        data.update({"icon": f"http://{link_icon}:4000/icon/default.png"})

    return jsonify(data)


@app.route("/company/by/service", methods=["POST"])
def company_by_service():
    service = request.json["service"]
    company = Company.query.filter_by(service=service).all()
    data = companies_schema.dump(company)
    print(data)
    lst = list()
    for item in data:
        final = bool()
        icon = get_icon_by_company(item["name"])
        if icon:
            item["icon"] = f"http://{link_icon}:4000/icon/{icon.image}"
        else:
            item["icon"] = f"http://{link_icon}:4000/icon/default.png"
        lst.append(item)
    return jsonify(data)


@app.route("/search/<string:term>")
def search(term):
    # getting user specific data
    search = Help.query.filter(Help.solution.contains(term))
    data = helps_schema.dump(search)
    return jsonify(data)


@app.route("/help/feed", methods=['POST'])
def help_feed():
    lookup = Help.query.limit(5).all()
    data = helps_schema.dump(lookup)
    return jsonify(data)


@app.route("/help/feed/more", methods=["POST"])
def help_more():
    help = request.json["help_id"]
    data = Help.query.get(help)
    return help_schema.dump(data)


@app.route("/help/feed/search", methods=["POST"])
def help_search_app():
    query = request.json["query"]
    solution = Help.query.filter(Help.solution.like(f"%{query}%")).all()
    header = Help.query.filter(Help.title.like(f"%{query}%")).all()

    solutions = helps_schema.dump(solution)
    headers = helps_schema.dump(header)
    final = solutions + headers
    return jsonify(final)


# the search route
@app.route("/app/search", methods=["POST"])
def search_app():
    # data from the terms search
    term = request.json["term"]
    company_lookup = Company.query.filter(Company.name.contains(term)).first()
    company_data = company_schema.dump(company_lookup)
    # getting branch_data from company data
    final_branch_data_company = []
    if company_data:
        company_name = company_data["name"]
        branchdata_from_companyid = Branch.query.filter_by(company=company_name).all();
        branch_data_company = branches_schema.dump(branchdata_from_companyid)
        final_branch_data_company = branch_data_company
    # gettng data by company name
    branch_lookup = Branch.query.filter(Branch.name.like(f"%{term}%")).all();
    branch_data_branch = branches_schema.dump(branch_lookup)
    final_branch_data_term = branch_data_branch
    # update cunstomer data to add medical
    data = final_branch_data_term + final_branch_data_company
    lst = list()

    for item in data:
        final = bool()
        if branch_is_medical(item["id"]):
            final = True
        else:
            final = False
        med = {"is_medical": final}

        # getting company data from branchname
        branch = Company.query.filter_by(name=item["company"]).first()
        data = branch_schema.dump(branch)
        item["company"] = data["id"]

        icon = get_icon_by_company(item["company"])
        if icon:
            item.update({"icon": f"http://{link_icon}:4000/icon/{icon.image}"})
        else:
            item.update({"icon": f"http://{link_icon}:4000/icon/default.png"})
        item.update(med)
        lst.append(item)
    final_list = [dict(t) for t in {tuple(d.items()) for d in lst}]
    return jsonify(final_list)


@app.route("/services/get/all", methods=["POST"])
def service_offered():
    branch_id = request.json["branch_id"]
    lookup = ServiceOffered.query.filter_by(branch_id=branch_id).all()
    final = service_offers_schema.dump(lookup)
    return jsonify(final)


@app.route("/ahead/of/you", methods=["POST"])
def ahead_of_you():
    service_name = request.json["service_name"]
    branch_id = request.json["branch_id"]

    # get the tellers for that service
    tellers = Teller.query.filter_by(service=service_name).filter_by(branch=branch_id).all()
    log(f"service name {service_name}")
    log(f"Branch_id {branch_id}")
    # loop to get the services forwarded to these tellers
    for teller in tellers:
        log(teller)
        # get booking forwared count
        bookings = db.session.execute(
            f"SELECT * FROM booking WHERE unique_teller = '{teller.unique_id}' AND serviced = 0")
        bookings_ = [dict(x)["unique_id"] for x in bookings]

    # get the maximum number of forwarded
    # get the bookings meant for this teller that are not forwarded and other flags

    bookings_final = list()
    forwarded_per_teller = list()
    for teller in tellers:
        bookings = Booking.query.filter_by(unique_teller=teller.unique_id).filter_by(serviced=False).filter_by(
            nxt=1001).all()
        bookings_final.append(bookings)
        forwarded_per_teller.append(len(bookings))
        log(f"per teller data {teller.unique_id} -> {bookings}")

    log(forwarded_per_teller)
    # get the teller with max forwarded
    data_ = max(forwarded_per_teller) if len(forwarded_per_teller) else 0

    # get this teller_kind_bookings
    # get other booking that are not forwarded but belong to this teller type
    query = f"SELECT * FROM booking WHERE service_name = '{service_name}' AND branch_id = {branch_id} AND serviced = 0 AND forwarded = 0 AND nxt =1001"

    actual_teller_bookings = db.session.execute(query)
    data = [dict(x)["unique_id"] for x in actual_teller_bookings]
    log(f">>{data_}")
    log(f"<<<<<{len(data)}")
    final = len(data) + data_

    return jsonify({"infront": final})


@app.route("/ahead/of/you/id", methods=["POST"])
def ahead_of_you_id_():
    branch_id = request.json["booking_id"]
    return jsonify(ahead_of_you_id(branch_id))


@app.route("/sycn/online/booking", methods=["POST"])
def sync_bookings():
    service_name = request.json["service_name"]
    start = request.json["start"]
    branch_id = request.json["branch_id"]
    is_instant = request.json["is_instant"]
    user = request.json["user"]
    ticket = request.json["ticket"]
    key_ = request.json["key_"]
    unique_id = request.json["unique_id"]
    is_synced = True if int(user) == 0 else False
    serviced = request.json['serviced']
    forwarded = request.json["forwarded"]
    unique_teller = request.json["unique_teller"]

    if not booking_exists_by_unique_id(unique_id):
        final = dict()
        try:
            try:
                final = create_booking_online_(service_name, start, branch_id, is_instant, user, kind=ticket,
                                               key=key_, unique_id=unique_id, is_synced=is_synced, serviced=serviced,
                                               forwarded=forwarded, unique_teller=forwarded)
            except ValueError as err:
                log(err)
        except sqlalchemy.exc.IntegrityError:
            log("Error! Could not create booking.")
    else:
        log("Booking Does exist.")
        final = {"msg": "booking exists"}
        ack_successful_entity("BOOKING", {"unique_id": unique_id})
    return final


@app.route("/sycn/offline/services", methods=["POST"])
def sync_services():
    name = request.json["name"]
    teller = request.json["teller"]
    branch_id = request.json["branch_id"]
    code = request.json["code"]
    icon_id = request.json["icon"]
    key = request.json["key"]
    unique_id = request.json["unique_id"]
    service = dict()
    try:
        key_data = get_online_by_key(key)
        if key_data:
            service = create_service(name, teller, key_data["id"], code, icon_id, unique_id)
        else:
            service = dict()
    except sqlalchemy.exc.IntegrityError:
        print("Error! Could not create service.")
    return service_schema.jsonify(service)


@app.route('/sycn/offline/teller', methods=["POST"])
def sycn_teller():
    service = request.json["service"]
    branch = request.json["branch"]
    number_ = request.json["number"]
    unique_id = request.json["unique_id"]
    branch_unique_id = request.json["branch_unique_id"]
    teller_ = dict()
    ref = branch_by_unique_id_for_teller
    try:
        teller_ = add_teller(number_, ref.id, service, unique_id, branch_unique_id)
    except sqlalchemy.exc.IntegrityError as e:
        print(e)
        print("Error! Teller could not be added Could not add the record.")
    return teller_


def branch_by_unique_id_for_teller(branch_unique_id):
    lookup = Branch.query.filter_by(unique_id = branch_unique_id ).first()
    return lookup

@app.route("/update/ticket", methods=["POST"])
def update_tickets_():
    # get branch by key
    key = request.json["key_"]
    service_name = request.json["service_name"]
    ticket = request.json["ticket"]
    branch_data = get_online_by_key(key)
    final = dict()
    if branch_data:
        # online booking
        booking_lookup = Booking.query.filter_by(service_name=service_name).filter_by(branch_id=branch_data["id"]). \
            filter_by(ticket=ticket).first()
        booking_data = booking_schema.dump(booking_lookup)
        if booking_data:
            # make this booking active
            booking_lookup.serviced = True
            db.session.commit()
            final = booking_schema.dump(booking_lookup)
        # if data is not saved save
        # ______!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # TODO: add sync if does not exist
    return final


@app.route("/payments/user/status", methods=["POST"])
def payment_user_status():
    data = request.json["phone"]
    lookup = Payments(data)
    # we are going to work with new mpsay payments
    db.session.add(lookup)
    db.session.commit()
    return payment_schema.jsonify(lookup)


'''
reset ticket count
'''


@app.route("/ticket/reset", methods=["POST"])
def reset():
    code = {"code": random.getrandbits(100)}
    sio.emit("reset_tickets", code)
    return jsonify(code)


@app.route("/init/sync/online", methods=["POST"])
def init_sync():
    branch = request.json["key"]
    sio.emit("init_sync", {"key": branch})
    return dict()


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# functions >>>>>>>>>>>>>>>>>>>>>>>>
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


def get_online_by_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    lookup_data = branch_schema.dump(lookup)
    return lookup_data


def services_exist(services, branch_id):
    holder = services.split(",")
    for item in holder:
        if not service_exists(item, branch_id):
            return False
    return True


def add_teller(teller_number, branch_id, service_name, unique_id, branch_unique_id):
    # here we are going to ad teller details
    # two words service name
    if not teller_exists_unique(unique_id):
        if len(service_name.split(",")) > 1:
            # get teller by unique
            if get_teller(unique_id):
                final = {"msg": "Teller number exists"}, 500
                # log(f"teller exists - {unique_id}")
            else:
                lookup = Teller(teller_number, branch_id, service_name, branch_unique_id)
                lookup.unique_id = unique_id
                try:
                    db.session.add(lookup)
                    db.session.commit()
                    print("added")
                    ack_successful_entity("TELLER", teller_schema.dump(lookup))
                    log(f"teller synced + {unique_id}")
                except sqlalchemy.exc.IntegrityError:
                    ack_failed_entity("TELLER", {"unique_id": unique_id})
                    # log(f"teller exists - {unique_id}")
                    ack_successful_entity("TELLER", {"data": {"unique_id": unique_id}})

                final = teller_schema.dump(lookup)
        else:
            # get teller by unique
            if get_teller(unique_id):
                final = {"msg": "Teller number exists"}, 500
                log(f"teller exists - {unique_id}")
                ack_successful_entity("TELLER", {"unique_id": unique_id})
            else:
                lookup = Teller(teller_number, branch_id, service_name, branch_unique_id)
                lookup.unique_id = unique_id

                db.session.add(lookup)
                db.session.commit()
                
                final = teller_schema.dump(lookup)
                log(f"teller synced + {unique_id}")

    else:
        lookup = teller_exists_unique(unique_id)
        ack_successful_entity("TELLER", {"unique_id": unique_id})
        log("We should make teller synced")
        lookup.is_synced = True
        db.session.commit()
        
        final = dict()
    return final


"""
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:::::sync offline booking | service >> online data for offline updating:::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
"""


def teller_exists_unique(unique_id):
    return Teller.query.filter_by(unique_id=unique_id).first()


def get_branch_by_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    return branch_schema.dump(lookup)


# new sync implementation
# get all data online to offline
def get_sync_all_data(key):
    # get all booking
    bookings_to_sync = get_all_unsyced_bookings()
    # return the data
    final = {"bookings": bookings_to_sync, "key": key}
    return final


def get_all_unsyced_bookings(branch_key):
    branch = get_branch_by_key(branch_key)
    online = Booking.query.filter_by(nxt=1001).filter_by(active=False).filter_by(branch_id=branch["id"]).filter_by(
        serviced=False).filter_by(is_synced=False).all()
    online_bookings = bookings_schema.dump(online)
    return online_bookings


@app.route("/bookings/to/sycn", methods=["POST"])
def test__():
    key = request.json["key"]
    data = sync_service(key)
    final = list()
    for record in data:
        final.append(record["unique_id"])
    return jsonify(data)


def sync_service(key):
    branch_data = get_branch_by_key(key)
    final = dict()
    if branch_data:
        # branch_data font the company
        final = get_all_unsyced_bookings(key)
    # emit event
    return final


# getting branch data
def sync_company_data():
    company_lookup = Company.query.all()
    company_data = companies_schema.dump(company_lookup)
    return company_data


def sycn_branch_data(key):
    # get all the branch`
    branch = get_branch_by_key(key)
    # get the company for the branch
    final = list()
    if branch:
        company = Company.query.filter_by(name=branch["company"]).first()
        company_data = company_schema.dump(company)
        if company_data:
            branches_lookup = Branch.query.filter_by(company=company_data["name"]).all()
            branches_data = branches_schema.dump(branches_lookup)
            final = branches_data
    # get all the branches for that company
    return final


# sycing off line services
def create_service(name, teller, branch_id, code, icon_id, unique_id=""):
    if branch_exist(branch_id):
        final = None
        if service_exists_by_unique_id(unique_id):
            final = {"msg": "Error service name already exists"}
            log(f"service exists - {unique_id}")
            ack_successful_entity("SERVICE", {"unique_id": unique_id})
        else:
            if get_service_code(code, branch_id):
                final = {"msg": "Error Code already exists"}
                log(f"service exists [code] - {unique_id} - {code}")
                ack_successful_entity("SERVICE", {"unique_id": unique_id})

            else:
                service = ServiceOffered(name, branch_id, teller, code, int(icon_id))
                service.unique_id = unique_id
                service.is_synced = True
                try:
                    db.session.add(service)
                    db.session.commit()
                    
                    ack_successful_entity("SERVICE", service_schema.dump(service))
                    log(f"service synced + {unique_id}")
                except sqlalchemy.exc.IntegrityError as e:
                    ack_failed_entity("SERVICE", {"unique_id": unique_id})
                    log(f"service exists - {unique_id}")
                final = service_schema.dump(service)
    else:
        final = {"msg": "Service/Branch issue"}
    return final


def update_sync_all_data(data):
    bookings = data["bookings"]
    key = data["key"]
    if branch_exists_key(key):
        # we can sync
        for booking in bookings:
            # check if booking exists
            if not booking_exists_unique(booking):
                # booking does not exists
                # add booking to the db
                # flag the booking as synced now
                id = booking["id"]
                service_name = booking["service_name"]
                start = booking["start"]
                branch_id = booking["branch_id"]
                ticket = booking["ticket"]  # replaces kind
                active = booking["active"]
                nxt = booking["nxt"]
                serviced = booking["serviced"]
                teller = booking["teller"]
                kind = booking["kind"]
                user = booking["user"]
                is_instant = booking["is_instant"]
                forwarded = booking["forwarded"]
                is_synced = booking["is_synced"]
                unique_id = booking["unique_id"]
                # adding data to the database
                create_booking(service_name, start, branch_id, bool(is_instant), user, unique_id, is_synced)
            else:
                # booking exists
                flag_booking_as_synced(booking)
                ack_successful_entity("BOOKING", booking)
    else:
        print("branch data is not for this branch")
    return dict()


def booking_exists_unique(data):
    final = Booking.query.filter_by(unique_id=data["unique_id"]).first()
    return final


# def flag_booking_as_synced(data):
#     booking = booking_exists_unique(data)
#     booking.is_synced = True
#     return booking


def branch_exists_key(key):
    lookup = Branch.query.filter_by(key_=key).first()
    return lookup


# check if the user exists
def user_exists(email, password):
    data = Customer.query.filter_by(email=email).first()
    print("user_data", data)
    # checking for the password
    if data:
        if bcrypt.check_password_hash(data.password, password):
            token = secrets.token_hex(48)
            result = {"user_data": user_schema.dump(data), "token": token}
        else:
            result = {
                "user_data": {
                    "email": None,
                    "msg": "Bad Username/Password combination"
                }
            }
    else:
        result = {
            "user_data": {
                "email": None,
                "msg": "Bad Username/Password combination"
            }
        }
    return result


def is_user(user_id):
    lookup = Customer.query.get(user_id)
    user_data = user_schema.dump(lookup)
    return user_data


def get_teller(unique_id):
    lookup = Teller.query.filter_by(unique_id=unique_id).first()
    data = teller_schema.dump(lookup)
    return data


def ticket_queue(service_name, branch_id):
    lookup = Booking.query.filter_by(service_name=service_name).filter_by(nxt=1001).filter_by(
        branch_id=branch_id).order_by(
        desc(Booking.date_added)).first()
    booking_data = booking_schema.dump(lookup)
    return booking_data


def create_booking(service_name, start, branch_id, is_instant, user_id):
    if service_exists(service_name, branch_id):
        if is_user(user_id):
            final = ""
            # get the service
            data = service_exists(service_name, branch_id)
            name = data["name"]
            if ticket_queue(service_name, branch_id):
                # get last ticket is active next == True
                # get the last booking
                book = get_last_ticket(service_name, branch_id)
                # if is active we can creat a next
                is_active = book["active"]
                is_serviced = book["serviced"]
                # last booking next so this booking should just be a normal booking
                last_ticket_number = book["ticket"]
                next_ticket = int(last_ticket_number) + 1
                final = make_booking(name, start, branch_id, next_ticket, instant=is_instant, user=user_id)
            else:
                # we are making the first booking for this category
                # we are going to make this ticket  active
                next_ticket = 1
                final = make_booking(name, start, branch_id, next_ticket, active=True, instant=is_instant, user=user_id)
        else:
            print("user_does not exist")
            final = None
            logging.info("user does not exist")
    else:
        print("service does not exist")
        final = None
        logging.info("service does not exists")
    return final


def create_booking_online(service_name, start, branch_id, ticket, is_instant=False, user_id="", is_active=False):
    data = service_exists(service_name, branch_id)
    final = make_booking(service_name, start, branch_id, ticket, False, is_active, instant=is_instant, user=user_id)
    return final


def update_branch_offline(key):
    lookup = Branch.query.filter_by(key_=key).first()
    lookup_data = branch_schema.dump(lookup)
    return lookup_data


def create_booking_online_(service_name, start, branch_id_, is_instant=False, user=0, kind=0, key="", unique_id="",
                           is_synced="", serviced=False, forwarded=False, unique_teller=0):
    data_ = update_branch_offline(key)
    branch_id = data_["id"] if data_ else 1
    if branch_is_medical(branch_id):
        if service_exists(service_name, branch_id):
            # get the service
            data = service_exists(service_name, branch_id)
            name = data["name"]
            if ticket_queue(service_name, branch_id):
                book = ticket_queue(service_name, branch_id)
                last_ticket_number = book["ticket"]
                next_ticket = int(last_ticket_number) + 1
                log("before make booking call")
                final = make_booking(name, start, branch_id, next_ticket, instant=False, user=user, kind=kind,
                                     unique_id=unique_id, is_synced=is_synced, serviced=serviced, forwarded=forwarded,
                                     unique_teller=unique_teller)
            else:
                # we are making the first booking for this category
                # we are going to make this ticket  active
                next_ticket = 1
                final = make_booking(name, start, branch_id, next_ticket, active=False, instant=False, user=user,
                                     kind=kind, unique_id=unique_id, is_synced=is_synced, serviced=serviced,
                                     forwarded=forwarded, unique_teller=unique_teller)
        else:
            raise ValueError("Service Does Not Exist. Please Add Service First.")
            final = True
    else:
        if service_exists(service_name, branch_id):
            # get the service
            data = service_exists(service_name, branch_id)
            name = data["name"]
            if ticket_queue(service_name, branch_id):
                book = ticket_queue(service_name, branch_id)
                last_ticket_number = book["ticket"]
                next_ticket = int(last_ticket_number) + 1
                log(f"before make booking call-> booking status {serviced}")
                final = make_booking(name, start, branch_id, next_ticket, instant=is_instant, user=user, kind=kind,
                                     unique_id=unique_id, is_synced=is_synced, serviced=serviced, forwarded=forwarded,
                                     unique_teller=unique_teller)
            else:
                # we are making the first booking for this category
                # we are going to make this ticket  active
                next_ticket = 1
                log(f"before make booking call-> booking status {serviced}")
                final = make_booking(name, start, branch_id, next_ticket, active=False, instant=is_instant, user=user,
                                     kind=kind, unique_id=unique_id, is_synced=is_synced, serviced=serviced,
                                     forwarded=forwarded, unique_teller=unique_teller)
        else:
            raise ValueError("Service Does Not Exist. Please Add Service First.")
            final = True

    # print("the final output of the fuction >>>>", final)
    time.sleep(5)
    return final


# requests.exceptions.ConnectionError: HTTPConnectionPool

def make_booking(service_name, start="", branch_id=1, ticket=1, active=False, upcoming=False, serviced=False,
                 teller=000, kind="1", user=0000, instant=False, unique_id="", is_synced="", forwarded=False,
                 unique_teller=0):
    final = list()
    branch_data = branch_exist(branch_id)
    if branch_is_medical(branch_id):
        log("This is a medical branch")
        lookup = Booking(service_name, start, branch_id, ticket, active, upcoming, serviced, teller, kind, user, False,
                         forwarded)
        if unique_id:
            lookup.unique_id = unique_id
        if is_synced:
            lookup.is_synced = True
        if serviced:
            lookup.serviced = True
        if forwarded:
            lookup.forwarded = True
        if unique_teller:
            lookup.unique_teller = unique_teller

        db.session.add(lookup)
        db.session.commit()
        
        final = booking_schema.dump(lookup)
        if final:
            ack_successful_entity("BOOKING", final)
            log(f"service synced + {unique_id}")
        else:
            ack_failed_entity("BOOKING", {"unique_id": unique_id})
            log(f"Error Booking + {unique_id}")
        final.update({"key": branch_data["key_"]})

    else:
        lookup = Booking(service_name, start, branch_id, ticket, active, upcoming, serviced, teller, kind, user,
                         instant, fowarded=False)
        if unique_id:
            lookup.unique_id = unique_id

        if is_synced:
            lookup.is_synced = True

        if serviced:
            lookup.serviced = True
        db.session.add(lookup)
        db.session.commit()
        
        final = booking_schema.dump(lookup)
        if final:
            ack_successful_entity("BOOKING", final)
            log(f"service synced + {unique_id}")
        else:
            ack_failed_entity("BOOKING", {"unique_id": unique_id})
            log(f"Error Booking + {unique_id}")

        final.update({"key": branch_data["key_"]})
    return final


def ack_successful_entity(name, data):
    sio.emit("ack_successful_enitity", {"category": name, "data": data})
    return data


def ack_failed_entity(name, data):
    sio.emit("ack_failed_enitity", {"category": name, "data": data})
    return data


def service_exists(name, branch_id):
    lookup = ServiceOffered.query.filter_by(name=name).filter_by(branch_id=branch_id).first()
    data = service_offered_schema.dump(lookup)
    return data


def service_exists_by_unique_id(unique_id):
    lookup = ServiceOffered.query.filter_by(unique_id=unique_id).first()
    data = service_offered_schema.dump(lookup)
    return data


def get_last_ticket(service_name, branch_id):
    """ Also check last online ticket """
    # here we are going to get the last ticket offline then make anew one base on that's
    # emit("last_ticket",{"branch_id":branch_id,"service_name": service_name})

    lookup = Booking.query.filter_by(service_name=service_name).filter_by(nxt=1001).order_by(
        desc(Booking.date_added)).first()
    booking_data = booking_schema.dump(lookup)
    return booking_data


def branch_exist(branch_id):
    lookup = Branch.query.get(branch_id)
    branch_data = branch_schema.dump(lookup)
    return branch_data


# assume we are making a booking
def generate_ticket(booking_id):
    # get_ticket code
    booking = get_booking(booking_id)
    if booking:
        branch = branch_exist(booking['branch_id'])
        service = service_exists(booking["service_name"], booking["branch_id"])
        if branch and service:
            code = service["code"] + booking["ticket"]
            branch_name = branch["name"]
            company = branch["company"]
            service_name = service["name"]
            date_added = booking["start"]
            booking_id = booking["id"]
            final = {"booking_id": booking_id, "code": code, "branch": branch_name, "company": company,
                     "service": service_name, "date": date_added}
        else:
            final = {"msg": "Details not Found"}
    else:
        final = {"msg": "Booking not Found"}
    return final


def get_booking(booking_id):
    lookup = Booking.query.get(booking_id)
    data = booking_schema.dump(lookup)
    return data


def get_user_bookings(user_id):
    lookup = Booking.query.filter_by(user=user_id).all()
    data = bookings_schema.dump(lookup)
    return data


def user_id_exists(user_id):
    lookup = Customer.query.get(user_id)
    return lookup


def branch_is_medical(branch_id):
    branch_lookup = Branch.query.get(branch_id)
    branch_data = branch_schema.dump(branch_lookup)
    if branch_data:
        lookup = Service.query.filter_by(name=branch_data["service"]).first()
        service_data = service_.dump(lookup)
        if service_data["is_medical"]:
            service_data = True
        else:
            service_data = False
    else:
        service_data = None
    return service_data


def get_teller_service(teller_unique_id):
    lookup = Teller.query.filter_by(unique_id=teller_unique_id).first()
    return lookup.service


def booking_teller_service_real(unique_id):
    lookup = Booking.query.filter_by(unique_id=unique_id).first()
    return lookup.service_name


def booking_teller_service_forwarded(unique_id):
    lookup = Booking.query.filter_by(unique_id=unique_id).first()
    return get_teller_service(lookup.unique_teller)


def get_tellers_by_name_and_branch(name, branch):
    lookup = Teller.query.filter_by(service=name).filter_by(branch=branch).all()
    return lookup


def tellers_offered_on(booking_id):
    booking = Booking.query.get(booking_id)
    tellers = Teller.query.filter_by(service=booking.service_name).filter_by(branch=booking.branch_id).all()
    return tellers


def tellers_offered_on_is_forwarded(booking_id):
    booking = Booking.query.get(booking_id)
    if booking.unique_teller:
        teller = Teller.query.filter_by(unique_id=booking.unique_teller).first()
        tellers = Teller.query.filter_by(service=teller.service).filter_by(branch=teller.branch).all()
    return tellers


def any_forwarded_ticket_on_teller(booking_id):
    tellers = tellers_offered_on(booking_id)
    list_x = list()
    for teller in tellers:
        forwarded_service_bookings_per_teller = Booking.query.filter_by(unique_teller=teller.unique_id).filter_by(
            forwarded=True).filter_by(serviced=False).filter_by(nxt=1001).all()
        list_x.append(forwarded_service_bookings_per_teller)
    list_x = list(itertools.chain(*list_x))
    final = set(list_x)
    return final


def any_forwarded_ticket_on_teller_otherside(booking_id):
    # check if other tellers have same service
    tellers = tellers_offered_on_is_forwarded(booking_id)
    list_x = list()
    for teller in tellers:
        forwarded_service_bookings_per_teller = Booking.query.filter_by(unique_teller=teller.unique_id).filter_by(
            forwarded=True).filter_by(serviced=False).filter_by(nxt=1001).all()
        list_x.append(forwarded_service_bookings_per_teller)
    list_x = list(itertools.chain(*list_x))
    final = set(list_x)

    return final


def other_service_bookings_tellers_of_this_booking_id_to_these_service_tellers(booking_id):
    booking = Booking.query.get(booking_id)
    # service name
    booking_service = Booking.service_name
    # get tellers
    tellers = Teller.query.filter_by(service=booking_service).all()
    # booking to the teller
    final = 0
    for teller in tellers:
        # select bookings which are not type loans and is forwarded and not serviced and nxt = 1001 and unique_teller
        proxy = db.session.execute(
            f"SELECT count(*) FROM booking WHERE  service_name='{booking_service}' AND forwarded "
            f"= 1 AND serviced = 0 AND nxt = 1001 AND unique_teller='{teller.unique_id}'")
        data = [list(x) for x in proxy]
        data = list(itertools.chain(*data))
        final = final + data[0]
    return final


def forwarded_bookings_to_this_kind_of_tellers(booking_id):
    # get teller_forwareded to type
    booking = Booking.query.get(booking_id)
    # teller_type
    teller = booking.unique_teller
    # get teller
    init_target_teller = Teller.query.filter_by(unique_id=teller).first()

    # service_type
    service_type = init_target_teller.service

    # get all tellers with the
    tellers = Teller.query.filter_by(service=service_type).all()
    # tellers bookings
    final = 0
    for teller in tellers:
        proxy = db.session.execute(f"select count(*) from booking where forwarded= 1 and nxt =1001 and serviced = 0 "
                                   f"and unique_teller = '{teller.unique_id}'")
        data = [list(x) for x in proxy]
        data = list(itertools.chain(*data))
        final = final + data[0]
    return final


def point_x(booking_id):
    final = list()
    log(f"ANY FORWARDED TICKET ON TELLER {any_forwarded_ticket_on_teller(booking_id)}")
    log(f"ANY OWN FORWARDED TICKET ON OTHER TELLER {any_forwarded_ticket_on_teller_otherside(booking_id)}")
    log(other_service_bookings_tellers_of_this_booking_id_to_these_service_tellers(booking_id))
    log(forwarded_bookings_to_this_kind_of_tellers(booking_id))
    # if any_forwarded_ticket_on_teller(booking_id):
    #
    # # get this booking forwarded service
    # book_get = Booking.query.filter_by(id=booking_id).filter_by(forwarded=True).first()
    #
    # #  get the booking forwarded to that service
    # forwarded_service = get_teller_service(book_get.unique_teller)
    #
    # # get tellers which ofer this service
    # # get booking forawarded to each of these tellers
    # tellers = get_tellers_by_name_and_branch(forwarded_service,book_get.branch_id)
    #
    # # for each of these tellers get services booked to them either active or also add to the one that are
    # list_x = list()
    # for teller in tellers:
    #     forwarded_service_bookings_per_teller = Booking.query.filter_by(unique_teller=teller.unique_id).filter_by(forwarded=True).filter_by(serviced=False).filter_by(nxt=1001).all()
    #     list_x.append(forwarded_service_bookings_per_teller)
    # list_x = list(itertools.chain(*list_x))
    # final = set(list_x)

    return len(final)


def bookings_forwared_to_this_teller_and_others_of_its_kind(booking_id):
    init = Booking.query.get(booking_id)
    # forwarded status
    is_forwarded = init.forwarded
    if is_forwarded:
        # use unique teller types
        unique_teller = init.unique_teller

        # unique teller service
        teller = Teller.query.filter_by(unique_id=unique_teller).first()
        # get this tellers service
        unique_teller_service = teller.service
        unique_teller_branch_id = teller.branch

        # get the teller bookings as teller forwardig only works for tellers forwarded
        bookings = Booking.query.filter_by(unique_teller=unique_teller).all()
        log(bookings)

        query = f"SELECT * FROM booking WHERE unique_teller = '{unique_teller}' AND serviced=0 AND nxt=1001"
        bookings = db.session.execute(query)
        bookings_ = [dict(x)["unique_id"] for x in bookings]

        forwarded_teller_bookings = f"SELECT * FROM booking WHERE service_name = '{unique_teller_service}' AND " \
                                    f"branch_id = {unique_teller_branch_id} AND serviced = 0 AND forwarded = 0 AND " \
                                    f"nxt =1001 AND date(date_added) < date('{init.start}') ORDER BY date_added DESC"

        data = db.session.execute(forwarded_teller_bookings)
        data_ = [x for x in data]
        inx = 0
        for index, x in enumerate(bookings_):
            if init.unique_id == x:
                inx = index

        final = len(bookings_[:inx]) + len(data_)

        # log(bookings_)
        # log(bookings_[:inx])
        # log(f"final : {final}")
    else:
        """
        Get teller by this booking service type and branch id 
        Then for all those tellers that offer the service that this booking offers 
        Get the forwarded booking there regardless of service but only get these forwarded one by the teller_unique 
        on bookings
        (This will include getting booking for all tellers and then summing up)
        """
        # use service_name and branch_id
        normal_teller = Teller.query.filter_by(service=init.service_name).filter_by(branch=init.branch_id).first()
        # tellers to work with
        tellers = Teller.query.filter_by(service=normal_teller.service).filter_by(branch=normal_teller.branch).all()

        log(f"Target Tellers ->{tellers}")
        # we are going to get the forwarded and get the max. why? we cannot predetermine the teller which will
        # service the booking
        bookings_final = list()
        forwarded_per_teller = list()
        for teller in tellers:
            bookings = Booking.query.filter_by(unique_teller=teller.unique_id).filter_by(serviced=False).filter_by(
                nxt=1001).all()
            bookings_final.append(bookings)
            forwarded_per_teller.append(len(bookings))
            # log(f"per teller data {teller.unique_id} -> {bookings}")
        # flatten the list
        log(forwarded_per_teller)
        # data_ = list(itertools.chain(*bookings_final))
        data_ = max(forwarded_per_teller) if len(forwarded_per_teller) else 0

        # convert it to a set to remove duplicates
        # get this teller_kind_bookings
        # get other booking that are not forwarded but belong to this teller type
        query = f"SELECT * FROM booking WHERE service_name = '{normal_teller.service}' AND branch_id = {normal_teller.branch} AND serviced = 0 AND forwarded = 0 AND nxt =1001"

        actual_teller_bookings = db.session.execute(query)
        data = [dict(x)["unique_id"] for x in actual_teller_bookings]
        inx = 0
        log(data)
        for index, x in enumerate(data):
            if init.unique_id == x:
                inx = index

        final = len(data[:inx]) + data_
        # log(f"CCC{data[:inx]}")
        # log(f"NOT {data_}")
        # log(f"this booking {init.unique_id}")
    return final


def ahead_of_you_id(booking_id):
    lookup = Booking.query.get(booking_id)
    if lookup:
        forwarded = bookings_forwared_to_this_teller_and_others_of_its_kind(booking_id)
        final = {"msg": forwarded}
    else:
        final = {"msg": None}

    return final


def booking_exists(branch, service, tckt):
    lookup = Booking.query.filter_by(branch_id=branch).filter_by(service_name=service).filter_by(ticket=tckt).first()
    data = booking_schema.dump(lookup)
    return data


def booking_exists_by_unique_id(unique_id):
    return Booking.query.filter_by(unique_id=unique_id).first()


@app.route("/booking/test", methods=["POST"])
def bkg_test():
    id = request.json["id"]
    return jsonify(booking_schema.dump(booking_exists_by_unique_id(id)))


def get_service_code(code, branch_id):
    lookup = ServiceOffered.query.filter_by(name=code).filter_by(branch_id=branch_id).first()
    data = service_schema.dump(lookup)
    return data


def log(msg):
    print(f"{datetime.now().strftime('%d:%m:%Y %H:%M:%S')} — {msg}")
    return True


'''here we are going to reset tickets every midnight'''


@sio.event
def connect():
    print('connection established')


@sio.event
def teller(data):
    sio.emit('teller', {'response': 'my response'})


@sio.event
def disconnect():
    print('disconnected from server')


def booking_is_serviced(unique_id):
    book = Booking.query.filter_by(unique_id=unique_id).first()
    return book.serviced


def booking_is_forwarded(unique_id):
    book = Booking.query.filter_by(unique_id=unique_id).first()
    return book.forwarded and book.unique_teller


def update_booking_by_unique_id(bookings):
    for booking in bookings:
        unique_id = booking["unique_id"]
        status = booking["serviced"]
        unique_teller = booking["unique_teller"]
        forwarded = booking["forwarded"]

        booking = booking_exists_by_unique_id(unique_id)
        if booking:
            if bool(status):
                if not booking_is_serviced(unique_id):
                    booking.serviced = True
                    db.session.commit()
                    
            if bool(forwarded):
                if unique_teller:
                    if not booking_is_forwarded(unique_id):
                        booking.forwarded = True
                        booking.unique_teller = unique_teller
                        db.session.commit()
                        
        else:
            # request offline data for sync
            sio.emit("booking_update", unique_id)
    return dict()


"""
syncing all offline data
"""


def ack_teller_fail(data):
    # check if it exists -> if true -> flag as synced if not { inform user of synced }  -> else trigger a sync
    teller = teller_exists_unique(data["data"]["unique_id"])
    if teller:
        if teller["is_synced"]:
            # teller is synced
            log("Teller Already Synced")
        else:
            # teller does not exists
            # trigger async
            sio.emit("add_teller", {"teller_data": data["data"]})


def ack_booking_fail(data):
    booking = booking_exists_unique(data)
    if booking:
        if booking.is_synced:
            # booking is synced
            log("Booking Already Synced")
        else:
            # booking is not synced
            # trigger async
            sio.emit("online_", {"booking_data": data})


def ack_service_fail(data):
    # check if it exists -> if true -> flag as synced if not { inform user of synced }  -> else trigger a sync
    service = service_exists_unique(data["data"]["unique_id"])
    if service:
        if service["is_synced"]:
            log("Service Already Synced")
        else:
            sio.emit("sync_service", data["data"])


def ack_teller_success(data):
    # flag as sycned here based on unique key
    return flag_teller_as_synced(data)


def ack_service_success(data):
    # flag as sycned here based on unique key
    return flag_service_as_synced(data)


def ack_booking_success(data):
    # flag as sycned here based on unique key
    return flag_booking_as_synced(data)


def teller_exists_unique(unique_id):
    return Teller.query.filter_by(unique_id=unique_id).first()


def service_exists_unique(unique_id):
    return ServiceOffered.query.filter_by(unique_id=unique_id).first()


def is_this_branch(key):
    return branch_exists_key(key)


def flag_booking_as_synced(data):
    booking = booking_exists_unique(data)
    if booking:
        booking.is_synced = True
        db.session.commit()
        
    return booking


def flag_service_as_synced(data):
    service = booking_exists_unique(data)
    if service:
        service.is_synced = True
        db.session.commit()
        
    return service


def flag_teller_as_synced(data):
    teller = booking_exists_unique(data)
    if teller:
        teller.is_synced = True
    return teller


# server 2 connection
try:
    sio.connect(socket_link)
except socketio.exceptions.ConnectionError:
    print("Error! Could not connect to the socket server.")
