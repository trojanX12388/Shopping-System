from datetime import datetime, timezone
from sqlalchemy import inspect
from flask_jwt_extended import create_access_token, decode_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_login import UserMixin
import ast
import pytz

from .extensions import db

 # MAE SHOPPING ACCOUNT MODEL 

class MSAccount(db.Model, UserMixin):
    __tablename__ = 'MSAccount'
    MSId = db.Column(db.Integer, primary_key=True, autoincrement=True)  # UserID
    Type = db.Column(db.String(50), nullable=False)  
    FirstName = db.Column(db.String(50))  
    LastName = db.Column(db.String(50))  
    MiddleName = db.Column(db.String(50))  
    ContactNumber = db.Column(db.String(11))
    Address = db.Column(db.String())
    BirthDate = db.Column(db.Date())
    ProfilePic = db.Column(db.String(50))
    Age = db.Column(db.Numeric, nullable=False)
    Gender = db.Column(db.Integer) # Gender # 1 if Male 2 if Female

    Email = db.Column(db.String(256))  
    Password = db.Column(db.String(256), nullable=False)  
    Status = db.Column(db.String(50), default="Deactivated")
    Login_Attempt = db.Column(db.Integer, default=12) 
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # RELATIONSHIP TABLES
    MSOrder = db.relationship('MSOrder')
    MSCart = db.relationship('MSCart')
    MSVoucher = db.relationship('MSVoucher')
    MSUser_Log = db.relationship('MSUser_Log')

    # LOGIN TOKEN
    MSLoginToken = db.relationship('MSLoginToken')
    


    def to_dict(self):
        return {
            'MSId': self.MSId,
            'MSType': self.Type,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'MiddleName': self.MiddleName,
            'ContactNumber': self.ContactNumber,
            'Address': self.Address,
            'BirthDate': self.BirthDate,
            'ProfilePic': self.ProfilePic,
            'Age': self.Age,
            'Gender': self.Gender,
            
            'Email': self.Email,
            'Password': self.Password,
            'Status': self.Status,
            'Login_Attempt': self.Login_Attempt,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            
            'MSOrder': self.MSOrder,
            'MSCart': self.MSCart,
            'MSVoucher': self.MSVoucher,
            'MSUser_Log': self.MSUser_Log,
            
            'MSLoginToken': self.MSLoginToken, 
        }
        
    def get_id(self):
        return str(self.MSId)  # Convert to string to ensure compatibility


# MS ORDER
  
class MSOrder(db.Model):
    __tablename__ = 'MSOrder'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    ProductSerial = db.Column(db.String)
    OrderId = db.Column(db.Numeric)
    OrderCount = db.Column(db.Numeric)
    OrderStatus = db.Column(db.String(50))
    OrderDate = db.Column(db.DateTime)
    OrderReceive = db.Column(db.DateTime)
    OrderVoucher = db.Column(db.String)
    is_delete = db.Column(db.Boolean, default=False) 

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductSerial': self.ProductSerial,
            'OrderId': self.OrderId,
            'OrderCount': self.OrderCount,
            'OrderStatus': self.OrderStatus,
            'OrderDate': self.OrderDate,
            'OrderReceive': self.OrderReceive,
            'OrderVoucher': self.OrderVoucher,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility
    
# MS CART
  
class MSCart(db.Model):
    __tablename__ = 'MSCart'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    ProductSerial = db.Column(db.String)
    ItemCount = db.Column(db.Numeric)
    is_delete = db.Column(db.Boolean, default=False) 

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductSerial': self.ProductSerial,
            'ItemCount': self.ItemCount,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility
    
# MS VOUCHER
  
class MSVoucher(db.Model):
    __tablename__ = 'MSVoucher'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    VoucherName = db.Column(db.String)
    VoucherDiscount = db.Column(db.Numeric)
    VoucherCode = db.Column(db.String)
    is_delete = db.Column(db.Boolean, default=False) 

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'VoucherName': self.VoucherName,
            'VoucherDiscount': self.VoucherDiscount,
            'VoucherCode': self.VoucherCode,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility
    
# MS PRODUCT
  
