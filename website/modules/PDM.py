from flask import Flask, Blueprint, redirect, render_template, request, url_for, flash
from dotenv import load_dotenv
from flask_login import login_required, current_user
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from urllib.request import urlretrieve
from cryptography.fernet import Fernet
import rsa

import requests
import base64

import os
import os.path

load_dotenv()

# DATABASE CONNECTION
from website.models import db
from sqlalchemy import update

# LOADING MODEL CLASSES
from website.models import FISFaculty

# LOADING MODEL PDS_TABLES
from website.models import FISPDS_PersonalDetails, FISPDS_ContactDetails, FISPDS_FamilyBackground, FISPDS_FamilyBackground_Children, FISPDS_EducationalBackground, FISPDS_EducationalBackground_Additional, FISPDS_Eligibity, FISPDS_WorkExperience, FISPDS_VoluntaryWork, FISProfessionalDevelopment, FISPDS_TrainingSeminars, FISPDS_OutstandingAchievements, FISPDS_OfficeShipsMemberships, FISPDS_AgencyMembership, FISPDS_TeacherInformation, FISPDS_AdditionalQuestions, FISPDS_CharacterReference,FISPDS_Signature
   
# LOADING FUNCTION CHECK TOKEN
from website.Token.token_check import Check_Token

PDM = Blueprint('PDM', __name__)

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
         
# -------------------------------------------------------------


#                                                    FACULTY PERSONAL DATA MANAGEMENT ROUTE


# ------------------------------- PDM BASIC DETAILS ----------------------------  

@PDM.route("/PDM-Basic-Details", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_BD():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
        
        def get_initials(middle_name):
            # Split the middle name into parts
            parts = middle_name.split()
            # Take the first character of each part, convert to uppercase, and join them
            initials = ''.join(part[0].upper() for part in parts)
            return initials

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
           
        
        # UPDATE PROFILE BASIC DETAILS
        
        if request.method == 'POST':

            # UPDATE BASIC DETAILS
            # VALUES
            FacultyCode = request.form.get('faculty_code')
            Honorific = request.form.get('honorific')
            LastName = request.form.get('last_name')
            MiddleName = request.form.get('middle_name')
            MiddleInitial = get_initials(MiddleName)
            NameExtension = request.form.get('name_extension')
            Remarks = request.form.get('remarks')
            
            u = update(FISFaculty)
            u = u.values({"FacultyCode": FacultyCode,
                          "Honorific": Honorific,
                          "LastName": LastName,
                          "MiddleName": MiddleName,
                          "MiddleInitial": MiddleInitial,
                          "NameExtension": NameExtension,
                          "Remarks": Remarks,
                          })
            u = u.where(FISFaculty.FacultyId == current_user.FacultyId)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_BD')) 
                      
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Basic-Details.html", 
                               User= username.FirstName + " " + username.LastName,
                               PDM= "show",
                               user= current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               profile_pic=ProfilePic,
                               activate_BD= "active")


# UPDATE PIC

@PDM.route("/PDM-Basic-Details-Update-Pic", methods=['POST'])
@login_required
def PDM_BDUP():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
        id = username.FacultyId
        
        # UPDATE PROFILE PIC
        
        file =  request.form.get('base64')
        ext = request.files.get('fileup')
        ext = ext.filename
        
        # FACULTY FIS PROFILE PIC FOLDER ID
        folder = '1mT1alkWJ-akPnPyB9T7vtumNutwqRK0S'
        
        
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
        
        u = update(FISFaculty)
        u = u.values({"ProfilePic": '%s'%(file1['id'])})
        u = u.where(FISFaculty.FacultyId == current_user.FacultyId)
        db.session.execute(u)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('PDM.PDM_BD')) 
    
    
# CLEAR PIC
    
@PDM.route("/PDM-Basic-Details-Clear-Pic")
@login_required
def PDM_BDCP():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
        id = username.FacultyId
        
        # FACULTY FIS PROFILE PIC FOLDER ID
        folder = '1mT1alkWJ-akPnPyB9T7vtumNutwqRK0S'
       
        # CLEAR PROFILE PIC
        file_list = drive.ListFile({'q': "'%s' in parents and trashed=false"%(folder)}).GetList()
        try:
            for file1 in file_list:
                if file1['title'] == str(id):
                    file1.Delete()                
        except:
            pass

        # UPDATE USER PROFILE PIC ID
        
        u = update(FISFaculty)
        u = u.values({"ProfilePic": profile_default})
        u = u.where(FISFaculty.FacultyId == current_user.FacultyId)
        db.session.execute(u)
        db.session.commit()
        db.session.close()
        
        return redirect(url_for('PDM.PDM_BD')) 


# ------------------------------- END PDM BASIC DETAILS ----------------------------  


# ------------------------------- PDM PERSONAL DETAILS ----------------------------  

