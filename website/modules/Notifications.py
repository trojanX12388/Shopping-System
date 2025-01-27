from flask import Flask, Blueprint, abort, flash, json, make_response, redirect, render_template, request, jsonify, url_for
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from flask_login import login_user,login_required, logout_user, current_user, LoginManager
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
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
from website.models import MSAccount, MSCart, MSProduct, MSNotification


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
profile_default='14wkc8rPgd8NcrqFoRFO_CNyrJ7nhmU08'

# -------------------------------------------------------------
# WEB AUTH ROUTES URL
notification = Blueprint('notification', __name__)

# -------------------------------------------------------------

# FACULTY NOTIFICATION API 

  
@notification.route('/api/Faculty/Notifications', methods=['GET', 'POST'])
@login_required
@Check_Token
def notificationFaculty_func():
    
    # Fetch all data from FISRequests
    requests = MSCart.query.filter_by(MSId=current_user.MSId).all() 
    
    # Create a list to store the selected fields for each log entry
    formatted_requests = []
  
    # Iterate over the logs and extract the required fields
    for request in requests:
        # Determine whether it's a Faculty or Admin log entry
        
        # Fetch FirstName from MSAccount or FISAdmin based on identifier_type
        notifier_name = None
        
        
        identifier_entry = MSAccount.query.filter_by(MSId=request.notif_by).first()


        if identifier_entry:
                notifier_name = identifier_entry.FirstName + " " + identifier_entry.LastName
            
            
        # Create a dictionary with the required data
        formatted_request = {
                'id': request.id,
                'DateTime': request.DateTime.strftime("%Y-%m-%d %H:%M:%S"),  # Format datetime as string
                'Status': request.Status,
                'Type': request.Type,
                'Notification': request.Notification,
                'Price': request.MSProduct.ProductPrice,
                'ProductImage': request.MSProduct.ProductImage,
                'IdentifierType': request.notifier_type,
                'updated_at': request.updated_at.strftime("%Y-%m-%d %H:%M:%S"), 
            }

        formatted_requests.append(formatted_request)
        
    # Create a dictionary with the required data
    api_response_data = {
        'requests': formatted_requests
    }

    # Return the data as JSON using Flask's jsonify
    return jsonify(api_response_data)



@notification.route("/notifications")
@login_required
@Check_Token
def notifications():
    # Get all unread notifications for the current user
    user_notifications = MSNotification.query.filter_by(user_id=current_user.MSId, is_seen=False).all()

    # Render notifications page
    return render_template('notifications.html', notifications=user_notifications)


@notification.route("/notifications/mark_seen/<int:notification_id>")
@login_required
@Check_Token
def mark_notification_seen(notification_id):
    notification = MSNotification.query.get(notification_id)
    
    if notification and notification.user_id == current_user.MSId:
        notification.is_seen = True
        db.session.commit()

    return redirect(url_for('notification.notifications'))

@notification.route('/api/purchase/notifications', methods=['GET'])
@login_required
@Check_Token
def purchase_notifications():
    # Fetch all unread notifications for the current user
    user_notifications = MSNotification.query.filter_by(user_id=current_user.MSId, is_seen=False).all()

    # Create a list to store the formatted notifications
    formatted_notifications = []

    for notification in user_notifications:
        # Get the related product from the notification (if it exists)
        product = MSProduct.query.get(notification.product_id) if notification.product_id else None

        # Format the notification details (adjust as per your requirements)
        formatted_notification = {
            'id': notification.id,
            'Notification': notification.message,  # Using 'Notification' for consistency with frontend
            'DateTime': notification.created_at.strftime("%Y-%m-%d %H:%M:%S"),  # Format the timestamp as a string
            'Status': notification.purchase_item.MSPurchase.status,  # Assuming 'Status' is pending (change based on your logic)
            'Price': notification.purchase_item.TotalPrice if product else None,  # Fetch the price of the related product if exists
            'Quantity': notification.purchase_item.Quantity if product else None,  # Fetch the price of the related product if exists
            'ProductImage': product.ProductImage if product else "sample_image_url",  # Use product's image URL
            'Type': "purchase",  # Can be dynamic depending on the notification type
            'updated_at': notification.created_at.strftime("%Y-%m-%d %H:%M:%S")  # Optional: last update timestamp
        }

        # Append the formatted notification to the list
        formatted_notifications.append(formatted_notification)

    # Create a dictionary with the notifications (change key from 'notifications' to 'requests' for consistency)
    api_response_data = {
        'requests': formatted_notifications
    }

    # Return the data as JSON
    return jsonify(api_response_data)