class MSProduct(db.Model):
    __tablename__ = 'MSProduct'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    ProductName = db.Column(db.String)
    ProductSerial = db.Column(db.String)
    ProductImage = db.Column(db.String)
    ProductInventory = db.Column(db.String)
    ProductPrice = db.Column(db.Float)
    ProductSale = db.Column(db.Float)
    ProductStock = db.Column(db.Numeric)
    is_delete = db.Column(db.Boolean, default=False) 

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductName': self.ProductName,
            'ProductSerial': self.ProductSerial,
            'ProductImage': self.ProductImage,
            'ProductInventory': self.ProductInventory,
            'ProductPrice': self.ProductPrice,
            'ProductSale': self.ProductSale,
            'ProductStock': self.ProductStock,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility
    

# LOGIN TOKEN
  
class MSLoginToken(db.Model):
    __tablename__ = 'MSLoginToken'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    is_delete = db.Column(db.Boolean, default=False) 

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility


# USER LOGS
  
class MSUser_Log(db.Model):
    __tablename__ = 'MSUser_Log'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    Type = db.Column(db.String(50), nullable=False)
    DateTime = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    Status = db.Column(db.String(50), default="success")
    Log = db.Column(db.String(50))
    is_delete = db.Column(db.Boolean, default=False) 
    
    
    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'Type': self.Type,
            'DateTime': self.DateTime,
            'Status': self.Status,
            'Log': self.Log,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility  
    




def init_db(app):
    db.init_app(app)
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('MSAccount'):
            db.create_all()
            # create_sample_data()
        
# #=====================================================================================================
# # INSERTING DATA
# def create_sample_data():
        
#  # Create and insert FISFaculty
 
# #     faculty_sample1 = FISFaculty(
# #         FacultyId='2020-00072-D-1',
# #         FacultyType='Full Time',
# #         Rank='Associate Professor II',
# #         Units = 8,
# #         Name='Alma Matter',
# #         FirstName='Palma',
# #         LastName='Matter',
# #         MiddleName='Bryant',
# #         MiddleInitial='B',
# #         NameExtension='',
# #         BirthDate= datetime.now(timezone.utc),
# #         DateHired= datetime.now(timezone.utc),
# #         Degree='Bachelor of Science in Computer Science',
# #         Remarks='',
# #         FacultyCode=91801,
# #         Honorific='N/A',
# #         Age=35,
# #         Email='alma123@gmail.com',
# #         Password=generate_password_hash('alma123'),
# #         # Add more attributes here
# #         )
    
# #     faculty_sample2 = FISFaculty(
# #         FacultyId='2020-00073-D-1',
# #         FacultyType='Part Time',
# #         Rank='Instructor I',
# #         Units = 6,
# #         Name='Andrew Bardoquillo',
# #         FirstName='Andrew',
# #         LastName='Bardoquillo',
# #         MiddleName='Lucero',
# #         MiddleInitial='L',
# #         NameExtension='',
# #         BirthDate= datetime.now(timezone.utc),
# #         DateHired= datetime.now(timezone.utc),
# #         Degree='Master in Business Administration',
# #         Remarks='',
# #         FacultyCode=51295,
# #         Honorific='N/A',
# #         Age=26,
# #         Email='robertandrewb.up@gmail.com',
# #         Password=generate_password_hash('plazma@123'),
# #         # Add more attributes here
# #         ) 
    
# #     faculty_sample3 = FISFaculty(
# #         FacultyId='2020-00076-D-4',
# #         FacultyType='Full Time',
# #         Rank='Instructor III',
# #         Units = 12,
# #         Name='Jason Derbis',
# #         FirstName='Jason',
# #         LastName='Derbis',
# #         MiddleName='Lucero',
# #         MiddleInitial='L',
# #         NameExtension='Jr.',
# #         BirthDate= datetime.now(timezone.utc),
# #         DateHired= datetime.now(timezone.utc),
# #         Degree='Master In Information Technology',
# #         Remarks='N/A',
# #         FacultyCode=81214,
# #         Honorific='N/A',
# #         Age=29,
# #         Email='sample123@gmail.com',
# #         Password=generate_password_hash('plazma@123'),
# #         # Add more attributes here
# #         ) 
  
#     # # ADD  DATA
    
#     # db.session.add(admin_sample1)
#     # db.session.add(admin_sample2)
 
#     # # COMMIT 
    
#     # db.session.commit()
#     # db.session.close()
    
    