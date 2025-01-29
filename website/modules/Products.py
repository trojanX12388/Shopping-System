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
from sqlalchemy import update, desc

# LOADING MODEL CLASSES
from website.models import MSAccount, MSProduct, MSStore, MSRating, MSCart, MSPurchaseItem, MSNotification


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

# Helper function to calculate average rating
def calculate_average_rating(product_id):
    """Calculate and return the average rating for a product."""
    ratings_count = db.session.query(func.count(MSRating.id)).filter(MSRating.ProductId == product_id).scalar()
    
    if ratings_count > 0:
        average_rating = db.session.query(func.avg(MSRating.Rate1)).filter(MSRating.ProductId == product_id).scalar()
        return round(average_rating, 1) if average_rating is not None else 0
    return 0


@products.route("/products", methods=['GET', 'POST'])
@login_required
@Check_Token
def ProductsM():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
    
    # Set default profile picture if none exists
    ProfilePic = username.ProfilePic if username.ProfilePic else profile_default

    # Retrieve non-deleted stores
    stores = MSStore.query.filter((MSStore.is_delete == False) | (MSStore.is_delete.is_(None))).all()
    msstore_products = MSProduct.query.filter(MSProduct.is_delete == False).order_by(MSProduct.id.asc()).all()

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

    # Handle POST request for updating products
    if request.method == 'POST':
        # VALUES
        name = request.form.get('name')
        description = request.form.get('description')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        store = request.form.get('store')
        itemid = request.form.get('id')
        StoreId = MSStore.query.filter_by(id=store).first()
        
        # Get base64 image and file upload
        file = request.form.get('base64')
        ext = request.files.get('fileup')
        
        # Generate product ID
        id = f'{str(username.MSId)}{str(name)}'
        
        # PRODUCT IMAGE FOLDER ID
        folder = '1C2WKjnNSUIzKTaDeFUdPWariYEpLHWZz'
        
        if ext:  # Only process image if a new file is provided
            ext = ext.filename
            
            url = """data:image/png;base64,{}""".format(file)
            filename, m = urlretrieve(url)

            # DELETE EXISTING IMAGE WITH SAME TITLE IN THE FOLDER
            file_list = drive.ListFile({'q': "'%s' in parents and trashed=false" % folder}).GetList()
            try:
                for file1 in file_list:
                    if file1['title'] == str(id):
                        file1.Delete()
            except Exception as e:
                print(f"Error deleting file: {e}")
            
            # CONFIGURE FILE FORMAT AND NAME
            file1 = drive.CreateFile(metadata={
                "title": str(id),
                "parents": [{"id": folder}],
                "mimeType": "image/png"
            })
            
            # GENERATE FILE AND UPLOAD
            file1.SetContentFile(filename)
            file1.Upload()
            
            # Set product image to the newly uploaded file ID
            product_image_id = file1['id']
        else:
            # Retain the existing product image if no new file is uploaded
            existing_product = MSProduct.query.filter_by(id=itemid).first()
            product_image_id = existing_product.ProductImage

        # Update product details
        u = update(MSProduct)
        u = u.values({
            "ProductName": name,
            "ProductDescription": description,
            "ProductStock": quantity,
            "ProductImage": product_image_id,  # New or existing image ID
            "ProductPrice": price,
            "StoreId": StoreId.id,
        })
        u = u.where(MSProduct.id == itemid)
        db.session.execute(u)
        db.session.commit()
        db.session.close()

        # Redirect back to the products page
        return redirect(url_for('products.ProductsM'))
    
    # Render template with user and store data
    return render_template(
        "Client-Home-Page/My-Product/index.html",
        User=f"{username.FirstName} {username.LastName}",
        user=current_user,
        store=MSProduct.MSStore,
        stores=stores,
        products=msstore_products,
        average_rating=average_rating,
        profile_pic=ProfilePic
    )

                      

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
            
           
@products.route("/products/delete-record", methods=['POST'])
@login_required
def ProductsDel():
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first()

    # Get the product ID from the form
    product_id = request.form.get('id')

    # Find the product in the database
    data = MSProduct.query.filter_by(id=product_id).first()

    if data:
        # Build the folder name
        id_str = f'{str(username.MSId)}{str(data.ProductName)}'

        # Instructional material folder ID
        folder = '1C2WKjnNSUIzKTaDeFUdPWariYEpLHWZz'

        # Clear profile picture in Google Drive
        file_list = drive.ListFile({'q': f"'{folder}' in parents and trashed=false"}).GetList()
        try:
            for file1 in file_list:
                if file1['title'] == str(id_str):
                    file1.Delete()
        except:
            pass

        # Use a no_autoflush block to avoid premature flush
        with db.session.no_autoflush:
            # Delete related rows in MSNotification
            MSPurchaseItem_ids = MSPurchaseItem.query.with_entities(MSPurchaseItem.id).filter_by(ProductId=data.id).all()
            MSPurchaseItem_ids = [item.id for item in MSPurchaseItem_ids]

            if MSPurchaseItem_ids:
                MSNotification.query.filter(MSNotification.purchase_item_id.in_(MSPurchaseItem_ids)).delete(synchronize_session=False)

            # Delete related MSPurchaseItem rows
            MSPurchaseItem.query.filter_by(ProductId=data.id).delete()

            # Delete related MSCart rows
            MSCart.query.filter_by(ProductId=data.id).delete()

            # Delete the product
            db.session.delete(data)

            # Commit changes
            db.session.commit()

        db.session.close()
        return redirect(url_for('products.ProductsM'))

    flash('Product not found.', 'danger')
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
        ratings_count = db.session.query(func.count(MSRating.id)).filter(
            MSRating.ProductId == product.id,
            MSRating.Rate1.isnot(None)  # Ensure Rate1 is not NULL
        ).scalar()

        if ratings_count > 0:
            # Calculate the average rating for the product only if there are ratings
            average_rating = db.session.query(func.avg(MSRating.Rate1)).filter(
                MSRating.ProductId == product.id,
                MSRating.Rate1.isnot(None)
            ).scalar()
            # Round to 1 decimal place
            average_rating = round(average_rating, 1) if average_rating is not None else 0

        # Add the average rating to the product object
        product.average_rating = average_rating

    ProfilePic = username.ProfilePic if username.ProfilePic else profile_default

    # Perform the update using session.query instead of update()
    try:
        store_to_update = MSProduct.query.get(id)
        if store_to_update:
            if store_to_update.ProductViews is None or store_to_update.ProductViews <= 0:
                store_to_update.ProductViews = 1  # Initialize to 1 if null or invalid
            else:
                store_to_update.ProductViews += 1  # Increment by 1
            db.session.commit()
        else:
            return "Store with the given ID not found."
    except Exception as e:
        db.session.rollback()
        return str(e)

    # Fetch Reviews for the product
    reviews = db.session.query(
        MSRating.Rate1, 
        MSRating.Review, 
        MSAccount.FirstName, 
        MSAccount.LastName, 
        MSAccount.ProfilePic
    ).join(MSAccount, MSAccount.MSId == MSRating.MSId) \
     .filter(
         MSRating.ProductId == id,
         MSRating.Rate1.isnot(None)  # Ensure Rate1 is not NULL
     ).order_by(MSRating.id.desc()).all()
    
    most_recommended_products = (
                        MSProduct.query
                        .join(MSRating, MSProduct.id == MSRating.ProductId)
                        .order_by(desc(MSRating.Rate1), desc(MSProduct.ProductViews))
                        .limit(10)
                        .all()
                    )
        
    # Assuming msstore_products contains products fetched from the database
    for recommend in most_recommended_products:
        # Initialize average_rating to 0 by default
        recom_average_rating = 0
                
        # Check if there are any ratings for the product in the MSRating table
        ratings_count = db.session.query(func.count(MSRating.id)).filter(MSRating.ProductId == recommend.id).scalar()

        if ratings_count > 0:
            # Calculate the average rating for the product only if there are ratings
            recom_average_rating = db.session.query(func.avg(MSRating.Rate1)).filter(MSRating.ProductId == recommend.id).scalar()
            # Round to 1 decimal place
            recom_average_rating = round(recom_average_rating, 1) if recom_average_rating is not None else 0

        # Add the average rating to the product object (or to the dictionary you're passing to the template)
        recommend.recom_average_rating = recom_average_rating
    return render_template(
        "Client-Home-Page/My-Product/view-product.html", 
        User=username.FirstName + " " + username.LastName,
        user=current_user,
        product=product,
        average_rating=average_rating,
        profile_pic=ProfilePic,
        most_recommended_products=most_recommended_products,
        recom_average_rating = recom_average_rating,
        reviews=reviews  # Pass reviews to the template
    )



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



