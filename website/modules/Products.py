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
from website.models import MSAccount, MSProduct, MSStore, MSRating, MSCart


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
products = Blueprint('products', __name__)

# -------------------------------------------------------------

# PRODUCTS ROUTES

@products.route("/products", methods=['GET', 'POST'])
@login_required
@Check_Token
def ProductsM():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
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
            return redirect(url_for('products.ProductsM')) 
                      
        return render_template("Client-Home-Page/My-Product/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               store=MSProduct.MSStore,
                               profile_pic=ProfilePic)


@products.route("/products/add-record", methods=['GET', 'POST'])
@login_required
def ProductsAdd():
        
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        
        name = request.form.get('name')
        description = request.form.get('description')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        store = request.form.get('store')
        
        file =  request.form.get('base64')
        ext = request.files.get('fileup')
        ext = ext.filename
        
        id = f'{str(username.MSId)}{str(name)}'
        
        StoreId = MSStore.query.filter_by(id=store).first() 

        # PRODUCT IMAGE FOLDER ID
        folder = '1C2WKjnNSUIzKTaDeFUdPWariYEpLHWZz'
        
        url = """data:image/png;base64,{}""".format(file)
                
        filename, m = urlretrieve(url)


        file_list = drive.ListFile({'q': "'%s' in parents and trashed=false"%(folder)}).GetList()
        try:
            for file1 in file_list:
                if file1['title'] == str(id):
                    file1.Delete()                
        except:
            pass
        # CONFIGURE FILE FORMAT AND NAME
        file1 = drive.CreateFile(metadata={
            "title": ""+ str(id),
            "parents": [{"id": folder}],
            "mimeType": "image/png"
            })
        
        # GENERATE FILE AND UPLOAD
        file1.SetContentFile(filename)
        file1.Upload()
        
        add_record = MSProduct(ProductName=name,
                               ProductDescription=description,
                               ProductStock=quantity,
                               ProductPrice=price,
                               StoreId=StoreId.id,
                               ProductImage='%s'%(file1['id']),
                               MSId = current_user.MSId)
        
        db.session.add(add_record)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('products.ProductsM'))
            
           
@products.route("/products/delete-record", methods=['GET', 'POST'])
@login_required
def ProductsDel():
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 

        id = request.form.get('id')
        
        
        data = MSProduct.query.filter_by(id=id).first() 
        
        if data:
            id = f'{str(username.MSId)}{str(data.ProductName)}'
        
            # INSTRUCTIONAL MATERIAL FOLDER ID
            folder = '1C2WKjnNSUIzKTaDeFUdPWariYEpLHWZz'
        
            # CLEAR PROFILE PIC
            file_list = drive.ListFile({'q': "'%s' in parents and trashed=false"%(folder)}).GetList()
            try:
                for file1 in file_list:
                    if file1['title'] == str(id):
                        file1.Delete()                
            except:
                pass

            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('products.ProductsM'))        

        

@products.route("/products/view/<int:id>", methods=['GET', 'POST'])
@login_required
@Check_Token
def ProductsV(id):
        

    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        
        product = MSProduct.query.filter_by(id=id).first() 
        msstore_products = MSProduct.query.filter_by(id=id).order_by(MSProduct.id.asc()).all()

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
        
        # Perform the update using session.query instead of update()
        try:
            # Retrieve the store record by ID
            store_to_update = MSProduct.query.get(id)
            
            if store_to_update:
                # Check if ProductViews is None
                if store_to_update.ProductViews is None:
                    store_to_update.ProductViews = 1  # Initialize to 1 if null
                else:
                    store_to_update.ProductViews += 1  # Increment by 1 if not null
                
                # Commit the transaction
                db.session.commit()
            else:
                return "Store with the given ID not found."
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
            return redirect(url_for('products.ProductsM')) 
                      
        return render_template("Client-Home-Page/My-Product/view-product.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               product=product,
                               average_rating = average_rating,
                               profile_pic=ProfilePic)



@products.route("/products/add-to-cart", methods=['GET', 'POST'])
@login_required
def ProductsAddC():
        
        prid = request.form.get('prid')
        prname = request.form.get('prname')
        prowner = request.form.get('prowner')
        
        add_record = MSCart(notif_by=prowner,
                               ProductId=prid,
                               Notification=prname,
                               notifier_type="Faculty",
                               Type="notif",
                               Status="pending",
                               MSId = current_user.MSId)
        
        db.session.add(add_record)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('products.ProductsV', id=prid))


@products.route("/products/to-cart", methods=['GET', 'POST'])
@login_required
def ProductsAddTC():
        
        stid = request.form.get('stid')
        prid = request.form.get('prid')
        prname = request.form.get('prname')
        prowner = request.form.get('prowner')
        
        add_record = MSCart(notif_by=prowner,
                               ProductId=prid,
                               Notification=prname,
                               notifier_type="Faculty",
                               Type="notif",
                               Status="pending",
                               MSId = current_user.MSId)
        
        db.session.add(add_record)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('Store.show_store', id=stid))



