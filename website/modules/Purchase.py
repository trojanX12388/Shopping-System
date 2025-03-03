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
purchase = Blueprint('purchase', __name__)

# -------------------------------------------------------------

# PURCHASE ROUTES

@purchase.route("/purchase/<int:id>", methods=['GET', 'POST'])
@login_required
@Check_Token
def Purchase(id):
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        
    if username.ProfilePic == None:
        ProfilePic=profile_default
    else:
        ProfilePic=username.ProfilePic
    # Fetch product details
    product = MSProduct.query.filter_by(id=id).first()
    if not product:
        return "Product not found", 404

    # Handle POST request to confirm purchase
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity'))
        product_price = float(request.form.get('product_price'))
        total_amount = quantity * product_price

        # Check stock availability
        if quantity > product.ProductStock:
            return "Insufficient stock available", 400

        # Create a new purchase record
        new_purchase = MSPurchase(
            MSId=current_user.MSId,  # Logged-in user
            StoreId=product.StoreId,
            TotalAmount=total_amount,
            status="pending"  # Initial status
        )
        db.session.add(new_purchase)
        db.session.flush()  # Get the new purchase ID without committing

        # Create a purchase item record
        purchase_item = MSPurchaseItem(
            PurchaseId=new_purchase.id,
            ProductId=product_id,
            Quantity=quantity,
            UnitPrice=product_price,
            TotalPrice=total_amount
        )
        db.session.add(purchase_item)

        # Update product stock
        product.ProductStock -= quantity

        # Commit all changes
        try:
            db.session.commit()
            return redirect(url_for('purchase.PurchaseSuccess', purchase_id=new_purchase.id))
        except Exception as e:
            db.session.rollback()
            return str(e), 500

    return render_template(
        "Client-Home-Page/Purchase/purchase-product.html",
        product=product,
        user=current_user,
        User= username.FirstName + " " + username.LastName,
        profile_pic=ProfilePic
    )

@purchase.route("/purchase/success/<int:purchase_id>")
@login_required
@Check_Token
def PurchaseSuccess(purchase_id):
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
    if username.ProfilePic == None:
        ProfilePic=profile_default
    else:
        ProfilePic=username.ProfilePic

    purchase = MSPurchase.query.get(purchase_id)
    product = MSPurchaseItem.query.filter_by(PurchaseId=purchase_id).first()
    if not purchase:
        return "Purchase not found", 404

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
        "Client-Home-Page/Purchase/purchase-success.html",
        purchase=purchase,
        product=product,
        user=current_user,
        most_recommended_products=most_recommended_products,
        recom_average_rating = recom_average_rating,
        User= username.FirstName + " " + username.LastName,
        profile_pic=ProfilePic,
    )
@purchase.route("/purchase/confirm", methods=["POST"])
@login_required
@Check_Token
def confirm_purchase():
    # Fetch the data from the form
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity"))
    product_price = float(request.form.get("product_price"))
    total_amount = quantity * product_price
    shipping_type = request.form.get("shipping_type")  # Get shipping type (walkin or delivery)
    shipping_address = request.form.get("shipping_address") if shipping_type == "delivery" else None  # Address is required only for delivery

    # Fetch the product and the owner (MSAccount)
    product = MSProduct.query.filter_by(id=product_id).first()
    if not product:
        return "Product not found"
    
    owner = MSAccount.query.filter_by(MSId=product.MSId).first()  # Get the owner of the product
    if not owner:
        return "Product owner not found"

    # Check if there is enough stock to fulfill the purchase
    if product.ProductStock < quantity:
        return "Not enough stock available"

    # Create a new purchase record
    purchase = MSPurchase(
        MSId=current_user.MSId,  # The buyer
        StoreId=product.StoreId,
        TotalAmount=total_amount,
        is_complete=False,  # Default status
        status='pending',  # Set initial status as 'pending'
        shipping_type=shipping_type,
        shipping_address=shipping_address  # Store the shipping address if applicable
    )
    db.session.add(purchase)
    db.session.commit()  # Commit to save the purchase record

    # Create a purchase item for the purchased product
    purchase_item = MSPurchaseItem(
        PurchaseId=purchase.id,
        ProductId=product.id,
        Quantity=quantity,
        UnitPrice=product.ProductPrice,
        TotalPrice=total_amount,
        ProductOwnerId=product.MSId  # Set the owner of the product
    )
    db.session.add(purchase_item)
    db.session.commit()  # Commit the item record to the database

    # Update the product stock by subtracting the purchased quantity
    product.ProductStock -= quantity  # Subtract the purchased quantity from the stock
    db.session.commit()  # Commit the stock update

    # Create a notification for the product owner
    notification_message = f"You have a new purchase! {quantity} unit(s) of {product.ProductName} has been purchased."
    notification = MSNotification(
        user_id=owner.MSId,
        message=notification_message,
        product_id=product.id,  # Add the product_id for reference in the notification
        purchase_item_id=purchase_item.id  # Add the purchase item ID for reference
    )
    db.session.add(notification)
    db.session.commit()

    # Return a response, redirecting to the view purchase page
    return redirect(url_for("purchase.view_purchase", purchase_id=purchase_item.PurchaseId))



