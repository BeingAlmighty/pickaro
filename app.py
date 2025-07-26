import os
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, EmailField, TelField, SelectField, validators
from wtforms.validators import DataRequired, Email, Length, Regexp

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configuration
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None

# Google Sheets configuration
def get_google_sheet(sheet_name):
    try:
        import json
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Use environment variables for service account credentials
        creds_dict = {
            'type': 'service_account',
            'project_id': os.environ.get('GOOGLE_PROJECT_ID'),
            'private_key_id': os.environ.get('GOOGLE_PRIVATE_KEY_ID'),
            'private_key': os.environ.get('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n'),
            'client_email': os.environ.get('GOOGLE_CLIENT_EMAIL'),
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url': f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('GOOGLE_CLIENT_EMAIL', '').replace('@', '%40')}",
            'universe_domain': 'googleapis.com'
        }
        print("Using environment variables for service account credentials")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        print(f"Attempting to open sheet by URL, worksheet: {sheet_name}")
        sheet_url = os.environ.get('GOOGLE_SHEET_URL', 'https://docs.google.com/spreadsheets/d/1YpViCb3PIZm8G7WGGdrSG2PpfYK73qEgANAMRzhLu0o/edit?usp=sharing')
        sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
        print(f"Successfully opened worksheet: {sheet_name}")
        
        # Check if headers exist, if not add them
        setup_sheet_headers(sheet, sheet_name)
        
        return sheet
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")
        return None

def setup_sheet_headers(sheet, sheet_name):
    try:
        # Check if first row has headers
        first_row = sheet.row_values(1)
        
        if sheet_name == "Partners":
            headers = ["Restaurant Name", "Owner Name", "Email", "Phone", "Address", "Cuisine Type", "Experience", "Description"]
        elif sheet_name == "Pickaro Registration":
            headers = ["Restaurant Name", "Owner Name", "Email", "Phone", "Address", "Cuisine Type", "Experience", "Description"]
        elif sheet_name == "Promote":
            headers = ["Name", "Instagram ID", "City", "Followers", "Avg Story Views", "Avg Reel Views", "Story Charges", "Reel Charges", "Interested For", "Contact Number"]
        else:
            return
            
        # If no headers or wrong headers, set them
        if not first_row or first_row != headers:
            sheet.insert_row(headers, 1)
            print(f"Headers added to {sheet_name} sheet")
            
    except Exception as e:
        print(f"Error setting up headers: {e}")

# Partner Form
class PartnerForm(FlaskForm):
    restaurant_name = StringField('Restaurant Name', validators=[DataRequired(), Length(min=2, max=100)])
    owner_name = StringField('Owner Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = TelField('Phone Number', validators=[
        DataRequired(), 
        Regexp(r'^[0-9]{10}$', message="Phone number must be exactly 10 digits")
    ])
    address = TextAreaField('Restaurant Address', validators=[DataRequired(), Length(min=10, max=200)])
    cuisine_type = SelectField('Cuisine Type', choices=[
        ('indian', 'Indian'),
        ('chinese', 'Chinese'),
        ('italian', 'Italian'),
        ('mexican', 'Mexican'),
        ('fast_food', 'Fast Food'),
        ('south_indian', 'South Indian'),
        ('north_indian', 'North Indian'),
        ('continental', 'Continental'),
        ('desserts', 'Desserts'),
        ('beverages', 'Beverages'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    experience = SelectField('Restaurant Experience', choices=[
        ('new', 'New Restaurant'),
        ('1-2', '1-2 Years'),
        ('3-5', '3-5 Years'),
        ('5+', '5+ Years')
    ], validators=[DataRequired()])
    description = TextAreaField('Restaurant Description', validators=[Length(max=500)])

# Promote Form
class PromoteForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    instagram_id = StringField('Instagram ID', validators=[DataRequired(), Length(min=1, max=100)])
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=100)])
    followers = StringField('Followers', validators=[DataRequired()])
    avg_story_views = StringField('Avg. Story Views', validators=[DataRequired()])
    avg_reel_views = StringField('Avg. Reel Views', validators=[DataRequired()])
    story_charges = StringField('Story Charges', validators=[DataRequired()])
    reel_charges = StringField('Reel Charges', validators=[DataRequired()])
    interested_for = SelectField('Interested for', choices=[
        ('barter_only', 'Barter Deal Only'),
        ('payment_only', 'Payment Deal Only'),
        ('any_works', 'Any one of them works')
    ], validators=[DataRequired()])
    contact_number = TelField('Contact Number', validators=[
        DataRequired(), 
        Regexp(r'^[0-9]{10}$', message="Phone number must be exactly 10 digits")
    ])



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'message': 'Pickaro API is running'}, 200

