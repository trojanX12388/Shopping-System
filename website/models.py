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
    ProfilePic = db.Column(db.String(50), default="1VikMpsCn5FpqbXd1Wny_EqOW92T8pFBt")
    Gender = db.Column(db.Integer)  # Gender # 1 if Male 2 if Female
    Email = db.Column(db.String(256))  
    Password = db.Column(db.String(256), nullable=False)  
    Status = db.Column(db.String(50), default="Deactivated")
    Login_Attempt = db.Column(db.Integer, default=12) 
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # RELATIONSHIP TABLES
    MSOrder = db.relationship('MSOrder', back_populates='MSAccount')
    MSRating = db.relationship('MSRating', back_populates='MSAccount')
    MSVoucher = db.relationship('MSVoucher', back_populates='MSAccount')
    MSProduct = db.relationship('MSProduct', back_populates='MSAccount')
    MSUser_Log = db.relationship('MSUser_Log', back_populates='MSAccount')
    MSCart = db.relationship('MSCart', back_populates='MSAccount')
    MSPurchase = db.relationship('MSPurchase', back_populates='MSAccount')
    MSPurchaseItem = db.relationship('MSPurchaseItem', back_populates='MSAccount')

    # Notification relationship (back_populates should match the one in MSNotification)
    notifications = db.relationship('MSNotification', back_populates='user')
    
    MSLoginToken = db.relationship('MSLoginToken', back_populates='MSAccount')

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
            'Gender': self.Gender,
            'Email': self.Email,
            'Password': self.Password,
            'Status': self.Status,
            'Login_Attempt': self.Login_Attempt,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'MSOrder': self.MSOrder,
            'MSRating': self.MSRating,
            'MSVoucher': self.MSVoucher,
            'MSProduct': self.MSProduct,
            'MSUser_Log': self.MSUser_Log,
            'MSCart': self.MSCart,
            'MSPurchase': self.MSPurchase,
            'MSPurchaseItem': self.MSPurchaseItem,
            'MSLoginToken': self.MSLoginToken,
            'notifications': self.notifications,  # Include notifications in the dict
        }

    def get_id(self):
        return str(self.MSId)  # Convert to string to ensure compatibility


# MS ORDER
  
class MSOrder(db.Model):
    __tablename__ = 'MSOrder'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    ProductId = db.Column(db.Integer, db.ForeignKey('MSProduct.id'), nullable=True)
    OrderId = db.Column(db.Numeric)
    OrderCount = db.Column(db.Numeric)
    OrderStatus = db.Column(db.String(50))
    OrderDate = db.Column(db.DateTime)
    OrderReceive = db.Column(db.DateTime)
    OrderVoucher = db.Column(db.String)
    is_delete = db.Column(db.Boolean, default=False) 
    MSAccount = db.relationship('MSAccount', back_populates='MSOrder')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductId': self.ProductId,
            'OrderId': self.OrderId,
            'OrderCount': self.OrderCount,
            'OrderStatus': self.OrderStatus,
            'OrderDate': self.OrderDate,
            'OrderReceive': self.OrderReceive,
            'OrderVoucher': self.OrderVoucher,
            'MSOrder': self.MSAccount,
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
    MSAccount = db.relationship('MSAccount', back_populates='MSVoucher')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'VoucherName': self.VoucherName,
            'VoucherDiscount': self.VoucherDiscount,
            'VoucherCode': self.VoucherCode,
            'MSVoucher': self.MSAccount,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility

# MS STORE
  
