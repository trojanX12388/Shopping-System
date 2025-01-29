from flask import Flask, Blueprint, abort, flash, json, make_response, redirect, render_template, request, jsonify, url_for
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from urllib.request import urlretrieve
from flask_login import login_user,login_required, logout_user, current_user, LoginManager
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from flask_mail import Mail,Message
from datetime import datetime, timedelta, timezone

import os,requests


load_dotenv()

# IMPORT LOCAL FUNCTIONS
from .API.authentication import *
from .Token.token_gen import *
from .Token.token_check import Check_Token

# IMPORT SMTP EMAILING FUNCTIONS

from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email

# DATABASE CONNECTION
from .models import db
from sqlalchemy import update, desc

# LOADING MODEL CLASSES
from website.models import MSAccount, MSProduct, MSStore, MSRating, MSCart, MSPurchase, MSPurchaseItem,MSNotification, MSLoginToken, MSUser_Log,MSOrder,MSMessage,MSVoucher



# LOAD JWT MODULE
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, decode_token

# EXECUTING DATABASE

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError  # Import this for catching database integrity errors
import traceback 

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


mail=Mail(app)

class EmailForm(Form):
    Email = StringField('Email', validators=[DataRequired(), Email()])

class PasswordForm(Form):
    Password = PasswordField('Email', validators=[DataRequired()])

# -------------------------------------------------------------

# PYDRIVE AUTH CONFIGURATION
gauth = GoogleAuth()
drive = GoogleDrive(gauth)

# Default Profile Pic
profile_default=os.getenv("profile_default") 

# -------------------------------------------------------------
# WEB AUTH ROUTES URL
auth = Blueprint('auth', __name__)

# -------------------------------------------------------------

# -------------------------------------------------------------

# calculate age in years
from datetime import date

def calculateAgeFromString(birthdate_str):
    birthdate = datetime.datetime.strptime(birthdate_str, "%Y-%m-%d").date()
    today = date.today()
    
    try:
        birthday = birthdate.replace(year=today.year)
    except ValueError:
        birthday = birthdate.replace(year=today.year, month=birthdate.month + 1, day=1)
    
    if birthday > today:
        return today.year - birthdate.year - 1
    else:
        return today.year - birthdate.year



# -------------------------------------------------------------


# CLIENT PAGE ROUTE