@PDM.route("/PDM-Personal-Details", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_PD():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 

        # CHECKING IF PROFILE PIC EXIST
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic   
             
        # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_PersonalDetails:
            data = current_user
        else:
            data =  {'FISPDS_PersonalDetails':
                    {'sex':"",
                    'gender':"",
                    'height':"",
                    'weight':"",
                    'religion':"",
                    'civil_status':"",
                    'blood_type':"",
                    'pronoun':"",
                    'country':"",
                    'city':"",
                    'citizenship':"",
                    'dual_citizenship':"",
                    'Remarks':"",
                    }
                    }
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
            sex = request.form.get('sex')
            gender = request.form.get('gender')
            height = request.form.get('height')
            weight = request.form.get('weight')
            religion = request.form.get('religion')
            civil_status = request.form.get('civil_status')
            blood_type = request.form.get('blood_type')
            pronoun = request.form.get('pronoun')
            country = request.form.get('country')
            city = request.form.get('city')
            citizenship = request.form.get('citizenship')
            dual_citizenship = request.form.get('dual_citizenship')
            Remarks = request.form.get('remarks')
           

            if FISPDS_PersonalDetails.query.filter_by(FacultyId=current_user.FacultyId).first():
                u = update(FISPDS_PersonalDetails)
                u = u.values({"sex": sex,
                            "gender": gender,
                            "height": height,
                            "weight": weight,
                            "religion": religion,
                            "civil_status": civil_status,
                            "blood_type": blood_type,
                            "pronoun": pronoun,
                            "country": country,
                            "city": city,
                            "citizenship": citizenship,
                            "dual_citizenship": dual_citizenship,
                            "Remarks": Remarks,
                            })
                u = u.where(FISPDS_PersonalDetails.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_PD'))
            
            else:
                add_record = FISPDS_PersonalDetails(  sex = sex,
                                                    gender = gender,
                                                    height = height,
                                                    weight = weight,
                                                    religion = religion,
                                                    civil_status = civil_status,
                                                    blood_type = blood_type,
                                                    pronoun = pronoun,
                                                    country = country,
                                                    city = city,
                                                    citizenship = citizenship,
                                                    dual_citizenship = dual_citizenship,
                                                    Remarks = Remarks,
                                                    FacultyId = current_user.FacultyId)
            
                db.session.add(add_record)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_PD'))
            
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Personal-Details.html", 
                               User=username.FirstName + " " + username.LastName,
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               data = data,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_PD="active")

# ------------------------------- END PDM PERSONAL DETAILS ----------------------------  


# ------------------------------- PDM CONTACT DETAILS ----------------------------  

@PDM.route("/PDM-Contact-Details", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_CD():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
       
        # CHECKING IF PROFILE PIC EXIST
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic   
             
        # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_ContactDetails:
            data = current_user
        else:
            data =  {'FISPDS_ContactDetails':
                    {'email':"",
                     'mobile_number':"",
                     'tel_number':"",
                     'perm_country':"",
                     'perm_region':"",
                     'perm_province':"",
                     'perm_city':"",
                     'perm_address':"",
                     'perm_zip_code':"",
                     'perm_phone_number':"",
                     'res_country':"",
                     'res_region':"",
                     'res_province':"",
                     'res_city':"",
                     'res_address':"",
                     'res_zip_code':"",
                     'res_phone_number':"",
                    'Remarks':"",
                    }
                    }
        
         # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
            email = request.form.get('email')
            mobile_number = request.form.get('mobile_number')
            tel_number = request.form.get('tel_number')
            perm_country = request.form.get('perm_country')
            perm_region = request.form.get('perm_region')
            perm_province = request.form.get('perm_province')
            perm_city = request.form.get('perm_city')
            perm_address = request.form.get('perm_address')
            perm_zip_code = request.form.get('perm_zip_code')
            perm_phone_number = request.form.get('perm_phone_number')
            res_country = request.form.get('res_country')
            res_region = request.form.get('res_region')
            res_province = request.form.get('res_province')
            res_city = request.form.get('res_city')
            res_address = request.form.get('res_address')
            res_zip_code = request.form.get('res_zip_code')
            res_phone_number = request.form.get('res_phone_number')
            Remarks = request.form.get('remarks')

            if FISPDS_ContactDetails.query.filter_by(FacultyId=current_user.FacultyId).first():
                u = update(FISPDS_ContactDetails)
                u = u.values({"Email": email,
                             "mobile_number": mobile_number,
                            "tel_number": tel_number,
                            "perm_country": perm_country,
                            "perm_region": perm_region,
                            "perm_province": perm_province,
                            "perm_city": perm_city,
                            "perm_address": perm_address,
                            "perm_zip_code": perm_zip_code,
                            "perm_phone_number": perm_phone_number,
                            "res_country": res_country,
                            "res_region": res_region,
                            "res_province": res_province,
                            "res_city": res_city,
                            "res_address": res_address,
                            "res_zip_code": res_zip_code,
                            "res_phone_number": res_phone_number,
                            "Remarks": Remarks
                            })
                u = u.where(FISPDS_ContactDetails.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                
                u = update(FISFaculty)
                u = u.values({"ResidentialAddress": res_address,
                            })
                u = u.where(FISFaculty.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                
                db.session.close()
                return redirect(url_for('PDM.PDM_CD'))
            
            else:
                
                add_record = FISPDS_ContactDetails(  Email = email,
                                                    mobile_number = mobile_number,
                                                    tel_number = tel_number,
                                                    perm_country = perm_country,
                                                    perm_region = perm_region,
                                                    perm_province = perm_province,
                                                    perm_city = perm_city,
                                                    perm_address = perm_address,
                                                    perm_zip_code = perm_zip_code,
                                                    perm_phone_number = perm_phone_number,
                                                    res_country = res_country,
                                                    res_region = res_region,
                                                    res_province = res_province,
                                                    res_city = res_city,
                                                    res_address = res_address,
                                                    res_zip_code = res_zip_code,
                                                    res_phone_number = res_phone_number,
                                                    Remarks = Remarks,
                                                    FacultyId = current_user.FacultyId)
                db.session.add(add_record)
                db.session.commit()
                
                u = update(FISFaculty)
                u = u.values({
                            "ResidentialAddress": res_address,
                            })
                u = u.where(FISFaculty.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                
                db.session.close()
                return redirect(url_for('PDM.PDM_CD'))
        
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Contact-Details.html", 
                               User=username.FirstName + " " + username.LastName,
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               data = data,
                               activate_CD="active")
        
        
# ------------------------------- END PDM CONTACT DETAILS ----------------------------  


# ------------------------------- PDM FAMILY BACKGROUNDS ----------------------------  

@PDM.route("/PDM-Family-Background", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_FB():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
            
        # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_FamilyBackground:
            data = current_user
        else:
            data =  {'FISPDS_FamilyBackground':
                    {'spouse_surname': "",
                    'spouse_firstname': "",
                    'spouse_middlename': "",
                    'spouse_nameextension': "",
                    'spouse_occupation': "",
                    'spouse_employer': "",
                    'spouse_businessaddress': "",
                    'spouse_telephone': "",
                    'father_surname': "",
                    'father_firstname': "",
                    'father_middlename': "",
                    'father_nameextension': "",
                    'mother_surname': "",
                    'mother_firstname': "",
                    'mother_middlename': "",
                    }
                    }    
            
         # UPDATE 
        
        if request.method == 'POST':
            spouse_surname = request.form.get('SpouseSurname')
            spouse_firstname = request.form.get('SpouseFirstName')
            spouse_middlename = request.form.get('SpouseMiddleName')
            spouse_nameextension = request.form.get('SpouseExtension')
            spouse_occupation = request.form.get('Occupation')
            spouse_employer = request.form.get('SpouseBusiness')
            spouse_businessaddress = request.form.get('BusinessAddress')
            spouse_telephone = request.form.get('SpouseTelephone')
            
            father_surname = request.form.get('FatherSurname')
            father_firstname = request.form.get('FatherFirstName')
            father_middlename = request.form.get('FatherMiddleName')
            father_nameextension = request.form.get('FatherExtension')
            
            mother_surname = request.form.get('MotherSurname')
            mother_firstname = request.form.get('MotherFirstName')
            mother_middlename = request.form.get('MotherMiddleName')
         
            # VALUES
            if FISPDS_FamilyBackground.query.filter_by(FacultyId=current_user.FacultyId).first():
                
             
                u = update(FISPDS_FamilyBackground)
                u = u.values({'spouse_surname': spouse_surname,
                                'spouse_firstname': spouse_firstname,
                                'spouse_middlename': spouse_middlename,
                                'spouse_nameextension': spouse_nameextension,
                                'spouse_occupation': spouse_occupation,
                                'spouse_employer': spouse_employer,
                                'spouse_businessaddress': spouse_businessaddress,
                                'spouse_telephone': spouse_telephone,
                                'father_surname': father_surname,
                                'father_firstname': father_firstname,
                                'father_middlename': father_middlename,
                                'father_nameextension': father_nameextension,
                                'mother_surname': mother_surname,
                                'mother_firstname': mother_firstname,
                                'mother_middlename': mother_middlename,
                            })
                u = u.where(FISPDS_FamilyBackground.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                print("update")
                return redirect(url_for('PDM.PDM_FB'))
            
            else:
                print("add")
                add_record = FISPDS_FamilyBackground( spouse_surname = spouse_surname, 
                                                    spouse_firstname = spouse_firstname, 
                                                    spouse_middlename = spouse_middlename, 
                                                    spouse_nameextension = spouse_nameextension, 
                                                    spouse_occupation = spouse_occupation, 
                                                    spouse_employer = spouse_employer, 
                                                    spouse_businessaddress = spouse_businessaddress, 
                                                    spouse_telephone = spouse_telephone,
                                                    father_surname = father_surname, 
                                                    father_firstname = father_firstname, 
                                                    father_middlename = father_middlename, 
                                                    father_nameextension = father_nameextension,
                                                    mother_surname = mother_surname, 
                                                    mother_firstname = mother_firstname, 
                                                    mother_middlename = mother_middlename, 
                                                    FacultyId = current_user.FacultyId)
                db.session.add(add_record)
                db.session.commit()
                
                return redirect(url_for('PDM.PDM_FB'))
            
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Family-Background.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               data = data,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_FB="active")
 
 
@PDM.route("/PDM-Family-Background/add-children", methods=['GET', 'POST'])
@login_required
def PDM_FBadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            full_name = request.form.get('full_name')
            birthdate = request.form.get('birthdate')
           
            add_record = FISPDS_FamilyBackground_Children(full_name=full_name,birthdate=birthdate,FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_FB'))
        
        
@PDM.route("/PDM-Family-Background/update-children", methods=['GET', 'POST'])
@login_required
def PDM_FBupdate():

         if request.method == 'POST':
         
            # VALUES
           
            full_name = request.form.get('full_name')
            birthdate = request.form.get('birthdate')
            id = request.form.get('id')

            u = update(FISPDS_FamilyBackground_Children)
            u = u.values({"full_name": full_name,
                          "birthdate": birthdate
                          })
            u = u.where(FISPDS_FamilyBackground_Children.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_FB'))

@PDM.route("/PDM-Family-Background/delete-children", methods=['GET', 'POST'])
@login_required
def PDM_FBdel():

         # DELETE RECORD
         
        # def delete( item_id):
        # item = ItemModel.query.get_or_404(item_id)
        # db.session.delete(item)
        # db.session.commit()
        # return {"message": "Item deleted."}

        id = request.form.get('id')
        

        data = FISPDS_FamilyBackground_Children.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_FB'))
 
# ------------------------------- END OF PDM FAMILY BACKGROUNDS ---------------------------- 

 
# ------------------------------- PDM EDUCATIONAL BACKGROUNDS ------------------------------  

@PDM.route("/PDM-Educational-Background", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_EB():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
            
        # UPDATE 
        
        # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_EducationalBackground:
            data = current_user
        else:
            data =  {'FISPDS_EducationalBackground':
                    { "ESchoolName": "",
                    "EAttendancePeriod_From": "",
                    "EAttendancePeriod_To": "",
                    "EYearGraduated": "",
                    "EScholarshi_Honor": "",
                    
                    "SSchoolName": "",
                    "SAttendancePeriod_From": "",
                    "SAttendancePeriod_To": "",
                    "SYearGraduated": "",
                    "SScholarshi_Honor": "",
                    
                    "CSchoolName": "",
                    "CBasicEducation": "",
                    "CAttendancePeriod_From": "",
                    "CAttendancePeriod_To": "",
                    "CUnits": "",
                    "CYearGraduated": "",
                    "CScholarshi_Honor": "",
                    }
                    }    
        
        if request.method == 'POST':
         
            # VALUES
           
            ESchoolName = request.form.get('ESchoolName')
            EAttendancePeriod_From = request.form.get('EAttendancePeriod_From')
            EAttendancePeriod_To = request.form.get('EAttendancePeriod_To')
            EYearGraduated = request.form.get('EYearGraduated')
            EScholarshi_Honor = request.form.get('EScholarshi_Honor')
            
            SSchoolName = request.form.get('SSchoolName')
            SAttendancePeriod_From = request.form.get('SAttendancePeriod_From')
            SAttendancePeriod_To = request.form.get('SAttendancePeriod_To')
            SYearGraduated = request.form.get('SYearGraduated')
            SScholarshi_Honor = request.form.get('SScholarshi_Honor')
            
            CSchoolName = request.form.get('CSchoolName')
            CBasicEducation = request.form.get('CBasicEducation')
            CAttendancePeriod_From = request.form.get('CAttendancePeriod_From')
            CAttendancePeriod_To = request.form.get('CAttendancePeriod_To')
            CUnits = request.form.get('CUnits')
            CYearGraduated = request.form.get('CYearGraduated')
            CScholarshi_Honor = request.form.get('CScholarshi_Honor')

            if FISPDS_EducationalBackground.query.filter_by(FacultyId=current_user.FacultyId).first():
                u = update(FISPDS_EducationalBackground)
                u = u.values({
                    "ESchoolName": ESchoolName,
                    "EAttendancePeriod_From": EAttendancePeriod_From,
                    "EAttendancePeriod_To": EAttendancePeriod_To,
                    "EYearGraduated": EYearGraduated,
                    "EScholarshi_Honor": EScholarshi_Honor,
                    
                    "SSchoolName": SSchoolName,
                    "SAttendancePeriod_From": SAttendancePeriod_From,
                    "SAttendancePeriod_To": SAttendancePeriod_To,
                    "SYearGraduated": SYearGraduated,
                    "SScholarshi_Honor": SScholarshi_Honor,
                    
                    "CSchoolName": CSchoolName,
                    "CBasicEducation": CBasicEducation,
                    "CAttendancePeriod_From": CAttendancePeriod_From,
                    "CAttendancePeriod_To": CAttendancePeriod_To,
                    "CUnits": CUnits,
                    "CYearGraduated": CYearGraduated,
                    "CScholarshi_Honor": CScholarshi_Honor,
                            })
                
                u = u.where(FISPDS_EducationalBackground.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                print("update")
                return redirect(url_for('PDM.PDM_EB')) 
        
            else:
                print("add")
                add_record = FISPDS_EducationalBackground( ESchoolName = ESchoolName, 
                                                    EAttendancePeriod_From = EAttendancePeriod_From,
                                                    EAttendancePeriod_To = EAttendancePeriod_To,
                                                    EYearGraduated = EYearGraduated,
                                                    EScholarshi_Honor = EScholarshi_Honor,
                                                    
                                                    SSchoolName = SSchoolName,
                                                    SAttendancePeriod_From = SAttendancePeriod_From,
                                                    SAttendancePeriod_To = SAttendancePeriod_To,
                                                    SYearGraduated = SYearGraduated,
                                                    SScholarshi_Honor = SScholarshi_Honor,
                                                    
                                                    CSchoolName = CSchoolName,
                                                    CBasicEducation = CBasicEducation,
                                                    CAttendancePeriod_From = CAttendancePeriod_From,
                                                    CAttendancePeriod_To = CAttendancePeriod_To,
                                                    CUnits = CUnits,
                                                    CYearGraduated = CYearGraduated,
                                                    CScholarshi_Honor = CScholarshi_Honor,
                                                    
                                                    FacultyId = current_user.FacultyId)
                db.session.add(add_record)
                db.session.commit()
                
                return redirect(url_for('PDM.PDM_EB')) 
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Educational-Background.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               data = data,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_EB="active")


@PDM.route("/PDM-Educational-Background/add-education", methods=['GET', 'POST'])
@login_required
def PDM_EBadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            Level = request.form.get('Level')
            School_Name = request.form.get('School_Name')
            Degree = request.form.get('Degree')
            Units = request.form.get('Units')
            YearGraduated = request.form.get('YearGraduated')
            From = request.form.get('From')
            To = request.form.get('To')
            Scholarshi_Honor = request.form.get('Scholarshi_Honor')
           
            add_record = FISPDS_EducationalBackground_Additional(Level=Level,
                                                    School_Name=School_Name,
                                                    Degree=Degree,
                                                    Units=Units,
                                                    YearGraduated=YearGraduated,
                                                    From=From,
                                                    To=To,
                                                    Scholarshi_Honor=Scholarshi_Honor,
                                                    
                                                    FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_EB'))

        
@PDM.route("/PDM-Family-Background/update-education", methods=['GET', 'POST'])
@login_required
def PDM_EBupdate():

         if request.method == 'POST':
         
            # VALUES
           
            Level = request.form.get('Level')
            School_Name = request.form.get('School_Name')
            Degree = request.form.get('Degree')
            Units = request.form.get('Units')
            YearGraduated = request.form.get('YearGraduated')
            From = request.form.get('From')
            To = request.form.get('To')
            Scholarshi_Honor = request.form.get('Scholarshi_Honor')
            
            id = request.form.get('id')

            u = update(FISPDS_EducationalBackground_Additional)
            u = u.values({"Level": Level,
                          "School_Name": School_Name,
                          "Degree": Degree,
                          "Units": Units,
                          "YearGraduated": YearGraduated,
                          "From": From,
                          "To": To,
                          "Scholarshi_Honor": Scholarshi_Honor,
                          })
            u = u.where(FISPDS_EducationalBackground_Additional.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_EB'))


@PDM.route("/PDM-Educational-Background/delete-education", methods=['GET', 'POST'])
@login_required
def PDM_EBdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        

        data = FISPDS_EducationalBackground_Additional.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_EB'))


# ------------------------------- END OF PDM EDUCATIONAL BACKGROUNDS ----------------------------
 
# ------------------------------- PDM ELIGIBITIES -----------------------------------------------

@PDM.route("/PDM-Eligibities", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_E():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
       
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
            
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            Eligibility = request.form.get('Eligibility')
            Rating = request.form.get('Rating')
            Date = request.form.get('Date')
            Place = request.form.get('Place')
            License = request.form.get('License')
            id = request.form.get('id')

            u = update(FISPDS_Eligibity)
            u = u.values({"Eligibility": Eligibility,
                          "Rating": Rating,
                          "Date": Date,
                          "Place": Place,
                          "License": License,
                          })
            
            u = u.where(FISPDS_Eligibity.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_E'))    
            
            
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Eligibities.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_E="active")

@PDM.route("/PDM-Eligibities/add-record", methods=['GET', 'POST'])
@login_required
def PDM_Eadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            Eligibility = request.form.get('Eligibility')
            Rating = request.form.get('Rating')
            Date = request.form.get('Date')
            Place = request.form.get('Place')
            License = request.form.get('License')
           
            add_record = FISPDS_Eligibity(Eligibility=Eligibility,
                                          Rating=Rating,
                                          Date=Date,
                                          Place=Place,
                                          License=License,
                                          FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_E'))

@PDM.route("/PDM-Eligibities/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_Edel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_Eligibity.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_E'))
  

# ------------------------------- END OF PDM ELIGIBITIES  ---------------------------- 

 
# ------------------------------- PDM WORK EXPERIENCE ------------------------------



@PDM.route("/PDM-Work-Experience", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_WE():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic 
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            position = request.form.get('position')
            company_name = request.form.get('company_name')
            status = request.form.get('status')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
            id = request.form.get('id')

            u = update(FISPDS_WorkExperience)
            u = u.values({"position": position,
                          "company_name": company_name,
                          "status": status,
                          "from_date": from_date,
                          "to_date": to_date
                          })
            
            u = u.where(FISPDS_WorkExperience.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_WE'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Work-Experience.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_WE="active")
  
@PDM.route("/PDM-Work-Experience/add-record", methods=['GET', 'POST'])
@login_required
def PDM_WEadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            position = request.form.get('position')
            company_name = request.form.get('company_name')
            status = request.form.get('status')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
           
            add_record = FISPDS_WorkExperience(position=position,
                                             company_name=company_name,
                                             status=status,
                                             from_date=from_date,
                                             to_date=to_date,
                                             FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_WE'))

@PDM.route("/PDM-Work-Experience/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_WEdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_WorkExperience.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_WE'))
    
# ------------------------------- END OF PDM WORK EXPERIENCE  ---------------------------- 

 
# ------------------------------- PDM VOLUNTARY WORKS ------------------------------
  
@PDM.route("/PDM-Voluntary-Works", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_VW():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            organization = request.form.get('organization')
            position = request.form.get('position')
            hours = request.form.get('hours')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
            id = request.form.get('id')

            u = update(FISPDS_VoluntaryWork)
            u = u.values({"position": position,
                          "organization": organization,
                          "hours": hours,
                          "from_date": from_date,
                          "to_date": to_date
                          })
            
            u = u.where(FISPDS_VoluntaryWork.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_VW'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Voluntary-Works.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_VW="active")


@PDM.route("/PDM-Voluntary-Works/add-record", methods=['GET', 'POST'])
@login_required
def PDM_VWadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            organization = request.form.get('organization')
            position = request.form.get('position')
            hours = request.form.get('hours')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
           
            add_record = FISPDS_VoluntaryWork(organization=organization,
                                            position=position,
                                            hours=hours,
                                            from_date=from_date,
                                            to_date=to_date,
                                            FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_VW'))

@PDM.route("/PDM-Voluntary-Works/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_VWdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_VoluntaryWork.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_VW'))
  
    
# ------------------------------- END OF PDM VOLUNTARY WORKS  ---------------------------- 

 
# ------------------------------- PDM TRAINING SEMINARS ------------------------------

@PDM.route("/PDM-Training-Seminars", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_TS():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 

        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            title = request.form.get('title')
            level = request.form.get('level')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
            id = request.form.get('id')

            u = update(FISPDS_TrainingSeminars)
            u = u.values({"title": title,
                          "level": level,
                          "from_date": from_date,
                          "to_date": to_date
                          })
            
            u = u.where(FISPDS_TrainingSeminars.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_TS'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Training-Seminars.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_TS="active")
        

@PDM.route("/PDM-Training-Seminars/add-record", methods=['GET', 'POST'])
@login_required
def PDM_TSadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            title = request.form.get('title')
            level = request.form.get('level')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
           
            add_record = FISPDS_TrainingSeminars(title=title,
                                                level=level,
                                                from_date=from_date,
                                                to_date=to_date,
                                                FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_TS'))

@PDM.route("/PDM-Training-Seminars/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_TSdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_TrainingSeminars.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_TS'))
       
  
# ------------------------------- END OF PDM TRAINING SEMINARS  ---------------------------- 

 
# ------------------------------- PDM OUTSTANDING ACHIEVEMENTS ------------------------------


@PDM.route("/PDM-Outstanding-Achievements", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_OA():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
       
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
            
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            achievement = request.form.get('achievement')
            level = request.form.get('level')
            from_date = request.form.get('date')
            id = request.form.get('id')

            u = update(FISPDS_OutstandingAchievements)
            u = u.values({"achievement": achievement,
                          "level": level,
                          "date": from_date
                          })
            
            u = u.where(FISPDS_OutstandingAchievements.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_OA'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Outstanding-Achievements.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_OA="active")


@PDM.route("/PDM-Outstanding-Achievements/add-record", methods=['GET', 'POST'])
@login_required
def PDM_OAadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            achievement = request.form.get('achievement')
            level = request.form.get('level')
            date = request.form.get('date')
           
            add_record = FISPDS_OutstandingAchievements(achievement=achievement,
                                                    level=level,
                                                    date=date,
                                                    FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_OA'))

@PDM.route("/PDM-Outstanding-Achievements/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_OAdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_OutstandingAchievements.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_OA'))

# ------------------------------- END OF PDM OUTSTANDING ACHIEVEMENTS  ---------------------------- 

 
# ------------------------------- PDM OFFICESHIPS MEMBERSHIPS ------------------------------
 
@PDM.route("/PDM-Officeships-Memberships", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_OSM():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
      
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            organization = request.form.get('organization')
            position = request.form.get('position')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
            id = request.form.get('id')

            u = update(FISPDS_OfficeShipsMemberships)
            u = u.values({"position": position,
                          "organization": organization,
                          "from_date": from_date,
                          "to_date": to_date
                          })
            
            u = u.where(FISPDS_OfficeShipsMemberships.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_OSM')) 
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Officeships-Memberships.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_OSM="active")

@PDM.route("/PDM-Officeships-Memberships/add-record", methods=['GET', 'POST'])
@login_required
def PDM_OSMadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            organization = request.form.get('organization')
            position = request.form.get('position')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
           
            add_record = FISPDS_OfficeShipsMemberships(organization=organization,
                                            position=position,
                                            from_date=from_date,
                                            to_date=to_date,
                                            FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_OSM'))

@PDM.route("/PDM-Officeships-Memberships/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_OSMdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_OfficeShipsMemberships.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_OSM'))
  
    
# ------------------------------- END OF PDM OFFICESHIPS MEMBERSHIPS  ---------------------------- 

 
# ------------------------------- PDM AGENCY MEMBERSHIP ------------------------------
 
@PDM.route("/PDM-Agency-Membership", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_AM():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
      
        # CHECKING IF PROFILE PIC EXIST
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic   
        
        # Generate a Fernet key
        key_bytes = os.getenv('Symmetric_Key').encode('utf-8')
        fernet_key = (key_bytes)
        cipher = Fernet(fernet_key)
  
        # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_AgencyMembership:
            data = current_user
            fetch = FISPDS_AgencyMembership.query.filter_by(FacultyId=current_user.FacultyId).first()
            
            # Decrypt the sensitive data
            GSIShex_bytes = bytes.fromhex(fetch.GSIS[2:])
            PAGIBIGhex_bytes = bytes.fromhex(fetch.PAGIBIG[2:])
            PHILHEALTHhex_bytes = bytes.fromhex(fetch.PHILHEALTH[2:])
            SSShex_bytes = bytes.fromhex(fetch.SSS[2:])
            TINhex_bytes = bytes.fromhex(fetch.TIN[2:])
        
            # Decrypt the ciphertext
            GSISdecrypted_data = cipher.decrypt(GSIShex_bytes)
            PAGIBIGdecrypted_data = cipher.decrypt(PAGIBIGhex_bytes)
            PHILHEALTHdecrypted_data = cipher.decrypt(PHILHEALTHhex_bytes)
            SSSdecrypted_data = cipher.decrypt(SSShex_bytes)
            TINdecrypted_data = cipher.decrypt(TINhex_bytes)
            
            # Decode the decrypted data to utf-8
            decrypted_GSIS = GSISdecrypted_data.decode('utf-8')
            decrypted_PAGIBIG = PAGIBIGdecrypted_data.decode('utf-8')
            decrypted_PHILHEALTH = PHILHEALTHdecrypted_data.decode('utf-8')
            decrypted_SSS = SSSdecrypted_data.decode('utf-8')
            decrypted_TIN = TINdecrypted_data.decode('utf-8')
            
        else:
            data =  {'FISPDS_AgencyMembership':
                    {
                    'Remarks':""
                    }
                    }
            # Decrypt the sensitive data
            decrypted_GSIS = ""
            decrypted_PAGIBIG = ""
            decrypted_PHILHEALTH = ""
            decrypted_SSS = ""
            decrypted_TIN = ""
        
        # UPDATE 
        
        if request.method == 'POST':
            # Values
            GSIS = request.form.get('GSIS')
            PAGIBIG = request.form.get('PAGIBIG')
            PHILHEALTH = request.form.get('PHILHEALTH')
            SSS = request.form.get('SSS')
            TIN = request.form.get('TIN')
            Remarks = request.form.get('remarks')

            # Encrypt sensitive data
            
            encrypted_GSIS = cipher.encrypt(GSIS.encode('utf-8'))
            encrypted_PAGIBIG = cipher.encrypt(PAGIBIG.encode('utf-8'))
            encrypted_PHILHEALTH = cipher.encrypt(PHILHEALTH.encode('utf-8'))
            encrypted_SSS = cipher.encrypt(SSS.encode('utf-8'))
            encrypted_TIN = cipher.encrypt(TIN.encode('utf-8'))
           
           

            if FISPDS_AgencyMembership.query.filter_by(FacultyId=current_user.FacultyId).first():
                u = update(FISPDS_AgencyMembership)
                u = u.values({  "GSIS": encrypted_GSIS,
                                "PAGIBIG": encrypted_PAGIBIG,
                                "PHILHEALTH": encrypted_PHILHEALTH,
                                "SSS": encrypted_SSS,
                                "TIN": encrypted_TIN,
                                "Remarks": Remarks,
                            })
                u = u.where(FISPDS_AgencyMembership.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_AM'))
            
            else:
                add_record = FISPDS_AgencyMembership( GSIS = encrypted_GSIS,
                                                    PAGIBIG = encrypted_PAGIBIG,
                                                    PHILHEALTH = encrypted_PHILHEALTH,
                                                    SSS = encrypted_SSS,
                                                    TIN = encrypted_TIN,
                                                    Remarks = Remarks,
                                                    FacultyId = current_user.FacultyId)
            
                db.session.add(add_record)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_AM'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Agency-Membership.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               data = data,
                               decrypted_GSIS = decrypted_GSIS,
                               decrypted_PAGIBIG = decrypted_PAGIBIG,
                               decrypted_PHILHEALTH = decrypted_PHILHEALTH,
                               decrypted_SSS = decrypted_SSS,
                               decrypted_TIN = decrypted_TIN,
                               activate_AM="active")  

# ------------------------------- END OF PDM AGENCY MEMBERSHIP  ---------------------------- 
 
# ------------------------------- PDM TEACHER INFORMATION ------------------------------

@PDM.route("/PDM-Teacher-Information", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_TI():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
      
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            information = request.form.get('information')
            type = request.form.get('type')
            id = request.form.get('id')

            u = update(FISPDS_TeacherInformation)
            u = u.values({"information": information,
                          "type": type
                          })
            
            u = u.where(FISPDS_TeacherInformation.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_TI'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Teacher-Information.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_TI="active")  

@PDM.route("/PDM-Teacher-Information/add-record", methods=['GET', 'POST'])
@login_required
def PDM_TIadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
           
            information = request.form.get('information')
            type = request.form.get('type')
           
            add_record = FISPDS_TeacherInformation(information=information,
                                                type=type,
                                                FacultyId = current_user.FacultyId)
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_TI'))

@PDM.route("/PDM-Teacher-Information/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_TIdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_TeacherInformation.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_TI'))

# ------------------------------- END OF PDM TEACHER INFORMATION  ---------------------------- 
 
# ------------------------------- PDM CHARACTER REFERENCE ------------------------------

@PDM.route("/PDM-Character-Reference", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_CR():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
      
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
           
            full_name = request.form.get('full_name')
            address = request.form.get('address')
            contact = request.form.get('contact')
            id = request.form.get('id')

            u = update(FISPDS_CharacterReference)
            u = u.values({"full_name": full_name,
                          "address": address,
                          "contact": contact,
                          })
            
            u = u.where(FISPDS_CharacterReference.id == id)
            db.session.execute(u)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_CR')) 
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Character-Reference.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_CR="active")

@PDM.route("/PDM-Character-Reference/add-record", methods=['GET', 'POST'])
@login_required
def PDM_CRadd():

         # INSERT RECORD
        
        if request.method == 'POST':
         
            # VALUES
            full_name = request.form.get('full_name')
            address = request.form.get('address')
            contact = request.form.get('contact')

            add_record = FISPDS_CharacterReference(full_name=full_name,
                                                   address=address,
                                                   contact=contact,
                                                FacultyId = current_user.FacultyId)
            
            db.session.add(add_record)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_CR'))

@PDM.route("/PDM-Character-Reference/delete-record", methods=['GET', 'POST'])
@login_required
def PDM_CRdel():

        # DELETE RECORD
         
        id = request.form.get('id')
        
        data = FISPDS_CharacterReference.query.filter_by(id=id).first() 
        
        if data:
            db.session.delete(data)
            db.session.commit()
            db.session.close()
            return redirect(url_for('PDM.PDM_CR'))

# ------------------------------- END OF PDM CHARACTER REFERENCE  ---------------------------- 
 
# ------------------------------- PDM SIGNATURE ------------------------------

@PDM.route("/PDM-Signature", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_S():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
        id = username.FacultyId
        
        # CHECKING IF PROFILE PIC EXIST
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic   
        
         # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_Signature:
            data = current_user
            
            # FETCHING USER ENCRYPTED SIGNATURE DATA
            fetch = FISPDS_Signature.query.filter_by(FacultyId=current_user.FacultyId).first()
            
            # FETCHING USER ENCRYPTED SIGNATURE DATA
            wet_signature = fetch.wet_signature
            
            if fetch.dict_certificate:
                dict_cert = fetch.dict_certificate
            else:
                dict_cert = "1bQcZE3rlJWhNXkMy7yjdWLNTxaKSDArL"
        else:
            # FETCHING DEFAULT BLANK IMAGE
            wet_signature = "1JIS5J0SPU_V5aOPAHACBxZ5hjhkHFfY4"
            dict_cert = "1bQcZE3rlJWhNXkMy7yjdWLNTxaKSDArL"
            
        # FETCHING STRING DATA FROM CLOUD    
        
        # FACULTY FIS WET SIGNATURE FOLDER ID
        folder = '1oLWdZCvLVTbhRc5XcXBqlw5H5wkqnBLu'
        file7 = drive.CreateFile(metadata={"parents": [{"id": folder}],'id': ''+ str(wet_signature)})
        
        signature_StringData = file7.GetContentString(''+ str(wet_signature))
        
        # DECRYPTING DATA TO CONVERT INTO IMAGE
        decrypted_signature = fernet.decrypt(signature_StringData[2:-1])
        
         # FACULTY FIS DICT CERTIFICATE FOLDER ID
        folder1 = '1KrXqzGYLm9ET4D6bPLwrP_QJGtCufkly'
        file7 = drive.CreateFile(metadata={"parents": [{"id": folder1}],'id': ''+ str(dict_cert)})
        
        dict_cert_StringData = file7.GetContentString(''+ str(dict_cert))
        
        # DECRYPTING DATA TO CONVERT INTO IMAGE
        decrypted_dict_cert = fernet.decrypt(dict_cert_StringData[2:-1])
        
        # UPDATE 
        
        if request.method == 'POST':
            file =  request.form.get('base64')
            
            # API BACKGROUND REMOVER 
            api_key = os.getenv('BGR_api_key')
            
            # Convert the base64 string to bytes
            image_data = base64.b64decode(file[22:])

            response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': image_data},
            data={'size': 'auto'},
            headers={'X-Api-Key': api_key}
            )

            base64_data = base64.b64encode(response.content)
            
            # ENCRYPTING IMAGE DATA
            encrypted = fernet.encrypt(base64_data)
            
            data = """{}""".format(encrypted)
 
            if FISPDS_Signature.query.filter_by(FacultyId=current_user.FacultyId).first():
                
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
                    "mimeType": "text/plain"
                    })
                
                # GENERATE FILE AND UPLOAD
                file1.SetContentString(data)
                file1.Upload()
                
                u = update(FISPDS_Signature)
                u = u.values({"wet_signature": '%s'%(file1['id'])})
                u = u.where(FISPDS_Signature.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                db.session.close()
                
                return redirect(url_for('PDM.PDM_S')) 
            
            else:
                # CONFIGURE FILE FORMAT AND NAME
                file1 = drive.CreateFile(metadata={
                    "title": ""+ str(id),
                    "parents": [{"id": folder}],
                    "mimeType": "text/plain"
                    })
                
                # GENERATE FILE AND UPLOAD
                file1.SetContentString(data)
                file1.Upload()
                
                add_record = FISPDS_Signature( wet_signature = '%s'%(file1['id']),
                                            FacultyId = current_user.FacultyId)
                db.session.add(add_record)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_S'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Signature.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               signature = "data:image/png;base64," + decrypted_signature.decode('utf-8'),
                               dict_cert = decrypted_dict_cert.decode('utf-8'),
                               activate_Sig="active")
        
@PDM.route("/PDM-Signature/Submit_DICT", methods=['GET', 'POST'])
@login_required
def PDM_SS():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
        id = username.FacultyId

        # FACULTY FIS DICT CERTIFICATE FOLDER ID
        folder = '1KrXqzGYLm9ET4D6bPLwrP_QJGtCufkly'
        
        # UPDATE 
        
        if request.method == 'POST':
            file =  request.form.get('base64_dict')
            
            # ENCRYPTING IMAGE DATA
            encrypted = fernet.encrypt(file.encode('utf-8'))
            
            data = """{}""".format(encrypted)
 
            if FISPDS_Signature.query.filter_by(FacultyId=current_user.FacultyId).first():
                
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
                    "mimeType": "text/plain"
                    })
                
                # GENERATE FILE AND UPLOAD
                file1.SetContentString(data)
                file1.Upload()
                
                u = update(FISPDS_Signature)
                u = u.values({"dict_certificate": '%s'%(file1['id'])})
                u = u.where(FISPDS_Signature.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                db.session.close()
                
                return redirect(url_for('PDM.PDM_S')) 
            
            else:
                # CONFIGURE FILE FORMAT AND NAME
                file1 = drive.CreateFile(metadata={
                    "title": ""+ str(id),
                    "parents": [{"id": folder}],
                    "mimeType": "text/plain"
                    })
                
                # GENERATE FILE AND UPLOAD
                file1.SetContentString(data)
                file1.Upload()
                
                add_record = FISPDS_Signature( dict_certificate = '%s'%(file1['id']),
                                            FacultyId = current_user.FacultyId)
                db.session.add(add_record)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_S'))

# ------------------------------- END OF PDM SIGNATURE  ---------------------------- 
 
# ------------------------------- PDM ADDITIONAL QUESTIONS ------------------------------
  
@PDM.route("/PDM-Additional-Questions", methods=['GET', 'POST'])
@login_required
@Check_Token
def PDM_AQ():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
       
        # CHECKING IF PROFILE PIC EXIST
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic   
             
        # VERIFYING IF DATA OF CURRENT USER EXISTS
        if current_user.FISPDS_AdditionalQuestions:
            data = current_user
        else:
            data =  {'FISPDS_AdditionalQuestions':
                    {'q1_a':"",
                    'q1_a_details':"",
                    
                    'q1_b':"",
                    'q1_b_details':"",
                    
                    'q2_a':"",
                    'q2_a_details':"",
                    
                    'q2_b':"",
                    'q2_b_details':"",
                    
                    'q3':"",
                    'q3_details':"",
                    
                    'q4':"",
                    'q4_details':"",
                    
                    'q5_a':"",
                    'q5_a_details':"",
                    
                    'q5_b':"",
                    'q5_b_details':"",
                    
                    'q6':"",
                    'q6_details':"",
                    
                    'q7_a':"",
                    'q7_a_details':"",
                    
                    'q7_b':"",
                    'q7_b_details':"",
                    
                    'q7_c':"",
                    'q7_c_details':""
                    }
                    }
        
        # UPDATE 
        
        if request.method == 'POST':
         
            # VALUES
            q1_a = request.form.get('q1_a')
            q1_a_details = request.form.get('q1_a_details')
            
            q1_b = request.form.get('q1_b')
            q1_b_details = request.form.get('q1_b_details')
            
            q2_a = request.form.get('q2_a')
            q2_a_details = request.form.get('q2_a_details')
            
            q2_b = request.form.get('q2_b')
            q2_b_details = request.form.get('q2_b_details')
            
            q3 = request.form.get('q3')
            q3_details = request.form.get('q3_details')
            
            q4 = request.form.get('q4')
            q4_details = request.form.get('q4_details')
            
            q5_a = request.form.get('q5_a')
            q5_a_details = request.form.get('q5_a_details')
            
            q5_b = request.form.get('q5_b')
            q5_b_details = request.form.get('q5_b_details')
            
            q6 = request.form.get('q6')
            q6_details = request.form.get('q6_details')
            
            q7_a = request.form.get('q7_a')
            q7_a_details = request.form.get('q7_a_details')
            
            q7_b = request.form.get('q7_b')
            q7_b_details = request.form.get('q7_b_details')
            
            q7_c = request.form.get('q7_c')
            q7_c_details = request.form.get('q7_c_details')
           

            if FISPDS_AdditionalQuestions.query.filter_by(FacultyId=current_user.FacultyId).first():
                u = update(FISPDS_AdditionalQuestions)
                u = u.values({
                            "q1_a": q1_a,
                            "q1_a_details": q1_a_details,
                            
                            "q1_b": q1_b,
                            "q1_b_details": q1_b_details,
                            
                            "q2_a": q2_a,
                            "q2_a_details": q2_a_details,
                            
                            "q2_b": q2_b,
                            "q2_b_details": q2_b_details,
                            
                            "q3": q3,
                            "q3_details": q3_details,
                            
                            "q4": q4,
                            "q4_details": q4_details,
                            
                            "q5_a": q5_a,
                            "q5_a_details": q5_a_details,
                            
                            "q5_b": q5_b,
                            "q5_b_details": q5_b_details,
                            
                            "q6": q6,
                            "q6_details": q6_details,
                            
                            "q7_a": q7_a,
                            "q7_a_details": q7_a_details,
                            
                            "q7_b": q7_b,
                            "q7_b_details": q7_b_details,
                            
                            "q7_c": q7_c,
                            "q7_c_details": q7_c_details
                            })
                u = u.where(FISPDS_AdditionalQuestions.FacultyId == current_user.FacultyId)
                db.session.execute(u)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_AQ'))
            
            else:
                add_record = FISPDS_AdditionalQuestions(  
                                                    q1_a = q1_a,
                                                    q1_a_details= q1_a_details,
                                                    
                                                    q1_b = q1_b,
                                                    q1_b_details = q1_b_details,
                                                    
                                                    q2_a = q2_a,
                                                    q2_a_details = q2_a_details,
                                                    
                                                    q2_b = q2_b,
                                                    q2_b_details = q2_b_details,
                                                    
                                                    q3 = q3,
                                                    q3_details = q3_details,
                                                    
                                                    q4 = q4,
                                                    q4_details = q4_details,
                                                    
                                                    q5_a = q5_a,
                                                    q5_a_details = q5_a_details,
                                                    
                                                    q5_b = q5_b,
                                                    q5_b_details = q5_b_details,
                                                    
                                                    q6 = q6,
                                                    q6_details = q6_details,
                                                    
                                                    q7_a = q7_a,
                                                    q7_a_details = q7_a_details,
                                                    
                                                    q7_b = q7_b,
                                                    q7_b_details = q7_b_details,
                                                    
                                                    q7_c = q7_c,
                                                    q7_c_details= q7_c_details,
                                                    FacultyId = current_user.FacultyId)
            
                db.session.add(add_record)
                db.session.commit()
                db.session.close()
                return redirect(url_for('PDM.PDM_AQ'))
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Additional-Questions.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               data = data,
                               activate_AQ="active")
  
# ------------------------------- END OF PDM ADDITIONAL QUESTIONS  ---------------------------- 
 
# ------------------------------- PDM PERSONAL DATA REPORTS ------------------------------
   
  
@PDM.route("/PDM-Personal-Data-Reports")
@login_required
@Check_Token
def PDM_PDR():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
      
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/PDM-Personal-Data-Reports.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               PDM="show",
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               activate_PDR="active")
    
@PDM.route('/PDM-Personal-Data-Reports/0-Export')
@login_required
@Check_Token
def PDS_Export():
    
    from datetime import datetime
    # Get the current date and time
    current_datetime = datetime.now()

    # Extract only the current date
    current_date = current_datetime.date()
    
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
    PersonalDetails = FISPDS_PersonalDetails.query.filter_by(FacultyId=current_user.FacultyId).first() 
    ContactDetails = FISPDS_ContactDetails.query.filter_by(FacultyId=current_user.FacultyId).first() 
    FamilyDetails = FISPDS_FamilyBackground.query.filter_by(FacultyId=current_user.FacultyId).first() 
    EducationDetails = FISPDS_EducationalBackground.query.filter_by(FacultyId=current_user.FacultyId).first() 
    
    if FISPDS_EducationalBackground_Additional.query.filter_by(FacultyId=current_user.FacultyId, Level = "Graduate Studies").first():
        AdditionalEducation_grad = FISPDS_EducationalBackground_Additional.query.filter_by(FacultyId=current_user.FacultyId, Level = "Graduate Studies").first()
        
        additional_edu_grad_level = AdditionalEducation_grad.Level
        additional_edu_grad_school = AdditionalEducation_grad.School_Name
        additional_edu_grad_degree = AdditionalEducation_grad.Degree
        additional_edu_grad_units = AdditionalEducation_grad.Units
        additional_edu_grad_yeargrad = AdditionalEducation_grad.YearGraduated
        additional_edu_grad_from = AdditionalEducation_grad.From
        additional_edu_grad_to = AdditionalEducation_grad.To
        additional_edu_grad_honor = AdditionalEducation_grad.Scholarshi_Honor
    else:
        additional_edu_grad_level = ""
        additional_edu_grad_school = ""
        additional_edu_grad_degree = ""
        additional_edu_grad_units = ""
        additional_edu_grad_yeargrad = ""
        additional_edu_grad_from = ""
        additional_edu_grad_to = ""
        additional_edu_grad_honor = ""
    
    if FISPDS_EducationalBackground_Additional.query.filter_by(FacultyId=current_user.FacultyId, Level = "Vocational/Trade Course").first():
        AdditionalEducation_voc = FISPDS_EducationalBackground_Additional.query.filter_by(FacultyId=current_user.FacultyId, Level = "Vocational/Trade Course").first()
        
        additional_edu_voc_level = AdditionalEducation_voc.Level
        additional_edu_voc_school = AdditionalEducation_voc.School_Name
        additional_edu_voc_degree = AdditionalEducation_voc.Degree
        additional_edu_voc_units = AdditionalEducation_voc.Units
        additional_edu_voc_yeargrad = AdditionalEducation_voc.YearGraduated
        additional_edu_voc_from = AdditionalEducation_voc.From
        additional_edu_voc_to = AdditionalEducation_voc.To
        additional_edu_voc_honor = AdditionalEducation_voc.Scholarshi_Honor
    else:
        additional_edu_voc_level = ""
        additional_edu_voc_school = ""
        additional_edu_voc_degree = ""
        additional_edu_voc_units = ""
        additional_edu_voc_yeargrad = ""
        additional_edu_voc_from = ""
        additional_edu_voc_to = ""
        additional_edu_voc_honor = ""

    Children = FISPDS_FamilyBackground_Children.query.filter_by(FacultyId=current_user.FacultyId).limit(10).all()

    child_1 = Children[0] if len(Children) >= 1 else None
    child_2 = Children[1] if len(Children) >= 2 else None
    child_3 = Children[2] if len(Children) >= 3 else None
    child_4 = Children[3] if len(Children) >= 4 else None
    child_5 = Children[4] if len(Children) >= 5 else None
    child_6 = Children[5] if len(Children) >= 6 else None
    child_7 = Children[6] if len(Children) >= 7 else None
    child_8 = Children[7] if len(Children) >= 8 else None
    child_9 = Children[8] if len(Children) >= 9 else None
    child_10 = Children[9] if len(Children) >= 10 else None
    
    Eligibility = FISPDS_Eligibity.query.filter_by(FacultyId=current_user.FacultyId).limit(7).all()

    eligibility_1 = Eligibility[0] if len(Eligibility) >= 1 else None
    eligibility_2 = Eligibility[1] if len(Eligibility) >= 2 else None
    eligibility_3 = Eligibility[2] if len(Eligibility) >= 3 else None
    eligibility_4 = Eligibility[3] if len(Eligibility) >= 4 else None
    eligibility_5 = Eligibility[4] if len(Eligibility) >= 5 else None
    eligibility_6 = Eligibility[5] if len(Eligibility) >= 6 else None
    eligibility_7 = Eligibility[6] if len(Eligibility) >= 7 else None
    
    WorkExperience = FISPDS_WorkExperience.query.filter_by(FacultyId=current_user.FacultyId).limit(20).all()

    work_1 = WorkExperience[0] if len(WorkExperience) >= 1 else None
    work_2 = WorkExperience[1] if len(WorkExperience) >= 2 else None
    work_3 = WorkExperience[2] if len(WorkExperience) >= 3 else None
    work_4 = WorkExperience[3] if len(WorkExperience) >= 4 else None
    work_5 = WorkExperience[4] if len(WorkExperience) >= 5 else None
    work_6 = WorkExperience[5] if len(WorkExperience) >= 6 else None
    work_7 = WorkExperience[6] if len(WorkExperience) >= 7 else None
    work_8 = WorkExperience[7] if len(WorkExperience) >= 8 else None
    work_9 = WorkExperience[8] if len(WorkExperience) >= 9 else None
    work_10 = WorkExperience[9] if len(WorkExperience) >= 10 else None
    work_11 = WorkExperience[10] if len(WorkExperience) >= 11 else None
    work_12 = WorkExperience[11] if len(WorkExperience) >= 12 else None
    work_13 = WorkExperience[12] if len(WorkExperience) >= 13 else None
    work_14 = WorkExperience[13] if len(WorkExperience) >= 14 else None
    work_15 = WorkExperience[14] if len(WorkExperience) >= 15 else None
    work_16 = WorkExperience[15] if len(WorkExperience) >= 16 else None
    work_17 = WorkExperience[16] if len(WorkExperience) >= 17 else None
    work_18 = WorkExperience[17] if len(WorkExperience) >= 18 else None
    work_19 = WorkExperience[18] if len(WorkExperience) >= 19 else None
    work_20 = WorkExperience[19] if len(WorkExperience) >= 20 else None
   
    Voluntary = FISPDS_VoluntaryWork.query.filter_by(FacultyId=current_user.FacultyId).limit(10).all()

    Voluntary_1 = Voluntary[0] if len(Voluntary) >= 1 else None
    Voluntary_2 = Voluntary[1] if len(Voluntary) >= 2 else None
    Voluntary_3 = Voluntary[2] if len(Voluntary) >= 3 else None
    Voluntary_4 = Voluntary[3] if len(Voluntary) >= 4 else None
    Voluntary_5 = Voluntary[4] if len(Voluntary) >= 5 else None
    Voluntary_6 = Voluntary[5] if len(Voluntary) >= 6 else None
    Voluntary_7 = Voluntary[6] if len(Voluntary) >= 7 else None
    Voluntary_8 = Voluntary[7] if len(Voluntary) >= 8 else None
    Voluntary_9 = Voluntary[8] if len(Voluntary) >= 9 else None
    Voluntary_10 = Voluntary[9] if len(Voluntary) >= 10 else None
    
    Training = FISProfessionalDevelopment.query.filter_by(FacultyId=current_user.FacultyId).limit(10).all()

    Training_1 = Training[0] if len(Training) >= 1 else None
    Training_2 = Training[1] if len(Training) >= 2 else None
    Training_3 = Training[2] if len(Training) >= 3 else None
    Training_4 = Training[3] if len(Training) >= 4 else None
    Training_5 = Training[4] if len(Training) >= 5 else None
    Training_6 = Training[5] if len(Training) >= 6 else None
    Training_7 = Training[6] if len(Training) >= 7 else None
    Training_8 = Training[7] if len(Training) >= 8 else None
    Training_9 = Training[8] if len(Training) >= 9 else None
    Training_10 = Training[9] if len(Training) >= 10 else None
    Training_11 = Training[10] if len(Training) >= 11 else None
    Training_12 = Training[11] if len(Training) >= 12 else None
    Training_13 = Training[12] if len(Training) >= 13 else None
    Training_14 = Training[13] if len(Training) >= 14 else None
    Training_15 = Training[14] if len(Training) >= 15 else None
    Training_16 = Training[15] if len(Training) >= 16 else None
    Training_17 = Training[16] if len(Training) >= 17 else None
    Training_18 = Training[17] if len(Training) >= 18 else None
    Training_19 = Training[18] if len(Training) >= 19 else None
    Training_20 = Training[19] if len(Training) >= 20 else None
    
    Awards = FISPDS_OutstandingAchievements.query.filter_by(FacultyId=current_user.FacultyId).limit(10).all()

    Awards_1 = Awards[0] if len(Awards) >= 1 else None
    Awards_2 = Awards[1] if len(Awards) >= 2 else None
    Awards_3 = Awards[2] if len(Awards) >= 3 else None
    Awards_4 = Awards[3] if len(Awards) >= 4 else None
    Awards_5 = Awards[4] if len(Awards) >= 5 else None
    Awards_6 = Awards[5] if len(Awards) >= 6 else None
    Awards_7 = Awards[6] if len(Awards) >= 7 else None
    Awards_8 = Awards[7] if len(Awards) >= 8 else None
    Awards_9 = Awards[8] if len(Awards) >= 9 else None
    Awards_10 = Awards[9] if len(Awards) >= 10 else None
    
    Officeships = FISPDS_OfficeShipsMemberships.query.filter_by(FacultyId=current_user.FacultyId).limit(10).all()

    Officeships_1 = Officeships[0] if len(Officeships) >= 1 else None
    Officeships_2 = Officeships[1] if len(Officeships) >= 2 else None
    Officeships_3 = Officeships[2] if len(Officeships) >= 3 else None
    Officeships_4 = Officeships[3] if len(Officeships) >= 4 else None
    Officeships_5 = Officeships[4] if len(Officeships) >= 5 else None
    Officeships_6 = Officeships[5] if len(Officeships) >= 6 else None
    Officeships_7 = Officeships[6] if len(Officeships) >= 7 else None
    Officeships_8 = Officeships[7] if len(Officeships) >= 8 else None
    Officeships_9 = Officeships[8] if len(Officeships) >= 9 else None
    Officeships_10 = Officeships[9] if len(Officeships) >= 10 else None
    
    Additional_Question = FISPDS_AdditionalQuestions.query.filter_by(FacultyId=current_user.FacultyId).first()
    
    Reference = FISPDS_CharacterReference.query.filter_by(FacultyId=current_user.FacultyId).limit(2).all()

    Reference_1 = Reference[0] if len(Reference) >= 1 else None
    Reference_2 = Reference[1] if len(Reference) >= 2 else None
    
    # Generate a Fernet key
    key_bytes = os.getenv('Symmetric_Key').encode('utf-8')
    fernet_key = (key_bytes)
    cipher = Fernet(fernet_key)

    # VERIFYING IF DATA OF CURRENT USER EXISTS
    if current_user.FISPDS_AgencyMembership:
        data = current_user
        fetch = FISPDS_AgencyMembership.query.filter_by(FacultyId=current_user.FacultyId).first()
        
        # Decrypt the sensitive data
        GSIShex_bytes = bytes.fromhex(fetch.GSIS[2:])
        PAGIBIGhex_bytes = bytes.fromhex(fetch.PAGIBIG[2:])
        PHILHEALTHhex_bytes = bytes.fromhex(fetch.PHILHEALTH[2:])
        SSShex_bytes = bytes.fromhex(fetch.SSS[2:])
        TINhex_bytes = bytes.fromhex(fetch.TIN[2:])
    
        # Decrypt the ciphertext
        GSISdecrypted_data = cipher.decrypt(GSIShex_bytes)
        PAGIBIGdecrypted_data = cipher.decrypt(PAGIBIGhex_bytes)
        PHILHEALTHdecrypted_data = cipher.decrypt(PHILHEALTHhex_bytes)
        SSSdecrypted_data = cipher.decrypt(SSShex_bytes)
        TINdecrypted_data = cipher.decrypt(TINhex_bytes)
        
        # Decode the decrypted data to utf-8
        decrypted_GSIS = GSISdecrypted_data.decode('utf-8')
        decrypted_PAGIBIG = PAGIBIGdecrypted_data.decode('utf-8')
        decrypted_PHILHEALTH = PHILHEALTHdecrypted_data.decode('utf-8')
        decrypted_SSS = SSSdecrypted_data.decode('utf-8')
        decrypted_TIN = TINdecrypted_data.decode('utf-8')
        
    else:
        data =  {'FISPDS_AgencyMembership':
                {
                'Remarks':""
                }
                }
        # Decrypt the sensitive data
        decrypted_GSIS = ""
        decrypted_PAGIBIG = ""
        decrypted_PHILHEALTH = ""
        decrypted_SSS = ""
        decrypted_TIN = ""
    
    
    # SIGNATURE
    
     # VERIFYING IF DATA OF CURRENT USER EXISTS
    if current_user.FISPDS_Signature:
        data = current_user
        
        # FETCHING USER ENCRYPTED SIGNATURE DATA
        fetch = FISPDS_Signature.query.filter_by(FacultyId=current_user.FacultyId).first()
        
        # FETCHING USER ENCRYPTED SIGNATURE DATA
        wet_signature = fetch.wet_signature
        
    else:
        # FETCHING DEFAULT BLANK IMAGE
        wet_signature = "1JIS5J0SPU_V5aOPAHACBxZ5hjhkHFfY4"
        
        
    # FETCHING STRING DATA FROM CLOUD    
    
    # FACULTY FIS WET SIGNATURE FOLDER ID
    folder = '1oLWdZCvLVTbhRc5XcXBqlw5H5wkqnBLu'
    file7 = drive.CreateFile(metadata={"parents": [{"id": folder}],'id': ''+ str(wet_signature)})
    
    signature_StringData = file7.GetContentString(''+ str(wet_signature))
    
    # DECRYPTING DATA TO CONVERT INTO IMAGE
    decrypted_signature = fernet.decrypt(signature_StringData[2:-1])     
    
    return render_template('Faculty-Home-Page/Personal-Data-Management-Page/PDS/index.html',
                        User=username.FirstName + " " + username.LastName, 
                        PDM="show",
                        user = current_user,
                        
                        signature = "data:image/png;base64," + decrypted_signature.decode('utf-8'),
                        
                        PersonalDetails = PersonalDetails,
                        ContactDetails = ContactDetails,
                        FamilyDetails = FamilyDetails,
                        
                        child_1 = child_1, 
                        child_2 = child_2, 
                        child_3 = child_3, 
                        child_4 = child_4, 
                        child_5 = child_5, 
                        child_6 = child_6, 
                        child_7 = child_7, 
                        child_8 = child_8, 
                        child_9 = child_9, 
                        child_10 = child_10,
                        
                        eligibility_1 = eligibility_1,
                        eligibility_2 = eligibility_2,
                        eligibility_3 = eligibility_3,
                        eligibility_4 = eligibility_4,
                        eligibility_5 = eligibility_5,
                        eligibility_6 = eligibility_6,
                        eligibility_7 = eligibility_7,
                        
                        work_1 = work_1,
                        work_2 = work_2,
                        work_3 = work_3,
                        work_4 = work_4,
                        work_5 = work_5,
                        work_6 = work_6,
                        work_7 = work_7,
                        work_8 = work_8,
                        work_9 = work_9,
                        work_10 = work_10,
                        work_11 = work_11,
                        work_12 = work_12,
                        work_13 = work_13,
                        work_14 = work_14,
                        work_15 = work_15,
                        work_16 = work_16,
                        work_17 = work_17,
                        work_18 = work_18,
                        work_19 = work_19,
                        work_20 = work_20,
                        
                        Voluntary_1 = Voluntary_1,
                        Voluntary_2 = Voluntary_2,
                        Voluntary_3 = Voluntary_3,
                        Voluntary_4 = Voluntary_4,
                        Voluntary_5 = Voluntary_5,
                        Voluntary_6 = Voluntary_6,
                        Voluntary_7 = Voluntary_7,
                        Voluntary_8 = Voluntary_8,
                        Voluntary_9 = Voluntary_9,
                        Voluntary_10 = Voluntary_10,
                        
                        Training_1 = Training_1,
                        Training_2 = Training_2,
                        Training_3 = Training_3,
                        Training_4 = Training_4,
                        Training_5 = Training_5,
                        Training_6 = Training_6,
                        Training_7 = Training_7,
                        Training_8 = Training_8,
                        Training_9 = Training_9,
                        Training_10 = Training_10,
                        Training_11 = Training_11,
                        Training_12 = Training_12,
                        Training_13 = Training_13,
                        Training_14 = Training_14,
                        Training_15 = Training_15,
                        Training_16 = Training_16,
                        Training_17 = Training_17,
                        Training_18 = Training_18,
                        Training_19 = Training_19,
                        Training_20 = Training_20,
                        
                        Awards_1 = Awards_1,
                        Awards_2 = Awards_2,
                        Awards_3 = Awards_3,
                        Awards_4 = Awards_4,
                        Awards_5 = Awards_5,
                        Awards_6 = Awards_6,
                        Awards_7 = Awards_7,
                        Awards_8 = Awards_8,
                        Awards_9 = Awards_9,
                        Awards_10 = Awards_10,
                        
                        Officeships_1 = Officeships_1,
                        Officeships_2 = Officeships_2,
                        Officeships_3 = Officeships_3,
                        Officeships_4 = Officeships_4,
                        Officeships_5 = Officeships_5,
                        Officeships_6 = Officeships_6,
                        Officeships_7 = Officeships_7,
                        Officeships_8 = Officeships_8,
                        Officeships_9 = Officeships_9,
                        Officeships_10 = Officeships_10,
                        
                        Reference_1 = Reference_1,
                        Reference_2 = Reference_2,
                        
                        EducationDetails = EducationDetails,
                        
                        Additional_Question= Additional_Question,
                        
                        additional_edu_grad_level = additional_edu_grad_level,
                        additional_edu_grad_school = additional_edu_grad_school,
                        additional_edu_grad_degree = additional_edu_grad_degree,
                        additional_edu_grad_units = additional_edu_grad_units,
                        additional_edu_grad_yeargrad = additional_edu_grad_yeargrad,
                        additional_edu_grad_from = additional_edu_grad_from,
                        additional_edu_grad_to = additional_edu_grad_to,
                        additional_edu_grad_honor = additional_edu_grad_honor,
                        
                        additional_edu_voc_level = additional_edu_voc_level,
                        additional_edu_voc_school = additional_edu_voc_school,
                        additional_edu_voc_degree = additional_edu_voc_degree,
                        additional_edu_voc_units = additional_edu_voc_units,
                        additional_edu_voc_yeargrad = additional_edu_voc_yeargrad,
                        additional_edu_voc_from = additional_edu_voc_from,
                        additional_edu_voc_to = additional_edu_voc_to,
                        additional_edu_voc_honor = additional_edu_voc_honor,
                        
                        
                        age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                        decrypted_GSIS = decrypted_GSIS,
                        decrypted_PAGIBIG = decrypted_PAGIBIG,
                        decrypted_PHILHEALTH = decrypted_PHILHEALTH,
                        decrypted_SSS = decrypted_SSS,
                        decrypted_TIN = decrypted_TIN,
                        current_date  = current_date
                        )

# ------------------------------- END OF PDM PERSONAL DATA REPORTS  ---------------------------- 
 
# ------------------------------------------------------------- 




# ------------------------------- SETTINGS ------------------------------

@PDM.route("/Settings", methods=['GET', 'POST'])
@login_required
@Check_Token
def Settings():
    # INITIALIZING DATA FROM USER LOGGED IN ACCOUNT    
    
        username = FISFaculty.query.filter_by(FacultyId=current_user.FacultyId).first() 
      
        if username.ProfilePic == None:
            ProfilePic=profile_default
        else:
            ProfilePic=username.ProfilePic
        
        # UPDATE 
        
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
                    
                    u = update(FISFaculty)
                    u = u.values({"Password": Password})
                    
                    u = u.where(FISFaculty.FacultyId == current_user.FacultyId)
                    db.session.execute(u)
                    db.session.commit()
                    db.session.close()
                    
                    flash('Password successfully updated!', category='success')
                    return redirect(url_for('PDM.Settings'))
                 
                else:
                    flash('Invalid input! Password does not match...', category='error')
                    return redirect(url_for('PDM.Settings')) 
            else:
                flash('Invalid input! Password does not match...', category='error')
                return redirect(url_for('PDM.Settings')) 
                                
        return render_template("Faculty-Home-Page/Personal-Data-Management-Page/Settings.html", 
                               User=username.FirstName + " " + username.LastName, 
                               profile_pic=ProfilePic,
                               user = current_user,
                               age = str(calculateAge(date(current_user.BirthDate.year, current_user.BirthDate.month, current_user.BirthDate.day))),
                               )