class MSStore(db.Model):
    __tablename__ = 'MSStore'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    StoreName = db.Column(db.String)
    Image = db.Column(db.String)
    Visits = db.Column(db.Numeric,default=0)
    is_delete = db.Column(db.Boolean, default=False) 

    MSProduct = db.relationship('MSProduct', back_populates='MSStore')
    MSPurchase = db.relationship('MSPurchase', back_populates='MSStore')

    def to_dict(self):
        return {
            'id': self.id,
            'StoreName': self.StoreName,
            'Image': self.Image,
            'Visits': self.Visits,
            'MSProduct': self.MSProduct,
            'MSPurchase': self.MSPurchase,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility

# MS RATING
  
class MSRating(db.Model):
    __tablename__ = 'MSRating'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    ProductId = db.Column(db.Integer, db.ForeignKey('MSProduct.id'), nullable=True)
    Rate1 = db.Column(db.Numeric)
    Rate2 = db.Column(db.Numeric)
    Rate3 = db.Column(db.Numeric)
    Rate4 = db.Column(db.Numeric)
    Rate5 = db.Column(db.Numeric)
    is_delete = db.Column(db.Boolean, default=False) 

    MSProduct = db.relationship('MSProduct', back_populates='MSRating')
    MSAccount = db.relationship('MSAccount', back_populates='MSRating')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductId': self.ProductId,
            'Rate1': self.Rate1,
            'Rate2': self.Rate2,
            'Rate3': self.Rate3,
            'Rate4': self.Rate4,
            'Rate5': self.Rate5,
            'MSProduct': self.MSProduct,
            'MSAccount': self.MSAccount,
            'is_delete': self.is_delete
        }
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility

# MS PRODUCT
  
class MSProduct(db.Model):
    __tablename__ = 'MSProduct'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    StoreId = db.Column(db.Integer, db.ForeignKey('MSStore.id'), nullable=True)
    ProductName = db.Column(db.String)
    ProductDescription = db.Column(db.String)
    ProductSerial = db.Column(db.String)
    ProductImage = db.Column(db.String)
    ProductInventory = db.Column(db.String)
    ProductViews = db.Column(db.Numeric, default=0)
    ProductPrice = db.Column(db.Float)
    ProductSale = db.Column(db.Float)
    ProductStock = db.Column(db.Numeric)
    is_delete = db.Column(db.Boolean, default=False) 

    MSAccount = db.relationship('MSAccount', back_populates='MSProduct')
    MSStore = db.relationship('MSStore', back_populates='MSProduct')
    MSRating = db.relationship('MSRating', back_populates='MSProduct')
    MSCart = db.relationship('MSCart', back_populates='MSProduct')
    MSPurchaseItem = db.relationship('MSPurchaseItem', back_populates='MSProduct')
    
    # Fix the relationship here
    MSNotification = db.relationship('MSNotification', back_populates='product')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductName': self.ProductName,
            'ProductDescription': self.ProductDescription,
            'ProductSerial': self.ProductSerial,
            'ProductImage': self.ProductImage,
            'ProductInventory': self.ProductInventory,
            'ProductViews': self.ProductViews,
            'ProductPrice': self.ProductPrice,
            'ProductSale': self.ProductSale,
            'ProductStock': self.ProductStock,
            'MSStore': self.MSStore,
            'MSRating': self.MSRating,
            'MSCart': self.MSCart,
            'MSPurchaseItem': self.MSPurchaseItem,
            'MSNotification': self.MSNotification,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility
    
# MS Purchase

class MSPurchase(db.Model):
    __tablename__ = 'MSPurchase'

    id = db.Column(db.Integer, primary_key=True)  # PurchaseID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=False)  # Customer Account
    StoreId = db.Column(db.Integer, db.ForeignKey('MSStore.id'), nullable=False)  # Store ID
    PurchaseDate = db.Column(db.DateTime, nullable=False, default=db.func.now())  # Purchase timestamp
    TotalAmount = db.Column(db.Float, nullable=False)  # Total cost of the purchase
    is_complete = db.Column(db.Boolean, default=False)  # Status of purchase (completed or not)
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default='pending'
    )  # Status of purchase (pending, packing, delivering, delivered)
    shipping_type = db.Column(db.String(20), nullable=False)  # Shipping type (e.g., 'walkin' or 'delivery')
    shipping_address = db.Column(db.String(255), nullable=True)  # Shipping address (optional, for 'delivery' only)

    MSAccount = db.relationship('MSAccount', back_populates='MSPurchase')
    MSStore = db.relationship('MSStore', back_populates='MSPurchase')
    MSPurchaseItem = db.relationship('MSPurchaseItem', back_populates='MSPurchase', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'StoreId': self.StoreId,
            'PurchaseDate': self.PurchaseDate.isoformat(),
            'TotalAmount': self.TotalAmount,
            'is_complete': self.is_complete,
            'status': self.status,
            'shipping_type': self.shipping_type,
            'shipping_address': self.shipping_address,
            'MSPurchaseItem': [item.to_dict() for item in self.MSPurchaseItem]
        }