@app.route('/become-partner', methods=['GET', 'POST'])
def become_partner():
    form = PartnerForm()
    if form.validate_on_submit():
        try:
            # Try Google Sheets first - store in Partners sheet
            sheet = get_google_sheet("Partners")
            if sheet:
                sheet.append_row([
                    form.restaurant_name.data,
                    form.owner_name.data,
                    form.email.data,
                    form.phone.data,
                    form.address.data,
                    form.cuisine_type.data,
                    form.experience.data,
                    form.description.data
                ])
                flash('Thank you! Your partner application has been submitted successfully.', 'success')
                return redirect(url_for('become_partner'))
            else:
                # Fallback: Log to console for now
                print("=== PARTNER APPLICATION SUBMITTED ===")
                print(f"Restaurant: {form.restaurant_name.data}")
                print(f"Owner: {form.owner_name.data}")
                print(f"Email: {form.email.data}")
                print(f"Phone: {form.phone.data}")
                print(f"Address: {form.address.data}")
                print(f"Cuisine: {form.cuisine_type.data}")
                print(f"Experience: {form.experience.data}")
                print(f"Description: {form.description.data}")
                print("=====================================")
                flash('Thank you! Your partner application has been received. (Note: Google Sheets integration needs to be configured)', 'success')
                return redirect(url_for('become_partner'))
        except Exception as e:
            print(f"Error: {e}")
            # Fallback: Log to console
            print("=== PARTNER APPLICATION (FALLBACK) ===")
            print(f"Restaurant: {form.restaurant_name.data}")
            print(f"Owner: {form.owner_name.data}")
            print(f"Email: {form.email.data}")
            print(f"Phone: {form.phone.data}")
            print(f"Address: {form.address.data}")
            print(f"Cuisine: {form.cuisine_type.data}")
            print(f"Experience: {form.experience.data}")
            print(f"Description: {form.description.data}")
            print("====================================")
            flash('Thank you! Your partner application has been received. (Note: Google Sheets integration needs to be configured)', 'success')
            return redirect(url_for('become_partner'))
    
    return render_template('partner_form.html', form=form)

@app.route('/promote-us', methods=['GET', 'POST'])
def promote_us():
    form = PromoteForm()
    if form.validate_on_submit():
        try:
            # Try Google Sheets first - store in Promote sheet
            sheet = get_google_sheet("Promote")
            if sheet:
                sheet.append_row([
                    form.name.data,
                    form.instagram_id.data,
                    form.city.data,
                    form.followers.data,
                    form.avg_story_views.data,
                    form.avg_reel_views.data,
                    form.story_charges.data,
                    form.reel_charges.data,
                    form.interested_for.data,
                    form.contact_number.data
                ])
                flash('Thank you! Your promotion application has been submitted successfully.', 'success')
                return redirect(url_for('promote_us'))
            else:
                # Fallback: Log to console for now
                print("=== PROMOTION APPLICATION SUBMITTED ===")
                print(f"Name: {form.name.data}")
                print(f"Instagram ID: {form.instagram_id.data}")
                print(f"City: {form.city.data}")
                print(f"Followers: {form.followers.data}")
                print(f"Avg Story Views: {form.avg_story_views.data}")
                print(f"Avg Reel Views: {form.avg_reel_views.data}")
                print(f"Story Charges: {form.story_charges.data}")
                print(f"Reel Charges: {form.reel_charges.data}")
                print(f"Interested For: {form.interested_for.data}")
                print(f"Contact Number: {form.contact_number.data}")
                print("========================================")
                flash('Thank you! Your promotion application has been received. (Note: Google Sheets integration needs to be configured)', 'success')
                return redirect(url_for('promote_us'))
        except Exception as e:
            print(f"Error: {e}")
            # Fallback: Log to console
            print("=== PROMOTION APPLICATION (FALLBACK) ===")
            print(f"Name: {form.name.data}")
            print(f"Instagram ID: {form.instagram_id.data}")
            print(f"City: {form.city.data}")
            print(f"Followers: {form.followers.data}")
            print(f"Avg Story Views: {form.avg_story_views.data}")
            print(f"Avg Reel Views: {form.avg_reel_views.data}")
            print(f"Story Charges: {form.story_charges.data}")
            print(f"Reel Charges: {form.reel_charges.data}")
            print(f"Interested For: {form.interested_for.data}")
            print(f"Contact Number: {form.contact_number.data}")
            print(f"======================================")
            flash('Thank you! Your promotion application has been received. (Note: Google Sheets integration needs to be configured)', 'success')
            return redirect(url_for('promote_us'))
    
    return render_template('promote_us.html', form=form)

@app.route('/download')
def download():
    # Placeholder for download analytics tracking
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
