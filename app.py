from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from datetime import datetime
import os
import io

# Import security components
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_bcrypt import Bcrypt # For password hashing
from models import db, User # Import db and User from models.py
from forms import RegistrationForm, LoginForm # Import forms
from config import Config # Import configuration

# Import reportlab components (your existing PDF logic)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.styles import ParagraphStyle

app = Flask(__name__)
app.config.from_object(Config) # Load config from Config class

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Where to redirect if login_required is used and user isn't logged in
login_manager.login_message_category = 'info' # Category for flash message

# --- Flask-Login user loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Configuration for PDF generation (still separate) ---
COMPANY_NAME = "Professional Inspection Services Inc."
COMPANY_LOGO_PATH = "company_logo.png"
CUSTOM_FONT_PATH = "Roboto-Regular.ttf"
FONT_NAME_NORMAL = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"
FONT_NAME_CUSTOM = "Roboto"

# --- Register custom font if available ---
try:
    if os.path.exists(CUSTOM_FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME_CUSTOM, CUSTOM_FONT_PATH))
        FONT_NAME_NORMAL = FONT_NAME_CUSTOM
        print(f"Custom font '{CUSTOM_FONT_PATH}' registered successfully.")
    else:
        print(f"Warning: Custom font file '{CUSTOM_FONT_PATH}' not found. Using default fonts.")
except Exception as e:
    print(f"Error registering custom font: {e}. Using default fonts.")

# --- Page Template Handler for Headers/Footers/Page Numbers ---
def _header_footer(canvas, doc):
    canvas.saveState()
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontName=FONT_NAME_NORMAL,
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        alignment=TA_RIGHT,
        spaceAfter=0
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=FONT_NAME_NORMAL,
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceBefore=0
    )

    # Header
    canvas.setFont(FONT_NAME_NORMAL, 9)
    canvas.setFillColor(colors.HexColor('#333333'))
    canvas.drawString(inch, letter[1] - 0.75 * inch, f"{COMPANY_NAME} - Inspection Report")
    canvas.drawString(letter[0] - 2 * inch, letter[1] - 0.75 * inch, doc.title)

    # Footer
    canvas.drawString(letter[0] / 2, 0.75 * inch, f"Page {doc.page}")
    canvas.restoreState()