@auth.route('/client-login', methods=['GET', 'POST'])
def clientL():
    if 'entry' not in session:
        session['entry'] = 3  # Set the maximum number of allowed attempts initially

    if request.method == 'POST':
        Email = request.form.get('email')
        Password = request.form.get('password')

        entry = session['entry']
        User = MSAccount.query.filter_by(Email=Email).first()

        if not User:
            flash('Incorrect Email or Password!', category='error')
        elif User.Status == "Disabled":
            flash('Your Account has been disabled. Please contact Administrator to enable your account...', category='error') 
        
        elif User.Status == "Locked":
            flash('Your Account is Locked. Please contact Administrator...', category='error') 
            
        elif User.Status == "Deactivated":

            if User.Login_Attempt != 2:
                u = update(MSAccount).values({"Login_Attempt": User.Login_Attempt - 1})
                u = u.where(MSAccount.MSId == User.MSId)
                db.session.execute(u)
                db.session.commit()

                if check_password_hash(User.Password, Password):
                    login_user(User, remember=False)
                    access_token = generate_access_token(User.MSId)
                    refresh_token = generate_refresh_token(User.MSId)

                    u = update(MSAccount).values({"Login_Attempt": 5,
                                                   "Status": "Active",})
                    u = u.where(MSAccount.MSId == User.MSId)
                    db.session.execute(u)
                    db.session.commit()
                        
                    login_token = MSLoginToken.query.filter_by(MSId=current_user.MSId).first()
                    if login_token:
                        u = update(MSLoginToken).values({"access_token": access_token,"refresh_token": refresh_token,})
                        u = u.where(MSLoginToken.MSId == User.MSId)
                        db.session.execute(u)
                        db.session.commit()
                    else:
                        login_token = MSLoginToken(access_token=access_token, refresh_token=refresh_token, MSId=current_user.MSId)
                        db.session.add(login_token)
                        db.session.commit()
                    
                    
                    add_log = MSUser_Log(
                        MSId=current_user.MSId,
                        Status= "success",
                        Log = "Activated",
                    )
                    
                    db.session.add(add_log)
                    db.session.commit()
                      
                    session['entry'] = 3
                    if User.Type == "Client":
                        return redirect(url_for('auth.clientH'))
                    else:
                        return redirect(url_for('auth.adminH'))

                else:
                    entry -= 1
                    if entry == 0:
                        flash('Your Account is Deactivated, enter the correct password to activate.', category='error')
                    else:
                        session['entry'] = entry
                        flash('Your Account is Deactivated, enter the correct password to activate.', category='error')
                        return redirect(url_for('auth.clientL'))
            
            else:
                u = update(MSAccount)
                u = u.values({"Status": "Locked",})
                u = u.where(MSAccount.MSId == User.MSId)
                db.session.execute(u)
                db.session.commit()
                
                add_log = MSUser_Log(
                        MSId=User.MSId,
                        Status= "alert",
                        Log = "Locked",
                    )
                    
                db.session.add(add_log)
                db.session.commit()
                
                db.session.close()
                flash('Your Account has been locked due to many incorrect attempts.', category='error')
                return redirect(url_for('auth.clientL'))
        
        elif User.Status == "Active":

            if User.Login_Attempt != 0:
                u = update(MSAccount).values({"Login_Attempt": User.Login_Attempt - 1})
                u = u.where(MSAccount.MSId == User.MSId)
                db.session.execute(u)
                db.session.commit()

                if check_password_hash(User.Password, Password):
                    login_user(User, remember=False)
                    access_token = generate_access_token(User.MSId)
                    refresh_token = generate_refresh_token(User.MSId)

                    u = update(MSAccount).values({"Login_Attempt": 5})
                    u = u.where(MSAccount.MSId == User.MSId)
                    db.session.execute(u)
                    db.session.commit()
                        
                    login_token = MSLoginToken.query.filter_by(MSId=current_user.MSId).first()
                    if login_token:
                        u = update(MSLoginToken).values({"access_token": access_token,"refresh_token": refresh_token,})
                        u = u.where(MSLoginToken.MSId == User.MSId)
                        db.session.execute(u)
                        db.session.commit()
                    else:
                        login_token = MSLoginToken(access_token=access_token, refresh_token=refresh_token, MSId=current_user.MSId)
                        db.session.add(login_token)
                        db.session.commit()
                    
                    add_log = MSUser_Log(
                        MSId=current_user.MSId,
                        Status= "success",
                        Log = "Logged In",
                    )
                    
                    db.session.add(add_log)
                    db.session.commit()
                         
                    session['entry'] = 3
                    if User.Type == "Client":
                        return redirect(url_for('auth.clientH'))
                    else:
                        return redirect(url_for('auth.adminH'))

                else:
                    entry -= 1
                    if entry == 0:
                        flash('Invalid Credentials! Please Try again...', category='error')
                    else:
                        session['entry'] = entry
                        flash('Invalid Credentials! Please Try again...', category='error')
                        return redirect(url_for('auth.clientL'))
            
            else:
                u = update(MSAccount)
                u = u.values({"Status": "Locked",})
                u = u.where(MSAccount.MSId == User.MSId)
                db.session.execute(u)
                db.session.commit()
                
                add_log = MSUser_Log(
                        MSId=User.MSId,
                        Status= "alert",
                        Log = "Locked",
                    )
                    
                db.session.add(add_log)
                db.session.commit()
                
                db.session.close()
                flash('Your Account has been locked due to many incorrect attempts.', category='error')
                return redirect(url_for('auth.clientL'))
        else:
           flash('Unknown Account', category='error')  
    else:
        flash('Invalid Credentials! Please Try again...', category='error')                 
    return render_template("Client-Login-Page/index.html")



# FACULTY RESET ENTRY FOR LOGIN

@app.route('/reset-entry', methods=['POST'])
def reset_entry():
    session['entry'] = 3  # Reset the entry session variable
    return jsonify({'message': 'Entry reset successfully'})

# -------------------------------------------------------------
# CLIENT HOME PAGE ROUTE