@products.route("/products/remove-from-cart", methods=['POST'])
@login_required
def ProductsRemoveFromCart():
    # Get the product ID from the form data
    prid = request.form.get('prid')
    
    # Query the cart to find the item associated with the product ID and current user
    cart_item = MSCart.query.filter_by(ProductId=prid, MSId=current_user.MSId).first()
    
    if cart_item:
        # Remove the item from the cart
        db.session.delete(cart_item)
        db.session.commit()
    
    # Redirect to the store page after removal
    return redirect(url_for('purchase.C_H'))


@products.route("/products/rate-product", methods=['POST'])
@login_required
def rate_product():
    # Get product ID, rating, and review from the form
    prid = request.form.get('prid')
    rating = request.form.get('rating')
    review = request.form.get('review')

    # Check if the product and user exist
    existing_rating = MSRating.query.filter_by(ProductId=prid, MSId=current_user.MSId).first()

    if existing_rating:
        # Update the existing rating and review
        existing_rating.Rate1 = rating
        existing_rating.Review = review
    else:
        # Add a new rating record with the review
        new_rating = MSRating(
            ProductId=prid,
            MSId=current_user.MSId,
            Rate1=rating,
            Review=review
        )
        db.session.add(new_rating)

    # Commit changes to the database
    db.session.commit()
    return redirect(url_for('purchase.C_H'))