class MSPurchaseItem(db.Model):
    __tablename__ = 'MSPurchaseItem'

    id = db.Column(db.Integer, primary_key=True)  # PurchaseItemID
    PurchaseId = db.Column(db.Integer, db.ForeignKey('MSPurchase.id'), nullable=False)  # Associated Purchase
    ProductId = db.Column(db.Integer, db.ForeignKey('MSProduct.id'), nullable=False)  # Product in the purchase
    Quantity = db.Column(db.Integer, nullable=False)  # Quantity of product purchased
    UnitPrice = db.Column(db.Float, nullable=False)  # Price per unit at the time of purchase
    TotalPrice = db.Column(db.Float, nullable=False)  # Total price for the quantity of the product
    ProductOwnerId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=False)  # Owner of the product

    MSPurchase = db.relationship('MSPurchase', back_populates='MSPurchaseItem')
    MSProduct = db.relationship('MSProduct', back_populates='MSPurchaseItem')
    MSNotification = db.relationship('MSNotification', back_populates='purchase_item')  # Make sure back_populates matches the MSNotification model
    MSAccount = db.relationship('MSAccount', back_populates='MSPurchaseItem')  # Owner relationship

    def to_dict(self):
        return {
            'id': self.id,
            'PurchaseId': self.PurchaseId,
            'ProductId': self.ProductId,
            'Quantity': self.Quantity,
            'UnitPrice': self.UnitPrice,
            'TotalPrice': self.TotalPrice,
            'ProductOwnerId': self.ProductOwnerId  # Add owner ID to the dictionary
        }


class MSNotification(db.Model):
    __tablename__ = 'MSNotification'

    id = db.Column(db.Integer, primary_key=True)  # Notification ID
    user_id = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=False)  # Owner of the product
    message = db.Column(db.String, nullable=False)  # Notification message
    is_seen = db.Column(db.Boolean, default=False)  # Whether the notification is seen by the user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp for when the notification is created
    product_id = db.Column(db.Integer, db.ForeignKey('MSProduct.id'), nullable=True)  # Product associated with the notification
    purchase_item_id = db.Column(db.Integer, db.ForeignKey('MSPurchaseItem.id'), nullable=True)  # Purchase item associated with the notification

    # Define relationships with MSAccount, MSProduct, and MSPurchaseItem
    user = db.relationship('MSAccount', back_populates='notifications')
    product = db.relationship('MSProduct', back_populates='MSNotification', lazy=True)  # Relationship with MSProduct
    purchase_item = db.relationship('MSPurchaseItem', back_populates='MSNotification', lazy=True)  # Relationship with MSPurchaseItem

    def __init__(self, user_id, message, product_id=None, purchase_item_id=None):
        self.user_id = user_id
        self.message = message
        self.product_id = product_id
        self.purchase_item_id = purchase_item_id


# LOGIN TOKEN
  
class MSLoginToken(db.Model):
    __tablename__ = 'MSLoginToken'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    is_delete = db.Column(db.Boolean, default=False) 

    MSAccount = db.relationship('MSAccount', back_populates='MSLoginToken')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'MSAccount': self.MSAccount,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility


# USER LOGS
  