@auth.route("/client-create", methods=['GET', 'POST'])
def clientC():
    if request.method == 'POST':
        FirstName = request.form.get('fname')
        LastName = request.form.get('lname')
        MidName = request.form.get('mname')
        Gender = request.form.get('gender')

        Email = request.form.get('email')
        Contact = request.form.get('phone')
        Birthday = request.form.get('bday')

        Password = request.form.get('password')
        CPassword = request.form.get('password2')


        # Check if email already exists
        existing_email = MSAccount.query.filter_by(Email=Email).first()
        if existing_email:
            return render_template("Client-Login-Page/create-account.html", sentreset=2) 
        else:
            # CHECK IF NEW AND CONFIRMATION ARE THE SAME
            if not Password == CPassword:
                flash("Password do not match.", category="error")
                return redirect(url_for('auth.clientC'))
            else:
                # Proceed to add the record
                try:
                    max_id = db.session.query(func.max(MSAccount.MSId)).scalar()

                    # Increment the maximum ID to get the new ID
                    new_client_id = max_id + 1 if max_id is not None else 1

                    add_record = MSAccount(
                        MSId=new_client_id,
                        Type="Client",
                        Password=generate_password_hash(Password),
                        FirstName=FirstName,
                        LastName=LastName,
                        MiddleName=MidName,
                        Gender=Gender,
                        BirthDate=Birthday,
                        Email=Email,
                        ContactNumber = Contact
                    )
                    
                    db.session.add(add_record)
                    db.session.commit()
                    
                    db.session.close()
                    
                    
                    return render_template("Client-Login-Page/create-account.html", sentreset=1) 
                except IntegrityError as e:
                        # Catch database integrity errors, like unique constraint violations
                        db.session.rollback()
                        flash('An error occurred while adding the Entrapp account. Please try again.', category='error')
                        traceback.print_exc()  # Print detailed error information to console
            
        
    
    return render_template("Client-Login-Page/create-account.html")
# -------------------------------------------------------------
 
# CLIENT HOME PAGE ROUTE

@auth.route("/client-home-page")
@login_required
@Check_Token
def clientH():
        
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        # Get the most viewed product (assuming you have a 'views' column in MSProduct table)
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
        
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic

        msstore_data = MSStore.query.order_by(MSStore.Visits.desc()).all()
     
        return render_template("Client-Home-Page/base.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               store = msstore_data,
                               most_recommended_products=most_recommended_products,
                               recom_average_rating = recom_average_rating,
                               profile_pic=ProfilePic)
 
# CLIENT USERS

@auth.route("/users")
@login_required
@Check_Token
def clientUsers():
        
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        # Get the most viewed product (assuming you have a 'views' column in MSProduct table)
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
        
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic

        users_data = MSAccount.query.order_by(MSAccount.MSId.desc()).all()
     
        return render_template("Client-Home-Page/Users/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               users_data = users_data,
                               most_recommended_products=most_recommended_products,
                               recom_average_rating = recom_average_rating,
                               profile_pic=ProfilePic)



# -------------------------------------------------------------

# IF USER SESSION IS NULL

@auth.route("/login-denied")
def login_denied():
    return redirect(url_for('auth.clientL'))

@auth.route("/access-denied")
def login_error_modal():
    return render_template('404/error_modal.html')  # Render the template containing your modal


# -------------------------------------------------------------

# FACULTY LOGOUT ROUTE
@auth.route("/logout")
@login_required
def Logout():
    
    MSId = current_user.MSId

    # REVOKE USER TOKEN FROM ALL BROWSERS
    token_list = current_user.MSLoginToken  # This returns a list of MSLoginToken objects
    if token_list:
        # Access the first token from the list
        token_id = token_list[0].id  # Assuming you want the first token
        user_token = MSLoginToken.query.filter_by(id=token_id, MSId=current_user.MSId).first()
        # Now 'user_token' should contain the specific MSLoginToken object
        if user_token:
            db.session.delete(user_token)
            db.session.commit()
            db.session.close()
    else:
        pass
    
    add_log = MSUser_Log(
                        MSId=MSId,
                        Status= "info",
                        Log = "Logged Out",
                    )
                    
    db.session.add(add_log)
    db.session.commit()
    db.session.close() 
    
    logout_user()
    session['entry'] = 3
    
    flash('Logged Out Successfully!', category='success')
    return redirect(url_for('auth.clientL')) 


# -------------------------------------------------------------