@purchase.route("/purchase/update-status/<int:purchase_item_id>", methods=["POST"])
@login_required
@Check_Token
def update_status(purchase_item_id):
    # Get the purchase item based on the provided ID
    purchase_item = MSPurchaseItem.query.get(purchase_item_id)
    
    # Check if the purchase item exists and belongs to the current user
    if not purchase_item or purchase_item.ProductOwnerId != current_user.MSId:
        return jsonify({"success": False, "message": "You are not the owner of this product."}), 403

    # Get the new status from the request JSON data
    new_status = request.json.get("status")

    # Validate the new status
    if new_status not in ["pending", "packing", "delivering", "delivered", "cancelled", "received", "trash"]:
        return jsonify({"success": False, "message": "Invalid status."}), 400

    try:
        # Update the status of the purchase item
        purchase_item.MSPurchase.status = new_status  # Update the parent purchase's status
        db.session.commit()

        # Return a JSON response on success
        return jsonify({
            "success": True,
            "message": "Status updated successfully.",
            "new_status": new_status
        }), 200

    except Exception as e:
        # Handle any unexpected errors
        return jsonify({"success": False, "message": "An error occurred.", "error": str(e)}), 500



@purchase.route("/purchase/success/<int:purchase_id>")
@login_required
@Check_Token
def view_purchase(purchase_id):
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
    if username.ProfilePic == None:
        ProfilePic=profile_default
    else:
        ProfilePic=username.ProfilePic

    purchase = MSPurchase.query.get(purchase_id)
    product = MSPurchaseItem.query.filter_by(PurchaseId=purchase_id).first()
    if not purchase:
        return "Purchase not found", 404

    return render_template(
        "Client-Home-Page/Purchase/purchase-success.html",
        purchase=purchase,
        product=product,
        user=current_user,
        User= username.FirstName + " " + username.LastName,
        profile_pic=ProfilePic,
    )


@purchase.route("/cart", methods=['GET', 'POST'])
@login_required
@Check_Token
def C_H():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first()
    
    # Default profile picture if not set
    if username.ProfilePic is None:
        ProfilePic = profile_default
    else:
        ProfilePic = username.ProfilePic

    # Query to get the count of each status
    pending_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchase.status == 'pending') \
        .all()

    packing_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchase.status == 'packing') \
        .all()

    received_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchase.status == 'received') \
        .all()

    delivering_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchase.status == 'delivering') \
        .all()
    
    cancelled_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchase.status == 'cancelled') \
        .all()
    
    purchased_items = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .all()

    # Count notifications by status
    pending = len(pending_purchases)
    packing = len(packing_purchases)
    delivering = len(delivering_purchases)
    received = len(received_purchases)
    cancelled = len(cancelled_purchases)

    purchase = len(purchased_items)

    cart_items = MSCart.query.filter_by(MSId=current_user.MSId).all()
    cart = len(cart_items)

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
        "Client-Home-Page/Purchase/My-Purchase.html",
        User=username.FirstName + " " + username.LastName,
        user=current_user,
        profile_pic=ProfilePic,
        purchase = purchase,
        cart = cart,
        orders = pending + packing,
        delivering = delivering,
        received = received,
        cancelled = cancelled,

        most_recommended_products=most_recommended_products,
        recom_average_rating = recom_average_rating,

        purchased_items=purchased_items,
    )
        
@purchase.route('/cart/invoice/<int:id>')
@login_required
@Check_Token
def C_I(id):
    # Fetch user details
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first()
    if username.ProfilePic is None:
        ProfilePic = profile_default
    else:
        ProfilePic = username.ProfilePic

    # Fetch the purchase invoice for the given product ID, including store information
    purchase_invoice = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .join(MSStore, MSProduct.StoreId == MSStore.id) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchaseItem.id == id) \
        .all()

    # Calculate total amount
    total_amount = sum(item.TotalPrice for item in purchase_invoice)

    for purchase_item in purchase_invoice:
        purchase_date = purchase_item.MSPurchase.PurchaseDate
        # Format the date into MM/DD/YYYY 12-hour format
        formatted_purchase_date = purchase_date.strftime('%m/%d/%Y %I:%M %p')

    return render_template('Client-Home-Page/Invoice/index.html',
                        User=username.FirstName + " " + username.LastName,
                        PDM="show",
                        user=current_user,
                        purchase_date=formatted_purchase_date,
                        ProfilePic=ProfilePic,
                        purchase_invoice=purchase_invoice,
                        id = id,
                        total_amount=total_amount)

# ------------------------------- END OF PDM PERSONAL DATA REPORTS  ---------------------------- 
