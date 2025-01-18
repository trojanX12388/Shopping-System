from flask import Flask, Blueprint, redirect, render_template, request, url_for, flash
from dotenv import load_dotenv
from flask_login import login_required, current_user
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from urllib.request import urlretrieve
from cryptography.fernet import Fernet
from datetime import datetime
import rsa

import os
import os.path
import requests

load_dotenv()

# DATABASE CONNECTION
from website.models import db
from sqlalchemy import update

# LOADING MODEL CLASSES
from website.models import FISFaculty, FISAdmin, FISRequests

# LOADING FUNCTION CHECK TOKEN
from website.Token.token_check import Check_Token

# WEB AUTH ROUTES URL
req = Blueprint('req', __name__)

# -------------------------------------------------------------

# PYDRIVE AUTH CONFIGURATION
gauth = GoogleAuth()
drive = GoogleDrive(gauth)


# -------------------------------------------------------------

# ENCRYPTION / DECRYPTION

private_key = rsa.PrivateKey.load_pkcs1(os.getenv('PRIVATE_KEY'))

with open(os.path.dirname(__file__) + '/../key/filekey.key', "rb") as f:
    enckey = f.read()

key = rsa.decrypt(enckey,private_key)

# using the generated key
fernet = Fernet(key)

# -------------------------------------------------------------

# Default Profile Pic
profile_default='14wkc8rPgd8NcrqFoRFO_CNyrJ7nhmU08'



# -------------------------------------------------------------


#                                                    ADMIN AND FACULTY REQUEST

# ------------------------------- FACULTY REQUEST ----------------------------  

@req.route("/Request", methods=['GET', 'POST'])
@login_required
@Check_Token
def req_main():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
        

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
           
        if request.method == 'POST':
         
            # VALUES
            requesttype = request.form.get('request')
            message = request.form.get('message')
            
            add_record = FISRequests(Request=requesttype,
                                     message=message,
                                     DateTime = datetime.now(),
                                     Type="update",
                                    FacultyId = current_user.FacultyId,
                                    )
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            
            flash('Successfully Requested! Please wait for the System Admin to respond...', category='success')
            return redirect(url_for('req.req_main'))
        
                      
        return render_template("Faculty-Home-Page/Request/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               faculty_code= username.FacultyCode,
                               user= current_user,
                               profile_pic=ProfilePic,)

 
# ------------------------------------------------------------- 


# ------------------------------- ADMIN REQUEST ----------------------------  

@req.route("/Admin-Request", methods=['GET', 'POST'])
@login_required
@Check_Token
def reqadmin_main():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISAdmin.query.filter_by(AdminId=current_user.AdminId).first() 
        

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
           
        if request.method == 'POST':
         
            # VALUES
            requesttype = request.form.get('request')
            message = request.form.get('message')
            
            add_record = FISRequests(Request=requesttype,
                                     message=message,
                                     DateTime = datetime.now(),
                                     Type="update",
                                    AdminId = current_user.AdminId,
                                    )
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            
            flash('Successfully Requested! Please wait for the System Admin to respond...', category='success')
            return redirect(url_for('req.reqadmin_main'))
        
                      
        return render_template("Admin-Home-Page/Request/index.html", 
                               User= username.FirstName + " " + username.LastName,
                               faculty_code= username.FacultyCode,
                               user= current_user,
                               profile_pic=ProfilePic,)

 
# ------------------------------------------------------------- 