# FORGOT PASSWORD ROUTE
@auth.route('/request-reset-pass', methods=["POST"])
def facultyF():
    Email = request.form['resetpass']
    User = MSAccount.query.filter_by(Email=Email).first()
    
    # CHECKING IF ENTERED EMAIL IS NOT IN THE DATABASE
    if request.method == 'POST':
        if not User:
            return render_template("Client-Login-Page/emailnotfound.html", Email=Email) 
        else:
            token = jwt.encode({
                    'user': request.form['resetpass'],
                    # don't foget to wrap it in str function, otherwise it won't work 
                    'exp': (datetime.datetime.utcnow() + timedelta(minutes=15))
                },
                    app.config['SECRET_KEY'])
            
            accesstoken = token
            
            
            Email = request.form['resetpass']
            msg = Message( 
                            'Reset EntrApp Account Password', 
                            sender=("ENTRAPP", "entrapp3c@gmail.com"),
                            recipients = [Email] 
                        ) 
            assert msg.sender == "ENTRAPP <entrapp3c@gmail.com>"
            
            recover_url = url_for(
                    'auth.facultyRP',
                    token=accesstoken,
                    _external=True)

            
            msg.html = render_template(
                    'Email/Recover.html',
                    recover_url=recover_url)
            
            msg.body = (accesstoken)
            mail.send(msg)
            return render_template("Client-Login-Page/index.html", sentreset=1) 

# -------------------------------------------------------------



# -------------------------------------------------------------

# FACULTY RESET PASSWORD ROUTE

# AUTHENTICATION FUNCTION WITH TOKEN KEY TO RESET PASSWORD

def token_required(func):
    # decorator factory which invoks update_wrapper() method and passes decorated function as an argument
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'Alert!': 'Token is missing!'}), 401

        try:

            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
        # You can use the JWT errors in exception
        # except jwt.InvalidTokenError:
        #     return 'Invalid token. Please log in again.'
        except:
            return jsonify({'Message': 'Invalid token'}), 403
        return func(*args, **kwargs)
    return decorated

@auth.route('/reset-pass', methods=['GET', 'POST'])
@token_required
def facultyRP():
    token = request.args.get('token')
    user = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
    
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')

    Email = user['user']

    # UPDATE NEW PASSWORD TO THE FACULTY ACCOUNT
    if request.method == 'POST':
        if password1 == password2:
            # Update
            u = update(MSAccount)
            u = u.values({"Password": generate_password_hash(password1)})
            u = u.where(MSAccount.Email == Email)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('auth.clientL')) 
    
    return render_template("Client-Login-Page/resetpass.html", Email=Email) 


# -------------------------------------------------------------

# calculate age in years
from datetime import date
 
def calculateAge(born):
    today = date.today()
    try: 
        birthday = born.replace(year = today.year)
 
    # raised when birth date is February 29
    # and the current year is not a leap year
    except ValueError: 
        birthday = born.replace(year = today.year,
                  month = born.month + 1, day = 1)
 
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year

@auth.route("/account", methods=['GET', 'POST'])
@login_required
@Check_Token
def clientA():
        
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic

        msstore_data = MSStore.query.order_by(MSStore.id.asc()).all()

        if request.method == 'POST':

            # UPDATE BASIC DETAILS
            # VALUES
            fname = request.form.get('fname')
            lname = request.form.get('lname')
            mname = request.form.get('mname')
            birth_date = request.form.get('birth_date')
            address = request.form.get('address')
            phone = request.form.get('phone')
            
            u = update(MSAccount)
            u = u.values({"FirstName": fname,
                          "LastName": lname,
                          "MiddleName": mname,
                          "BirthDate": birth_date,
                          "Address": address,
                          "ContactNumber": phone,
                          })
            u = u.where(MSAccount.MSId == current_user.MSId)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('auth.clientA')) 

        return render_template("Client-Home-Page/Account/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               store = msstore_data,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               profile_pic=ProfilePic)


# UPDATE PIC

@auth.route("/Client-Update-Pic", methods=['POST'])
@login_required
def clientA_UP():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        id = username.MSId
        
        # UPDATE PROFILE PIC
        
        file =  request.form.get('base64')
        ext = request.files.get('fileup')
        ext = ext.filename
        
        # FACULTY FIS PROFILE PIC FOLDER ID
        folder = '1RFtil8DViIv_SBObttRj0xAlHRkP9UEY'
        
        
        url = """{}""".format(file)
                
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
        
        u = update(MSAccount)
        u = u.values({"ProfilePic": '%s'%(file1['id'])})
        u = u.where(MSAccount.MSId == current_user.MSId)
        db.session.execute(u)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('auth.clientA')) 
    
    
# CLEAR PIC
    
