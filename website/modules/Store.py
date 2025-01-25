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
from website.models import MSAccount, MSProduct, MSStore, MSRating


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
Store = Blueprint('Store', __name__)

# -------------------------------------------------------------

# STORE ROUTES

@Store.route('/Store/<int:id>', methods=['GET', 'POST'])
@login_required
@Check_Token
def show_store(id):
    # Get the store by ID
    store = MSStore.query.get(id)
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
    storename = MSStore.query.filter_by(id=id).first() 
    msstore_products = MSProduct.query.filter_by(StoreId=id).order_by(MSProduct.id.asc()).all()

    # Assuming msstore_products contains products fetched from the database
    for product in msstore_products:
        # Initialize average_rating to 0 by default
        average_rating = 0
            
        # Check if there are any ratings for the product in the MSRating table
        ratings_count = db.session.query(func.count(MSRating.id)).filter(MSRating.ProductId == product.id).scalar()

        if ratings_count > 0:
            # Calculate the average rating for the product only if there are ratings
            average_rating = db.session.query(func.avg(MSRating.Rate1)).filter(MSRating.ProductId == product.id).scalar()
            # Round to 1 decimal place
            average_rating = round(average_rating, 1) if average_rating is not None else 0

        # Add the average rating to the product object (or to the dictionary you're passing to the template)
        product.average_rating = average_rating

    if username.ProfilePic == None:
        ProfilePic=profile_default
    else:
        ProfilePic=username.ProfilePic
    
    if not store:
        return "Store not found", 404

    # Get the products associated with this store
    products = MSProduct.query.filter_by(StoreId=store.id, is_delete=False).all()

    # If there are no products, pass a flag to indicate no products
    if not products:
        return render_template('404/no_store.html', store_name=store.StoreName,
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               profile_pic=ProfilePic)
    
    # Perform the update using session.query instead of update()
    try:
        # Increment the visits count by 3 for the store
        store_to_update = MSStore.query.get(id)
        store_to_update.Visits += 1  # Increment visits count
        
        # Commit the transaction
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)

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
        return redirect(url_for('Store.StoreM')) 
                      
    return render_template("Client-Home-Page/Store/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               storename=storename,
                               msstore_products=msstore_products,
                               average_rating = average_rating,
                               product= product,
                               profile_pic=ProfilePic)