class MSUser_Log(db.Model):
    __tablename__ = 'MSUser_Log'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)
    Type = db.Column(db.String(50), nullable=True)
    DateTime = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    Status = db.Column(db.String(50), default="success")
    Log = db.Column(db.String(50))
    is_delete = db.Column(db.Boolean, default=False) 

    MSAccount = db.relationship('MSAccount', back_populates='MSUser_Log')
    
    
    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'Type': self.Type,
            'DateTime': self.DateTime,
            'Status': self.Status,
            'Log': self.Log,
            'is_delete': self.is_delete,
            'MSAccount': self.MSAccount
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility  
    

# ------------------------------------------------
# # MS CART
  
class MSCart(db.Model):
    __tablename__ = 'MSCart'

    id = db.Column(db.Integer, primary_key=True)  # DataID
    MSId = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=True)  # 
    ProductId = db.Column(db.Integer, db.ForeignKey('MSProduct.id'), nullable=True)  # 
    notif_by = db.Column(db.Integer)
    notifier_type = db.Column(db.String(50))  
    DateTime = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    Status = db.Column(db.String(50), default="pending")
    Type = db.Column(db.String(50))
    Notification = db.Column(db.String)
    is_delete = db.Column(db.Boolean, default=False) 
    
    MSAccount = db.relationship('MSAccount', back_populates='MSCart')
    MSProduct = db.relationship('MSProduct', back_populates='MSCart')

    def to_dict(self):
        return {
            'id': self.id,
            'MSId': self.MSId,
            'ProductId': self.ProductId,
            'notif_by': self.notif_by,
            'notifier_type': self.notifier_type,
            'DateTime': self.DateTime,
            'updated_at': self.updated_at,
            'Status': self.Status,
            'Type': self.Type,
            'Notification': self.Notification,
            'MSAccount': self.MSAccount,
            'MSProduct': self.MSProduct,
            'is_delete': self.is_delete
        }
        
    def get_id(self):
        return str(self.id)  # Convert to string to ensure compatibility  

    
class MSMessage(db.Model):
    __tablename__ = 'MSMessage'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('MSAccount.MSId'), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Explicitly specify the foreign keys to each relationship
    sender = db.relationship('MSAccount', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    receiver = db.relationship('MSAccount', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy='dynamic'))

    def __repr__(self):
        return f'<Message from {self.sender.FirstName} to {self.receiver.FirstName}: {self.content}>'
        

def init_db(app):
    db.init_app(app)
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('MSAccount'):
            db.create_all()
            # create_sample_data()
        
#=====================================================================================================
# INSERTING DATA
def create_sample_data():
        
 # Create and insert MSAccount
    client_sample1 = MSAccount(
        MSId='10001',
        Type='Client',
        FirstName='Palma',
        LastName='Matter',
        MiddleName='Bryant',
        ContactNumber='09354510521',
        Address='41 Morning Star St. Brgy. San Isidro, Taytay Rizal',
        BirthDate= datetime.now(timezone.utc),
        ProfilePic='1VikMpsCn5FpqbXd1Wny_EqOW92T8pFBt',
        Age=35,
        Gender=2,

        Email='palma123@gmail.com',
        Password=generate_password_hash('palma123'),
        Status='Deactivated',
        # Add more attributes here
        )
    
    client_sample2 = MSAccount(
         MSId='10002',
        Type='Client',
        FirstName='Jonathan',
        LastName='Selaste',
        MiddleName='Kerakas',
        ContactNumber='09354510522',
        Address='44 Morning Star St. Brgy. San Isidro, Taytay Rizal',
        BirthDate= datetime.now(timezone.utc),
        ProfilePic='1VikMpsCn5FpqbXd1Wny_EqOW92T8pFBt',
        Age=25,
        Gender=1,

        Email='jonathan123@gmail.com',
        Password=generate_password_hash('jonathan123'),
        Status='Locked',
        # Add more attributes here
        )
    
  
    # ADD  DATA
    
    db.session.add(client_sample1)
    db.session.add(client_sample2)
    
    # COMMIT 
        
    db.session.commit()
    db.session.close()

    