@auth.route("/Client-Clear-Pic")
@login_required
def clientA_C():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        id = username.MSId
        
        # FACULTY FIS PROFILE PIC FOLDER ID
        folder = '1RFtil8DViIv_SBObttRj0xAlHRkP9UEY'
       
        # CLEAR PROFILE PIC
        file_list = drive.ListFile({'q': "'%s' in parents and trashed=false"%(folder)}).GetList()
        try:
            for file1 in file_list:
                if file1['title'] == str(id):
                    file1.Delete()                
        except:
            pass

        # UPDATE USER PROFILE PIC ID
        
        u = update(MSAccount)
        u = u.values({"ProfilePic": profile_default})
        u = u.where(MSAccount.MSId == current_user.MSId)
        db.session.execute(u)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('auth.clientA')) 




@auth.route("/Settings", methods=['GET', 'POST'])
@login_required
@Check_Token
def Settings():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    

    
        if request.method == 'POST':
            from werkzeug.security import generate_password_hash
            from werkzeug.security import check_password_hash
         
            # VALUES
           
            password = request.form.get('password')
            newpassword = request.form.get('newpassword')
            renewpassword = request.form.get('renewpassword')
            
            if check_password_hash(current_user.Password, password):

                if newpassword == renewpassword:
                    Password=generate_password_hash(newpassword)
                    
                    u = update(MSAccount)
                    u = u.values({"Password": Password})
                    
                    u = u.where(MSAccount.MSId == current_user.MSId)
                    db.session.execute(u)
                    db.session.commit()
                    db.session.close()
                    
                    flash('Password successfully updated!', category='success')
                    return redirect(url_for('auth.clientA'))
                 
                else:
                    flash('Invalid input! Password does not match...', category='error')
                    return redirect(url_for('auth.clientA')) 
            else:
                flash('Invalid input! Password does not match...', category='error')
                return redirect(url_for('auth.clientA')) 
                                
        return redirect(url_for('auth.clientA')) 




# ____________________________ ADMIN ROUTE ______________________________

@auth.route("/add/store",  methods=['GET', 'POST'])
@login_required
@Check_Token
def admin_add_store():
    # Handle POST request for updating products
    if request.method == 'POST':
        # VALUES
        name = request.form.get('name')
        # Get base64 image and file upload
        file = request.form.get('base64')
        ext = request.files.get('fileup')
        
        
        # STORE IMAGE FOLDER ID
        folder = '1GQUptoIKVP8zRahj5mF86Yc76QQJ3Cne'
        
        if ext:  # Only process image if a new file is provided
            ext = ext.filename
            
            url = """data:image/png;base64,{}""".format(file)
            filename, m = urlretrieve(url)

            # DELETE EXISTING IMAGE WITH SAME TITLE IN THE FOLDER
            file_list = drive.ListFile({'q': "'%s' in parents and trashed=false" % folder}).GetList()
            try:
                for file1 in file_list:
                    if file1['title'] == str(name):
                        file1.Delete()
            except Exception as e:
                print(f"Error deleting file: {e}")
            
            # CONFIGURE FILE FORMAT AND NAME
            file1 = drive.CreateFile(metadata={
                "title": str(name),
                "parents": [{"id": folder}],
                "mimeType": "image/png"
            })
            
            # GENERATE FILE AND UPLOAD
            file1.SetContentFile(filename)
            file1.Upload()
            

        
            add_record = MSStore(StoreName=name,
                                Image='%s'%(file1['id']))
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
        
        # Redirect back to the products page
        return redirect(url_for('auth.clientH'))

          