# --- PDF Generation Function (same as previous revision) ---
def generate_inspection_report_pdf(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    doc.title = f"Claim #{data.get('claim_number', 'N/A')}"

    styles = getSampleStyleSheet()

    # Define styles
    style_title = ParagraphStyle(
        'ReportTitle',
        parent=styles['h1'],
        fontName=FONT_NAME_BOLD,
        fontSize=24,
        textColor=colors.HexColor('#0056b3'),
        alignment=TA_CENTER,
        spaceAfter=0.3 * inch
    )
    style_section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['h2'],
        fontName=FONT_NAME_BOLD,
        fontSize=16,
        textColor=colors.HexColor('#004085'),
        alignment=TA_LEFT,
        spaceBefore=0.2 * inch,
        spaceAfter=0.1 * inch,
    )
    style_label = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName=FONT_NAME_BOLD,
        fontSize=10,
        textColor=colors.black,
        spaceAfter=0.05 * inch
    )
    style_body = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName=FONT_NAME_NORMAL,
        fontSize=10,
        textColor=colors.black,
        alignment=TA_LEFT,
        leading=12
    )
    style_disclaimer = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName=FONT_NAME_NORMAL,
        fontSize=8,
        textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER,
        spaceBefore=0.2 * inch
    )
    story = []

    # --- Company Logo (if exists) ---
    if os.path.exists(COMPANY_LOGO_PATH):
        try:
            logo = Image(COMPANY_LOGO_PATH, width=2.0 * inch, height=1.0 * inch)
            logo.hAlign = 'CENTER' # <--- Logo Centered
            story.append(logo)
            story.append(Spacer(1, 0.1 * inch))
        except Exception as e:
            story.append(Paragraph(f"<i>Error loading logo: {e}</i>", style_body))
            print(f"Error loading company logo: {e}")

    # --- Report Title ---
    story.append(Paragraph(data.get('report_title', 'Inspection Report'), style_title))
    story.append(Spacer(1, 0.2 * inch))

    # --- Inspection Details Table ---
    details_data = [
        [Paragraph(f"<b>Inspector:</b>", style_label), Paragraph(data.get('inspector_name', ''), style_body)],
        [Paragraph(f"<b>Inspector Address:</b>", style_label), Paragraph(data.get('inspector_address', ''), style_body)],
        [Paragraph(f"<b>Adjuster Name:</b>", style_label), Paragraph(data.get('adjuster_name', ''), style_body)],
        [Paragraph(f"<b>Adjuster Number:</b>", style_label), Paragraph(data.get('adjuster_number', ''), style_body)],
        [Paragraph(f"<b>Adjuster Email:</b>", style_label), Paragraph(data.get('adjuster_email', ''), style_body)],
        [Paragraph(f"<b>Report Date:</b>", style_label), Paragraph(data.get('report_date', ''), style_body)],
        [Paragraph(f"<b>Claim Number:</b>", style_label), Paragraph(data.get('claim_number', ''), style_body)],
        [Paragraph(f"<b>Year Built:</b>", style_label), Paragraph(data.get('year_built', ''), style_body)],
    ]
    details_table = Table(details_data, colWidths=[1.7 * inch, 4.3 * inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(KeepTogether(details_table))
    story.append(Spacer(1, 0.2 * inch))

    # --- Cause of Loss ---
    story.append(Paragraph(data.get('cause_of_loss_heading', 'Cause of Loss'), style_section_heading))
    story.append(Paragraph(data.get('cause_of_loss', ''), style_body))
    story.append(Spacer(1, 0.2 * inch))

    # --- Resulting Damages ---
    story.append(Paragraph(data.get('resulting_damages_heading', 'Resulting Damages'), style_section_heading))
    story.append(Paragraph(data.get('resulting_damages', ''), style_body))
    story.append(Spacer(1, 0.2 * inch))

    # --- Scope of Work ---
    story.append(Paragraph(data.get('scope_of_work_heading', 'Scope of Work'), style_section_heading))
    for line in data.get('scope_of_work', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), style_body))
    story.append(Spacer(1, 0.2 * inch))

    # --- Recommendations ---
    story.append(Paragraph(data.get('recommendations_heading', 'Recommendations'), style_section_heading))
    for line in data.get('recommendations', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), style_body))
    story.append(Spacer(1, 0.2 * inch))

    # --- Reserves ---
    story.append(Paragraph(data.get('reserves_heading', 'Estimated Reserves'), style_section_heading))
    reserve_data = [['Category', 'Amount']]
    total_reserves = 0.0

    reserves_input_text = data.get('reserves_input', '').strip()
    if reserves_input_text:
        for line in reserves_input_text.split('\n'):
            if ':' in line:
                try:
                    category, amount_str = line.split(':', 1)
                    amount = float(amount_str.strip().replace('$', '').replace(',', ''))
                    reserve_data.append([category.strip(), f"${amount:,.2f}"])
                    total_reserves += amount
                except ValueError:
                    reserve_data.append([category.strip(), "Invalid Amount (N/A)"])
            else:
                reserve_data.append([line.strip(), "N/A"])

    reserve_data.append(['<b>Total Estimated Reserves</b>', f"<b>${total_reserves:,.2f}</b>"])

    reserve_table = Table(reserve_data, colWidths=[3.5 * inch, 2.0 * inch])
    reserve_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('FONTNAME', (0, -1), (-1, -1), FONT_NAME_BOLD),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F0F0F0')),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        ('TOPPADDING', (0, -1), (-1, -1), 8),
    ]))
    story.append(reserve_table)
    story.append(Spacer(1, 0.5 * inch))

    # --- Disclaimer ---
    story.append(PageBreak())
    story.append(Paragraph(data.get('disclaimer_heading', 'Disclaimer'), style_section_heading))
    story.append(Paragraph(data.get('disclaimer', ''), style_disclaimer))
    story.append(Spacer(1, 0.5 * inch))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buffer.seek(0)
    return buffer

# --- Flask Routes ---

