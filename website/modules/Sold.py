from flask import Flask, Blueprint, abort, flash, json, make_response, redirect, render_template, request, jsonify, url_for
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from flask_login import login_user,login_required, logout_user, current_user, LoginManager
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from urllib.request import urlretrieve
from flask_mail import Mail,Message
from datetime import datetime, timedelta, timezone

import os,requests

from sqlalchemy.exc import IntegrityError  # Import this for catching database integrity errors
import traceback 


load_dotenv()

# IMPORT LOCAL FUNCTIONS
from website.API.authentication import *
from website.Token.token_gen import *
from website.Token.token_check import Check_Token

# IMPORT SMTP EMAILING FUNCTIONS

from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email

# DATABASE CONNECTION
from website.models import db
from sqlalchemy import update

# LOADING MODEL CLASSES
from website.models import MSAccount, MSProduct, MSStore, MSRating, MSCart, MSPurchase, MSPurchaseItem,MSNotification


# LOAD JWT MODULE
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, decode_token

# EXECUTING DATABASE

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

engine=create_engine(os.getenv('DATABASE_URI'), pool_pre_ping=True, pool_size=10, max_overflow=20, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -------------------------------------------------------------

# SMTP CONFIGURATION

app.config["MAIL_SERVER"]=os.getenv("MAILSERVER") 
app.config["MAIL_PORT"]=os.getenv("MAILPORT") 
app.config["MAIL_USERNAME"] = os.getenv("FISGMAIL")     
app.config['MAIL_PASSWORD'] = os.getenv("FISGMAILPASS")       
app.config['MAIL_DEFAULT_SENDER'] = 'PUPQC FIS'     
app.config['MAIL_USE_TLS']=False
app.config['MAIL_USE_SSL']=True


# -------------------------------------------------------------

# PYDRIVE AUTH CONFIGURATION
gauth = GoogleAuth()
drive = GoogleDrive(gauth)

# Default Profile Pic
profile_default=os.getenv("profile_default") 

# -------------------------------------------------------------
# WEB AUTH ROUTES URL
sold = Blueprint('sold', __name__)

# -------------------------------------------------------------

# SOLD ROUTES

@sold.route("/sold", methods=['GET', 'POST'])
@login_required
@Check_Token
def S_H():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first()
    
    # Default profile picture if not set
    if username.ProfilePic is None:
        ProfilePic = profile_default
    else:
        ProfilePic = username.ProfilePic

    # Fetch pending purchases for products owned by the current user
    pending_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId, MSPurchase.status == 'pending') \
        .all()
    
    packing_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId, MSPurchase.status == 'packing') \
        .all()
    
    delivering_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId, MSPurchase.status == 'delivering') \
        .all()
    
    received_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId, MSPurchase.status == 'received') \
        .all()
    
    cancelled_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId, MSPurchase.status == 'cancelled') \
        .all()
    
    # Sum the TotalPrice for each ProductOwnerId
    received_purchases_sum = db.session.query(
        func.sum(MSPurchaseItem.TotalPrice).label('total_price_sum')
    ).join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId, MSPurchase.status == 'received') \
        .scalar()  # Use scalar to get the result as a single value
    
    # If the sum is None, set it to 0
    if received_purchases_sum is None:
        received_purchases_sum = 0

    # Count notifications by status
    pending = len(pending_purchases)
    packing = len(packing_purchases)
    delivering = len(delivering_purchases)
    received = len(received_purchases)
    cancelled = len(cancelled_purchases)

    current_year = datetime.datetime.now().year

    orders_per_month = db.session.query(
        func.extract('month', MSPurchase.PurchaseDate).label('month'),  # Extract the month from the PurchaseDate
        func.count(MSPurchase.id).label('order_count')
    ) \
        .join(MSPurchaseItem, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId) \
        .filter(func.extract('year', MSPurchase.PurchaseDate) == current_year).group_by(func.extract('month', MSPurchase.PurchaseDate)) \
        .order_by(func.extract('month', MSPurchase.PurchaseDate)) \
        .all()

    # Prepare data for the chart
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    order_counts = [0] * 12  # Initialize the list for all months

    # Fill the order_counts list with the number of orders for each month
    for order in orders_per_month:
        order_counts[int(order.month) - 1] = order.order_count

    # Get the order count per day of the week (Sunday-Saturday)
    orders_per_week = db.session.query(
        func.extract('dow', MSPurchase.PurchaseDate).label('day_of_week'),  # Extract day of the week (1=Sunday, 7=Saturday)
        func.count(MSPurchase.id).label('order_count')
    ) \
        .join(MSPurchaseItem, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchaseItem.ProductOwnerId == current_user.MSId) \
        .filter(func.extract('year', MSPurchase.PurchaseDate) == current_year) \
        .group_by(func.extract('dow', MSPurchase.PurchaseDate)) \
        .order_by(func.extract('dow', MSPurchase.PurchaseDate)) \
        .all()

    # Prepare the data for the chart (per week data)
    order_counts_week = [0] * 7  # Initialize the list for each day of the week

    for order in orders_per_week:
        order_counts_week[int(order.day_of_week) - 1] = order.order_count  # Map the data to correct day


    return render_template(
        "Client-Home-Page/Sold/index.html",
        User=username.FirstName + " " + username.LastName,
        user=current_user,
        received=received,
        packing=packing,
        delivering=delivering,
        pending=pending,
        canceled=cancelled,
        profile_pic=ProfilePic,

        received_purchases_sum=received_purchases_sum,
        pending_purchases=pending_purchases,
        packing_purchases=packing_purchases,
        delivering_purchases=delivering_purchases,
        received_purchases=received_purchases,
        cancelled_purchases=cancelled_purchases,

        order_counts=order_counts,  # Existing data for per month
        order_counts_week=order_counts_week,  # New data for per week
    )

        