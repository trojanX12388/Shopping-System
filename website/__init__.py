from flask import Flask, session
from flask_login import LoginManager
from dotenv import load_dotenv
from flask_mail import Mail
from datetime import timedelta
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate 
from flask_cors import CORS  # Import CORS

from .extensions import db

import os
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.json.sort_keys = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['REFRESH_TOKEN_SECRET'] = os.getenv('REFRESH_TOKEN_SECRET')
    
    # CONFIGURING POSTGRESQL CONNECTIONS
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}  
    app.config['SQLALCHEMY_POOL_SIZE'] = 10
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800
    
    migrate = Migrate()  # Define migrate instance
    migrate.init_app(app, db)  # Initialize migrate with the Flask app and db instance
    
    # SMTP CONFIGURATION

    app.config["MAIL_SERVER"]=os.getenv("MAILSERVER") 
    app.config["MAIL_PORT"]=os.getenv("MAILPORT") 
    app.config["MAIL_USERNAME"] = os.getenv("FISGMAIL")     
    app.config['MAIL_PASSWORD'] = os.getenv("FISGMAILPASS") 
    app.config['MAIL_DEFAULT_SENDER'] = 'PUPQC FIS'               
    app.config['MAIL_USE_TLS']=False
    app.config['MAIL_USE_SSL']=True
    
    # Enable CORS for all routes
    CORS(app, origins=["*"],
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
         expose_headers=["*"],
         max_age=600)
    
    # UPLOAD CONFIGURATION
    app.config['IMAGE_UPLOADS']='temp/'
    
    mail=Mail(app)
    jwt = JWTManager(app)    
    
    # LOADING DATABASE 
    from .models import init_db
    init_db(app)
    
    # LOADING MODEL CLASSES
    from .models import MSAccount
    
    # IMPORTING ROUTES
    from .views import views
    from .auth import auth
    from .API.api_app import API
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(API, url_prefix='/')
    
     # IMPORTING MODULES
    from .modules.Products import products
    app.register_blueprint(products, url_prefix='/')
    from .modules.Store import Store
    app.register_blueprint(Store, url_prefix='/')
    from .modules.Chat import Chat
    app.register_blueprint(Chat, url_prefix='/')
    from .modules.Purchase import purchase
    app.register_blueprint(purchase, url_prefix='/')
    from .modules.Sold import sold
    app.register_blueprint(sold, url_prefix='/')
    
    # # SYSTEM ADMIN ROUTES
    
    # from .modules.SystemAdmin import sysadmin
    # app.register_blueprint(sysadmin, url_prefix='/')
    
    # NOTIFICATION API ROUTES
    
    from .modules.Notifications import notification
    app.register_blueprint(notification, url_prefix='/')
    
    # LOADING LOGIN MANAGER CACHE
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login_denied'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        
        faculty_user = MSAccount.query.get(int(user_id))
        if faculty_user:
            return faculty_user
        
        return None  # Return None if user not found
    
    @app.before_request
    def before_request():
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=15)
        session.modified = True
    
    return app
    