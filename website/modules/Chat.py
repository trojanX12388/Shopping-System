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
from sqlalchemy import and_, or_


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
from website.models import MSAccount, MSProduct, MSStore, MSRating, MSMessage, MSFollowing


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

@Chat.route('/get_messages/<sender_id>/<receiver_id>', methods=['GET'])
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

        # Fetch MSFollowing relationship
        ms_following = MSFollowing.query.filter(
            (MSFollowing.MSId == sender_id) & (MSFollowing.FollowId == receiver_id) |
            (MSFollowing.FollowId == receiver_id) & (MSFollowing.MSId == sender_id)
        ).first()  # Assuming MSFollowing is one-to-one or you'd want the first match

        # Prepare messages with sender's profile picture and following status
        message_list = [{
            'sender_id': message.sender_id,
            'receiver_id': message.receiver_id,
            'content': message.content,
            'timestamp': message.timestamp,
            'sender': {
                'FirstName': message.sender.FirstName,
                'LastName': message.sender.LastName,
                'ProfilePic': message.sender.ProfilePic  # Include the ProfilePic here
            },
            'receiver': {
                'ProfilePic': message.sender.ProfilePic  # Include the ProfilePic here
            },
            'is_following': ms_following is not None  # Check if sender and receiver are following each other
        } for message in messages]

        return jsonify(message_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@Chat.route('/send_message', methods=['POST'])
@login_required
@Check_Token
def send_message():
    try:
        data = request.get_json()
        sender_id = data['sender_id']
        receiver_id = data['receiver_id']
        content = data['content']

        # Check if sender follows receiver
        following = MSFollowing.query.filter_by(MSId=sender_id, FollowId=receiver_id).first()
        
        if not following:
            return jsonify({'error': 'You can only message users you follow'}), 403

        # Create and store the message
        message = MSMessage(sender_id=sender_id, receiver_id=receiver_id, content=content)
        db.session.add(message)
        db.session.commit()

        return jsonify({'message': 'Message sent successfully!'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@Chat.route('/get_users', methods=['GET'])
@login_required
@Check_Token
def get_users():
    try:
        # Fetch only users that the current user follows
        followed_users = MSFollowing.query.filter_by(MSId=current_user.MSId).all()

        if not followed_users:
            return jsonify({'error': 'You are not following any users'}), 404

        # Extract the IDs of followed users
        followed_user_ids = [user.FollowId for user in followed_users]

        # Fetch the MSAccount details of followed users
        users = MSAccount.query.filter(MSAccount.MSId.in_(followed_user_ids)).all()

        user_list = [{
            'MSId': user.MSId,
            'FirstName': user.FirstName,
            'LastName': user.LastName,
            'ProfilePic': user.ProfilePic
        } for user in users]

        return jsonify(user_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@Chat.route('/follow/<seller_id>', methods=['POST'])
@login_required
@Check_Token
def follow_user(seller_id):
    try:
        # Ensure the seller exists
        seller = MSAccount.query.filter_by(MSId=seller_id).first()
        if not seller:
            return jsonify({'error': 'Seller not found'}), 404

        # Check if the current user is already following the seller
        existing_follow = MSFollowing.query.filter_by(MSId=current_user.MSId, FollowId=seller_id).first()
        if existing_follow:
            return jsonify({'message': 'You are already following this user', 'isFollowing': True}), 200

        # Add the follow relationship to the MSFollowing table
        new_follow = MSFollowing(MSId=current_user.MSId, FollowId=seller_id)
        db.session.add(new_follow)
        db.session.commit()

        return jsonify({'message': 'You are now following the seller!', 'isFollowing': True}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@Chat.route('/unfollow/<seller_id>', methods=['POST'])
@login_required
@Check_Token
def unfollow_user(seller_id):
    try:
        # Ensure the seller exists
        seller = MSAccount.query.filter_by(MSId=seller_id).first()
        if not seller:
            return jsonify({'error': 'Seller not found'}), 404

        # Check if the current user is following the seller
        existing_follow = MSFollowing.query.filter_by(MSId=current_user.MSId, FollowId=seller_id).first()
        if not existing_follow:
            return jsonify({'message': 'You are not following this user', 'isFollowing': False}), 200

        # Remove the follow relationship
        db.session.delete(existing_follow)
        db.session.commit()

        return jsonify({'message': 'You have unfollowed the seller!', 'isFollowing': False}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@Chat.route('/check-following-status', methods=['POST'])
@login_required
@Check_Token
def check_following_status():
    try:
        # Get the sellerId from the request payload
        data = request.get_json()
        seller_id = data.get('sellerId')

        # Ensure the seller exists
        seller = MSAccount.query.filter_by(MSId=seller_id).first()
        if not seller:
            return jsonify({'error': 'Seller not found'}), 404

        # Check if the current user is following the seller
        existing_follow = MSFollowing.query.filter_by(MSId=current_user.MSId, FollowId=seller_id).first()
        is_following = True if existing_follow else False

        return jsonify({'isFollowing': is_following}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


