from flask import Flask, redirect, url_for, flash, session, request
from datetime import datetime
import jwt
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['REFRESH_TOKEN_SECRET'] = os.getenv('REFRESH_TOKEN_SECRET')

from website.models import MSLoginToken
from .token_gen import generate_access_token
from flask_login import current_user

# DATABASE CONNECTION
from website.models import db
from sqlalchemy import update


# CHECK TOKEN EXPIRATION
def Check_Token(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        session['previous_url'] = request.url
        
        if current_user.__class__.__name__ == "MSAccount":
            user_token = MSLoginToken.query.filter_by(MSId=current_user.MSId).first()
        elif current_user.__class__.__name__ == "FISAdmin":
            user_token = MSLoginToken.query.filter_by(AdminId=current_user.AdminId).first()
        else:
            # Handle other user types here if needed
            flash('Unknown user type.', category='error')
            return redirect(url_for('auth.Logout'))

        # Check if user_token exists
        if not user_token:
            flash('Account has been logged out. Please log in again.', category='error')
            if current_user.__class__.__name__ == "MSAccount":
                return redirect(url_for('auth.Logout'))
            else:
                return redirect(url_for('admin.adminLogout'))

        try:
            decoded = jwt.decode(user_token.access_token, app.config['SECRET_KEY'], algorithms=['HS256'])
            expiration_time = datetime.utcfromtimestamp(decoded['exp'])
            
            if datetime.utcnow() <= expiration_time:
                return func(*args, **kwargs)
            else:
                refresh_token(user_token)
                previous_url = session.pop('previous_url', None)
                if current_user.__class__.__name__ == "MSAccount":
                    return redirect(previous_url or url_for('auth.facultyH'))
                else:
                    return redirect(previous_url or url_for('admin.adminH'))
        
        except jwt.ExpiredSignatureError:
            try:
                decoded_refresh = jwt.decode(user_token.refresh_token, app.config['REFRESH_TOKEN_SECRET'], algorithms=['HS256'])
                refresh_expiration_time = datetime.utcfromtimestamp(decoded_refresh['exp'])
                
                if datetime.utcnow() >= refresh_expiration_time:
                    flash('Session Expired. Please Login again.', category='error')
                    if current_user.__class__.__name__ == "MSAccount":
                        return redirect(url_for('auth.Logout'))
                    else:
                        return redirect(url_for('admin.adminLogout'))
                else:
                    refresh_token(user_token)
                    previous_url = session.pop('previous_url', None)
                    if current_user.__class__.__name__ == "MSAccount":
                        return redirect(previous_url or url_for('auth.facultyH'))
                    else:
                        return redirect(previous_url or url_for('admin.adminH'))
            
            except jwt.ExpiredSignatureError:
                flash('Session Expired. Please Login again.', category='error')
                if current_user.__class__.__name__ == "MSAccount":
                    return redirect(url_for('auth.Logout'))
                else:
                    return redirect(url_for('admin.adminLogout'))
            
            except jwt.InvalidTokenError:
                flash('Invalid Token. Please Login again.', category='error')
                if current_user.__class__.__name__ == "MSAccount":
                    return redirect(url_for('auth.Logout'))
                else:
                    return redirect(url_for('admin.adminLogout'))
        
        except Exception as e:
            print(f'Error: {str(e)}')
            if current_user.__class__.__name__ == "MSAccount":
                return redirect(url_for('views.home'))
            else:
                return redirect(url_for('views.home'))
    
    return decorated


# REFRESH TOKEN
def refresh_token(user_token):
    refresh_token = user_token.refresh_token
    try:
        decoded_refresh_token = jwt.decode(refresh_token, app.config['REFRESH_TOKEN_SECRET'], algorithms=['HS256'])
        user_id = decoded_refresh_token['user_id']

        new_access_token = generate_access_token(user_id)
        
        if current_user.__class__.__name__ == "MSAccount":
            u = update(MSLoginToken)
            u = u.values({"access_token": new_access_token})
            u = u.where(MSLoginToken.MSId == current_user.MSId)
            db.session.execute(u)
        elif current_user.__class__.__name__ == "FISAdmin":
            u = update(MSLoginToken)
            u = u.values({"access_token": new_access_token})
            u = u.where(MSLoginToken.AdminId == current_user.AdminId)
            db.session.execute(u)
        else:
            # Handle other user types here if needed
            flash('Unknown user type.', category='error')
            if current_user.__class__.__name__ == "MSAccount":
                return redirect(url_for('auth.Logout'))
            else:
                return redirect(url_for('admin.adminLogout'))
        
        db.session.commit()
        db.session.close()
        
    except jwt.ExpiredSignatureError:
        if current_user.__class__.__name__ == "MSAccount":
            return redirect(url_for('auth.Logout'))
        else:
            return redirect(url_for('admin.adminLogout'))
    except jwt.InvalidTokenError:
        flash('Invalid User Token. Please Login again.', category='error')
        if current_user.__class__.__name__ == "MSAccount":
            return redirect(url_for('auth.Logout'))
        else:
            return redirect(url_for('admin.adminLogout'))
        