@auth.route("/delete/store/<int:id>", methods=['GET', 'POST'])
@Check_Token
@login_required
def admin_del_store(id):
    storeid = id

    # Find the store in the database
    data = MSStore.query.filter_by(id=storeid).first()
    if data:
        id_str = data.StoreName

        # Store image folder ID (Google Drive deletion code remains the same)
        folder = '1GQUptoIKVP8zRahj5mF86Yc76QQJ3Cne'

        # Use a no_autoflush block to avoid premature flush
        with db.session.no_autoflush:
            # Step 1: Get all product IDs for the store
            product_ids = db.session.query(MSProduct.id).filter(MSProduct.StoreId == data.id).all()
            product_ids = [product.id for product in product_ids]

            # Step 2: Get all purchase IDs that reference the store
            purchase_ids = db.session.query(MSPurchase.id).filter(MSPurchase.StoreId == data.id).all()
            purchase_ids = [purchase.id for purchase in purchase_ids]

            # Step 3: Get all MSPurchaseItem IDs related to those purchases
            purchase_items = db.session.query(MSPurchaseItem.id).filter(MSPurchaseItem.PurchaseId.in_(purchase_ids)).all()
            purchase_item_ids = [item.id for item in purchase_items]

            # Step 4: Delete related MSNotification entries (delete notifications referencing MSPurchaseItem)
            MSNotification.query.filter(MSNotification.purchase_item_id.in_(purchase_item_ids)).delete(synchronize_session=False)

            # Step 5: Delete related MSPurchaseItem entries for the purchases
            MSPurchaseItem.query.filter(MSPurchaseItem.PurchaseId.in_(purchase_ids)).delete(synchronize_session=False)

            # Step 6: Delete related MSCart entries for the products
            MSCart.query.filter(MSCart.ProductId.in_(product_ids)).delete(synchronize_session=False)

            # Step 7: Delete related MSRating entries for the products
            MSRating.query.filter(MSRating.ProductId.in_(product_ids)).delete(synchronize_session=False)

            # Step 8: Delete all purchases for the store (after deleting purchase items)
            MSPurchase.query.filter(MSPurchase.StoreId == data.id).delete(synchronize_session=False)

            # Step 9: Delete the products for the store (after deleting related data)
            MSProduct.query.filter(MSProduct.StoreId == data.id).delete(synchronize_session=False)

        # Step 10: Delete the store itself (after all dependent records are removed)
        db.session.delete(data)

        # Step 11: Commit the changes to apply the deletions
        db.session.commit()

        # Step 12: Close the session
        db.session.close()

        # Google Drive deletion logic
        file_list = drive.ListFile({'q': f"'{folder}' in parents and trashed=false"}).GetList()
        try:
            for file1 in file_list:
                if file1['title'] == str(id_str):
                    file1.Delete()
        except:
            pass
        
        return redirect(url_for('auth.clientH'))

    flash('Store not found.', 'danger')
    return redirect(url_for('auth.clientH'))


@auth.route("/admin-dashboard")
@login_required
@Check_Token
def adminH():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
    if username.ProfilePic is None:
        ProfilePic = profile_default
    else:
        ProfilePic = username.ProfilePic

    # Orders: Get the count of all purchases (or orders)
    all_orders = MSPurchase.query.filter(MSPurchase.MSId == current_user.MSId).all()

    # Users: Get the count of users with 'Client' type
    all_clients = MSAccount.query.filter_by(Type='Client').all()

    # Revenue: Calculate total revenue (sum of purchase item prices or amounts)
    revenue = db.session.query(db.func.sum(MSPurchaseItem.TotalPrice)).filter(MSPurchaseItem.PurchaseId == MSPurchase.id).all()[0][0]

    # Calculate other data like pending, packing, etc. (as in your current code)
    pending_purchases = MSPurchaseItem.query.join(MSPurchase, MSPurchaseItem.PurchaseId == MSPurchase.id) \
        .join(MSProduct, MSPurchaseItem.ProductId == MSProduct.id) \
        .join(MSAccount, MSPurchase.MSId == MSAccount.MSId) \
        .filter(MSPurchase.MSId == current_user.MSId) \
        .filter(MSPurchase.status == 'pending') \
        .all()
    

    # Get the total number of products in the system
    total_products = MSProduct.query.count()

    # Get the most viewed product (assuming you have a 'views' column in MSProduct table)
    most_viewed_products = MSProduct.query.order_by(MSProduct.ProductViews.desc()).limit(10).all()

    # Get top contributors (assuming you already have the query for this)
    top_contributors_data = db.session.query(
        MSAccount.FirstName, MSAccount.LastName, MSAccount.ProfilePic, db.func.count(MSProduct.id).label('product_count')
    ).join(MSProduct, MSAccount.MSId == MSProduct.MSId).group_by(MSAccount.MSId).order_by(db.func.count(MSProduct.id).desc()).limit(3).all()


    # Pass data to template
    return render_template("Client-Home-Page/Dashboard/index.html", 
                           User=username.FirstName + " " + username.LastName,
                           user=current_user,
                           profile_pic=ProfilePic,
                           total_orders=len(all_orders),
                           total_clients=len(all_clients),
                           pending_purchases=pending_purchases,
                           top_contributors=top_contributors_data,
                           total_products=total_products,
                           most_viewed_products=most_viewed_products,
                           revenue=revenue)