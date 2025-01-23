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
from sqlalchemy import update

# LOADING MODEL CLASSES
from .models import MSAccount, MSLoginToken, MSUser_Log


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
profile_default='1VikMpsCn5FpqbXd1Wny_EqOW92T8pFBt'

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
                    
                     
                    db.session.close()    
                    session['entry'] = 3
                    return redirect(url_for('auth.clientH'))

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
                        
                    db.session.close()    
                    session['entry'] = 3
                    return redirect(url_for('auth.clientH'))

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

@auth.route("/faculty-home-page")
@login_required
@Check_Token
def clientH():
        
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = MSAccount.query.filter_by(MSId=current_user.MSId).first() 
        
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
                                
        return render_template("Faculty-Home-Page/base.html", 
                               User= username.FirstName + " " + username.LastName,
                               user= current_user,
                               profile_pic=ProfilePic)



# -------------------------------------------------------------

# IF USER SESSION IS NULL

@auth.route("/login-denied")
def login_denied():
    return redirect(url_for('views.home'))

@auth.route("/access-denied")
def login_error_modal():
    return render_template('404/error_modal.html')  # Render the template containing your modal


# -------------------------------------------------------------

# FACULTY LOGOUT ROUTE
@auth.route("/logout")
@login_required
def Logout():
    
    
    # # REVOKE USER TOKEN FROM ALL BROWSERS
    # token_list = current_user.MSLoginToken  # This returns a list of MSLoginToken objects
    # if token_list:
    #     # Access the first token from the list
    #     token_id = token_list[0].id  # Assuming you want the first token
    #     user_token = MSLoginToken.query.filter_by(id=token_id, MSId=current_user.MSId).first()
    #     # Now 'user_token' should contain the specific MSLoginToken object
    #     if user_token:
    #         db.session.delete(user_token)
    #         db.session.commit()
    #         db.session.close()
    # else:
    #     pass
    
    add_log = MSUser_Log(
                        MSId=current_user.MSId,
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
            return render_template("Client-Login-Page/Emailnotfound.html", Email=Email) 
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