# Home route - accessible to all
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', title='Home') # New simple home page

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('generate_report_form')) # If logged in, go to form
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('generate_report_form'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('generate_report_form'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

# Logout route
@app.route('/logout')
@login_required # Requires login to log out
def logout():
    logout_user()
    return redirect(url_for('home'))

# Main report generation form - requires login
@app.route('/generate_report', methods=['GET', 'POST'])
@login_required # <--- THIS ROUTE IS NOW PROTECTED
def generate_report_form():
    if request.method == 'POST':
        form_data = {
            'report_title': request.form.get('report_title', 'Inspection Report'),
            'inspector_name': request.form.get('inspector_name', ''),
            'inspector_address': request.form.get('inspector_address', ''),
            'adjuster_name': request.form.get('adjuster_name', ''),
            'adjuster_number': request.form.get('adjuster_number', ''),
            'adjuster_email': request.form.get('adjuster_email', ''),
            'report_date': request.form.get('report_date', ''),
            'claim_number': request.form.get('claim_number', ''),
            'year_built': request.form.get('year_built', ''),
            'cause_of_loss_heading': request.form.get('cause_of_loss_heading', 'Cause of Loss'),
            'cause_of_loss': request.form.get('cause_of_loss', ''),
            'resulting_damages_heading': request.form.get('resulting_damages_heading', 'Resulting Damages'),
            'resulting_damages': request.form.get('resulting_damages', ''),
            'scope_of_work_heading': request.form.get('scope_of_work_heading', 'Scope of Work'),
            'scope_of_work': request.form.get('scope_of_work', ''),
            'recommendations_heading': request.form.get('recommendations_heading', 'Recommendations'),
            'recommendations': request.form.get('recommendations', ''),
            'reserves_heading': request.form.get('reserves_heading', 'Estimated Reserves'),
            'reserves_input': request.form.get('reserves_input', ''),
            'disclaimer_heading': request.form.get('disclaimer_heading', 'Disclaimer'),
            'disclaimer': request.form.get('disclaimer', '')
        }

        try:
            pdf_buffer = generate_inspection_report_pdf(form_data)
            response = send_file(pdf_buffer,
                                 mimetype='application/pdf',
                                 as_attachment=True,
                                 download_name=f"Inspection_Report_{form_data['claim_number'] or 'NoClaim'}.pdf")
            return response
        except Exception as e:
            # When an error occurs, pass back the form_data so user doesn't lose input
            flash(f"Error generating PDF: {e}", 'danger')
            return render_template('index.html', form_data=form_data)

    # Pre-fill *all* fields with initial default values for GET requests
    # Current date in MDT (Calgary) format
    current_date_mdt = datetime.now().strftime("%B %d, %Y")

    default_data = {
        'report_title': "Property Inspection Report",
        'inspector_name': "John Doe",
        'inspector_address': "123 Inspection Lane, Suite 456, Calgary, AB T2Y 3X4",
        'adjuster_name': "Jane Smith",
        'adjuster_number': "555-123-4567",
        'adjuster_email': "jane.smith@example.com",
        'report_date': current_date_mdt,
        'claim_number': "CLM-2025-06-001",
        'year_built': "2005",
        'cause_of_loss_heading': "Cause of Loss",
        'cause_of_loss': "High winds caused a large tree branch to fall onto the roof, puncturing the shingles and underlying sheathing. The incident occurred during a severe thunderstorm.",
        'resulting_damages_heading': "Resulting Damages",
        'resulting_damages': "Significant damage to the roof structure, including compromised trusses and water infiltration into the attic space. Partial ceiling collapse in the master bedroom due to water saturation. Damage to drywall, insulation, and some personal belongings in the affected area. Minor water staining observed on walls in adjacent rooms.",
        'scope_of_work_heading': "Scope of Work",
        'scope_of_work': "1. Remove and dispose of damaged roofing materials and debris.\n2. Repair/replace compromised roof trusses and sheathing.\n3. Install new roofing underlayment and shingles (to match existing).\n4. Remove damaged ceiling and drywall in master bedroom.\n5. Dry affected areas and apply mold preventative.\n6. Replace insulation, drywall, and paint in affected areas.\n7. Clean and restore any salvageable personal belongings; document non-salvageable items.",
        'recommendations_heading': "Recommendations",
        'recommendations': "1. Recommend engaging a licensed roofing contractor for all roof repairs.\n2. Advise the homeowner to have a qualified electrician inspect wiring in the attic space due to potential water exposure.\n3. Suggest contacting an arborist to trim overhanging branches from other trees to prevent future incidents.",
        'reserves_heading': "Estimated Reserves",
        'reserves_input': "Roof Repair: 15000.00\nInterior Repair: 3500.00\nContents: 2000.00\nContingency: 2500.00",
        'disclaimer_heading': "Disclaimer",
        'disclaimer': (
            "This inspection report is based on observations made at the time of the inspection and represents "
            "the inspector's professional opinion. It is not an exhaustive list of all defects or conditions "
            "and does not constitute a warranty or guarantee of any kind. Further investigation by specialists "
            "may be required for certain findings. Estimated reserves are preliminary and subject to change based "
            "on detailed assessments and actual repair costs. All parties should independently verify any information "
            "contained herein and consult with appropriate professionals before making decisions."
        )
    }
    # Pass current_user to template for conditional display of links
    return render_template('index.html', form_data=default_data)

# Context processor to make current_user available in all templates
@app.context_processor
def inject_current_user():
    return dict(current_user=current_user)

# --- Database Initialization on First Run ---
with app.app_context():
    db.create_all() # Creates tables based on models.py if they don't exist
    # Optional: Create a default admin user on first run if no users exist
    if User.query.count() == 0:
        print("No users found. Creating a default admin user.")
        hashed_password = bcrypt.generate_password_hash('adminpass').decode('utf-8')
        admin_user = User(username='admin', email='admin@example.com', password_hash=hashed_password)
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user 'admin' (password: adminpass) created.")


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    if not os.path.exists(COMPANY_LOGO_PATH):
        print(f"\nWARNING: '{COMPANY_LOGO_PATH}' not found. Logo will not appear in PDF.")
    if not os.path.exists(CUSTOM_FONT_PATH):
        print(f"WARNING: '{CUSTOM_FONT_PATH}' not found. Custom font will not be used in PDF.")

    print("\n-----------------------------------------------------------")
    print("Flask app will run on http://127.0.0.1:5000/")
    print("To register: http://127.0.0.1:5000/register")
    print("To login: http://127.0.0.1:5000/login")
    print("Default admin user (if created): admin / adminpass")
    print("Press Ctrl+C to stop the server.")
    print("-----------------------------------------------------------\n")
    app.run(host="0.0.0.0", port=7000, debug=True)