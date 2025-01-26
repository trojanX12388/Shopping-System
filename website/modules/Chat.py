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
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
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
from website.models import MSAccount, MSProduct, MSStore, MSRating, MSMessage


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
Chat = Blueprint('Chat', __name__)

# -------------------------------------------------------------

# STORE ROUTES

@Chat.route('/chat', methods=['GET', 'POST'])
@login_required
@Check_Token
def ChatH():
    
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
    
    if username.ProfilePic == None:
        ProfilePic=profile_default
    else:
        ProfilePic=username.ProfilePic
    
        # UPDATE 
    if request.method == 'POST':
         
        # VALUES
           
        name = request.form.get('name')
        description = request.form.get('description')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        store = request.form.get('store')
        id = request.form.get('id')
        StoreId = MSStore.query.filter_by(id=store).first() 

        u = update(MSProduct)
        u = u.values({"ProductName": name,
                          "ProductDescription": description,
                          "ProductStock": quantity,
                          "ProductPrice": price,
                          "StoreId": StoreId.id,
                          })
        u = u.where(MSProduct.id == id)
        db.session.execute(u)
        db.session.commit()
        db.session.close()
        return redirect(url_for('Chat.ChatH')) 
                      
    return render_template("Client-Home-Page/Chat/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               profile_pic=ProfilePic)


@Chat.route('/get_messages/<int:sender_id>/<int:receiver_id>', methods=['GET'])
@login_required
@Check_Token
def get_messages(sender_id, receiver_id):
    try:
        # Fetch messages between sender and receiver
        messages = MSMessage.query.filter(
            ((MSMessage.sender_id == sender_id) & (MSMessage.receiver_id == receiver_id)) |
            ((MSMessage.sender_id == receiver_id) & (MSMessage.receiver_id == sender_id))
        ).all()

        # Check if messages were found
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        # Prepare messages with sender's profile picture
        message_list = [{
            'sender_id': message.sender_id,
            'receiver_id': message.receiver_id,
            'content': message.content,
            'timestamp': message.timestamp,
            'sender': {
                'FirstName': message.sender.FirstName,
                'LastName': message.sender.LastName,
                'ProfilePic': message.sender.ProfilePic  # Include the ProfilePic here
            }
        } for message in messages]

        return jsonify(message_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@Chat.route('/send_message', methods=['POST'])
@login_required
@Check_Token
def send_message():
    data = request.get_json()
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content']

    message = MSMessage(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully!'})

@Chat.route('/get_users', methods=['GET'])
@login_required
@Check_Token
def get_users():
    users = MSAccount.query.all()  # Query to get all users
    user_list = [{
        'MSId': user.MSId,
        'FirstName': user.FirstName,
        'LastName': user.LastName,
        'ProfilePic': user.ProfilePic  # Add the profile picture
    } for user in users]

    return jsonify(user_list)
