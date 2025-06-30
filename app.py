import os
import pandas as pd
import smtplib
import bcrypt
import pymysql
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, IntegerField, TextAreaField, SelectField, FloatField
from wtforms.validators import DataRequired, Length, Email, NumberRange, ValidationError
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'abb-store-management-secret-key-2024')

# MySQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 
    f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DB', 'abb_store_management')}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {
        'charset': 'utf8mb4',
        'autocommit': True
    }
}

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration
app.config['SMTP_SERVER'] = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', 587))
app.config['SMTP_USERNAME'] = os.getenv('SMTP_USERNAME')
app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD')
app.config['SMTP_USE_TLS'] = True

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'manager', 'staff', name='user_roles'), nullable=False, default='staff')
    department = db.Column(db.String(100))
    employee_id = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships - removed conflicting backref
    user_requests = db.relationship('MaterialRequest', foreign_keys='MaterialRequest.user_id', lazy=True)
    transactions = db.relationship('Transaction', foreign_keys='Transaction.user_id', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']

class Material(db.Model):
    __tablename__ = 'materials'
    
    id = db.Column(db.Integer, primary_key=True)
    material_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    unit = db.Column(db.String(20), default='PCS')
    current_stock = db.Column(db.Numeric(10, 2), default=0.00)
    minimum_stock = db.Column(db.Numeric(10, 2), default=10.00)
    maximum_stock = db.Column(db.Numeric(10, 2), default=1000.00)
    unit_price = db.Column(db.Numeric(10, 2), default=0.00)
    location = db.Column(db.String(100))
    rack_number = db.Column(db.String(20))
    bin_number = db.Column(db.String(20))
    supplier = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships - removed conflicting backref
    material_requests = db.relationship('MaterialRequest', foreign_keys='MaterialRequest.material_id', lazy=True)
    transactions = db.relationship('Transaction', foreign_keys='Transaction.material_id', lazy=True)
    
    @property
    def is_low_stock(self):
        return float(self.current_stock) <= float(self.minimum_stock)
    
    @property
    def stock_value(self):
        return float(self.current_stock) * float(self.unit_price)

class MaterialRequest(db.Model):
    __tablename__ = 'material_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity_requested = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_approved = db.Column(db.Numeric(10, 2), default=0.00)
    purpose = db.Column(db.String(200))
    priority = db.Column(db.Enum('low', 'normal', 'high', 'urgent', name='priority_levels'), default='normal')
    status = db.Column(db.Enum('pending', 'approved', 'rejected', 'issued', 'cancelled', name='request_status'), default='pending')
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    approved_date = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    issued_date = db.Column(db.DateTime)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    remarks = db.Column(db.Text)
    
    # Relationships - explicit foreign_keys to avoid ambiguity
    material = db.relationship('Material', foreign_keys=[material_id])
    requester = db.relationship('User', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    issuer = db.relationship('User', foreign_keys=[issued_by])

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_type = db.Column(db.Enum('issue', 'receive', 'adjust', 'return', name='transaction_types'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0.00)
    reference_number = db.Column(db.String(100))
    purpose = db.Column(db.String(200))
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    remarks = db.Column(db.Text)
    
    # Relationships - explicit foreign_keys
    material = db.relationship('Material', foreign_keys=[material_id])
    user = db.relationship('User', foreign_keys=[user_id])
    
    @property
    def total_value(self):
        return abs(float(self.quantity)) * float(self.unit_price)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class UserRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    employee_id = StringField('Employee ID', validators=[DataRequired(), Length(max=50)])
    department = StringField('Department', validators=[Length(max=100)])
    role = SelectField('Role', choices=[('staff', 'Staff'), ('manager', 'Manager'), ('admin', 'Administrator')])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register User')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')
    
    def validate_employee_id(self, employee_id):
        user = User.query.filter_by(employee_id=employee_id.data).first()
        if user:
            raise ValidationError('Employee ID already exists.')

class MaterialForm(FlaskForm):
    material_number = StringField('Material Number', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = StringField('Category', validators=[Length(max=100)])
    unit = SelectField('Unit', choices=[('PCS', 'Pieces'), ('KG', 'Kilograms'), ('LTR', 'Liters'), ('MTR', 'Meters')])
    current_stock = FloatField('Current Stock', validators=[DataRequired(), NumberRange(min=0)])
    minimum_stock = FloatField('Minimum Stock', validators=[DataRequired(), NumberRange(min=0)])
    maximum_stock = FloatField('Maximum Stock', validators=[DataRequired(), NumberRange(min=0)])
    unit_price = FloatField('Unit Price', validators=[NumberRange(min=0)])
    location = StringField('Location', validators=[Length(max=100)])
    rack_number = StringField('Rack Number', validators=[Length(max=20)])
    bin_number = StringField('Bin Number', validators=[Length(max=20)])
    supplier = StringField('Supplier', validators=[Length(max=200)])
    submit = SubmitField('Save Material')
    
    def validate_material_number(self, material_number):
        material = Material.query.filter_by(material_number=material_number.data).first()
        if material and (not hasattr(self, 'material_id') or material.id != self.material_id):
            raise ValidationError('Material number already exists.')

class MaterialRequestForm(FlaskForm):
    material_id = SelectField('Material', coerce=int, validators=[DataRequired()])
    quantity_requested = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0.1)])
    purpose = StringField('Purpose', validators=[DataRequired(), Length(max=200)])
    priority = SelectField('Priority', choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')])
    submit = SubmitField('Submit Request')

class FileUploadForm(FlaskForm):
    file = FileField('Excel File', validators=[DataRequired(), FileAllowed(['xlsx', 'xls'], 'Excel files only!')])
    submit = SubmitField('Upload')

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utility functions
def send_email(to_email, subject, body):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['SMTP_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(app.config['SMTP_USERNAME'], app.config['SMTP_PASSWORD'])
        server.sendmail(app.config['SMTP_USERNAME'], to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        app.logger.error(f"Email sending failed: {str(e)}")
        return False

def send_low_stock_alerts():
    """Send low stock alerts to managers and admins"""
    low_stock_materials = Material.query.filter(
        Material.current_stock <= Material.minimum_stock,
        Material.is_active == True
    ).all()
    
    if not low_stock_materials:
        return
    
    managers = User.query.filter(User.role.in_(['admin', 'manager']), User.is_active == True).all()
    
    for manager in managers:
        subject = f"ABB Store Management - Low Stock Alert ({len(low_stock_materials)} items)"
        body = "The following materials are running low on stock:\n\n"
        
        for material in low_stock_materials:
            body += f"• {material.material_number} - {material.description}\n"
            body += f"  Current Stock: {material.current_stock} {material.unit}\n"
            body += f"  Minimum Stock: {material.minimum_stock} {material.unit}\n"
            body += f"  Location: {material.location or 'Not specified'}\n\n"
        
        body += "Please take necessary action to replenish the stock.\n\n"
        body += "Best regards,\nABB Store Management System"
        
        send_email(manager.email, subject, body)

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Dashboard statistics
    total_materials = Material.query.filter_by(is_active=True).count()
    low_stock_count = Material.query.filter(
        Material.current_stock <= Material.minimum_stock,
        Material.is_active == True
    ).count()
    
    pending_requests = MaterialRequest.query.filter_by(status='pending').count()
    total_stock_value = db.session.query(db.func.sum(Material.current_stock * Material.unit_price)).scalar() or 0
    
    # Recent activities
    recent_requests = MaterialRequest.query.order_by(MaterialRequest.request_date.desc()).limit(5).all()
    recent_transactions = Transaction.query.order_by(Transaction.transaction_date.desc()).limit(5).all()
    
    # Low stock materials
    low_stock_materials = Material.query.filter(
        Material.current_stock <= Material.minimum_stock,
        Material.is_active == True
    ).limit(10).all()
    
    return render_template('dashboard.html',
                         total_materials=total_materials,
                         low_stock_count=low_stock_count,
                         pending_requests=pending_requests,
                         total_stock_value=total_stock_value,
                         recent_requests=recent_requests,
                         recent_transactions=recent_transactions,
                         low_stock_materials=low_stock_materials)

@app.route('/materials')
@login_required
def materials():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = Material.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Material.material_number.contains(search),
                Material.description.contains(search)
            )
        )
    
    if category:
        query = query.filter_by(category=category)
    
    materials = query.order_by(Material.material_number).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = db.session.query(Material.category).distinct().filter(
        Material.category.isnot(None), Material.is_active == True
    ).all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('materials.html', materials=materials, categories=categories, search=search, category=category)

@app.route('/materials/add', methods=['GET', 'POST'])
@login_required
def add_material():
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('materials'))
    
    form = MaterialForm()
    if form.validate_on_submit():
        material = Material(
            material_number=form.material_number.data,
            description=form.description.data,
            category=form.category.data,
            unit=form.unit.data,
            current_stock=form.current_stock.data,
            minimum_stock=form.minimum_stock.data,
            maximum_stock=form.maximum_stock.data,
            unit_price=form.unit_price.data,
            location=form.location.data,
            rack_number=form.rack_number.data,
            bin_number=form.bin_number.data,
            supplier=form.supplier.data
        )
        
        db.session.add(material)
        db.session.commit()
        
        # Log transaction
        transaction = Transaction(
            material_id=material.id,
            user_id=current_user.id,
            transaction_type='receive',
            quantity=material.current_stock,
            unit_price=material.unit_price,
            purpose='Initial stock entry',
            remarks='Material added to system'
        )
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Material {material.material_number} added successfully!', 'success')
        return redirect(url_for('materials'))
    
    return render_template('material_form.html', form=form, title='Add Material')

@app.route('/materials/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_material(id):
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('materials'))
    
    material = Material.query.get_or_404(id)
    form = MaterialForm(obj=material)
    form.material_id = material.id
    
    if form.validate_on_submit():
        old_stock = material.current_stock
        
        form.populate_obj(material)
        material.last_updated = datetime.utcnow()
        
        # Log stock adjustment if changed
        if old_stock != material.current_stock:
            transaction = Transaction(
                material_id=material.id,
                user_id=current_user.id,
                transaction_type='adjust',
                quantity=material.current_stock - old_stock,
                unit_price=material.unit_price,
                purpose='Stock adjustment',
                remarks=f'Stock adjusted from {old_stock} to {material.current_stock}'
            )
            db.session.add(transaction)
        
        db.session.commit()
        flash(f'Material {material.material_number} updated successfully!', 'success')
        return redirect(url_for('materials'))
    
    return render_template('material_form.html', form=form, title='Edit Material', material=material)

@app.route('/materials/<int:id>/delete', methods=['POST'])
@login_required
def delete_material(id):
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('materials'))
    
    material = Material.query.get_or_404(id)
    material.is_active = False
    db.session.commit()
    
    flash(f'Material {material.material_number} deactivated successfully!', 'success')
    return redirect(url_for('materials'))

@app.route('/requests')
@login_required
def material_requests():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    if current_user.is_manager():
        query = MaterialRequest.query
    else:
        query = MaterialRequest.query.filter_by(user_id=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    requests = query.order_by(MaterialRequest.request_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('material_requests.html', requests=requests, status_filter=status_filter)

@app.route('/requests/new', methods=['GET', 'POST'])
@login_required
def new_request():
    form = MaterialRequestForm()
    
    # Populate material choices
    materials = Material.query.filter_by(is_active=True).order_by(Material.material_number).all()
    form.material_id.choices = [(m.id, f"{m.material_number} - {m.description}") for m in materials]
    
    if form.validate_on_submit():
        material = Material.query.get(form.material_id.data)
        
        request_obj = MaterialRequest(
            material_id=form.material_id.data,
            user_id=current_user.id,
            quantity_requested=form.quantity_requested.data,
            purpose=form.purpose.data,
            priority=form.priority.data
        )
        
        db.session.add(request_obj)
        db.session.commit()
        
        # Send notification to managers
        managers = User.query.filter(User.role.in_(['admin', 'manager']), User.is_active == True).all()
        for manager in managers:
            subject = f"New Material Request - {material.material_number}"
            body = f"""
A new material request has been submitted:

Material: {material.material_number} - {material.description}
Requested by: {current_user.username} ({current_user.department})
Quantity: {form.quantity_requested.data} {material.unit}
Purpose: {form.purpose.data}
Priority: {form.priority.data.title()}

Please review and approve/reject this request in the system.

Best regards,
ABB Store Management System
            """
            send_email(manager.email, subject, body)
        
        flash('Material request submitted successfully!', 'success')
        return redirect(url_for('material_requests'))
    
    return render_template('request_form.html', form=form, title='New Material Request')

@app.route('/requests/<int:id>/approve', methods=['POST'])
@login_required
def approve_request(id):
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('material_requests'))
    
    request_obj = MaterialRequest.query.get_or_404(id)
    
    if request_obj.status != 'pending':
        flash('Only pending requests can be approved.', 'warning')
        return redirect(url_for('material_requests'))
    
    approved_quantity = float(request.form.get('approved_quantity', request_obj.quantity_requested))
    remarks = request.form.get('remarks', '')
    
    if approved_quantity > request_obj.material.current_stock:
        flash('Insufficient stock to approve this request.', 'danger')
        return redirect(url_for('material_requests'))
    
    request_obj.status = 'approved'
    request_obj.quantity_approved = approved_quantity
    request_obj.approved_by = current_user.id
    request_obj.approved_date = datetime.utcnow()
    request_obj.remarks = remarks
    
    db.session.commit()
    
    # Send notification to requester
    subject = f"Material Request Approved - {request_obj.material.material_number}"
    body = f"""
Your material request has been approved:

Material: {request_obj.material.material_number} - {request_obj.material.description}
Requested Quantity: {request_obj.quantity_requested} {request_obj.material.unit}
Approved Quantity: {approved_quantity} {request_obj.material.unit}
Approved by: {current_user.username}

{f'Remarks: {remarks}' if remarks else ''}

Please collect the material from the store.

Best regards,
ABB Store Management System
    """
    send_email(request_obj.requester.email, subject, body)
    
    flash('Request approved successfully!', 'success')
    return redirect(url_for('material_requests'))

@app.route('/requests/<int:id>/reject', methods=['POST'])
@login_required
def reject_request(id):
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('material_requests'))
    
    request_obj = MaterialRequest.query.get_or_404(id)
    
    if request_obj.status != 'pending':
        flash('Only pending requests can be rejected.', 'warning')
        return redirect(url_for('material_requests'))
    
    remarks = request.form.get('remarks', '')
    
    request_obj.status = 'rejected'
    request_obj.approved_by = current_user.id
    request_obj.approved_date = datetime.utcnow()
    request_obj.remarks = remarks
    
    db.session.commit()
    
    # Send notification to requester
    subject = f"Material Request Rejected - {request_obj.material.material_number}"
    body = f"""
Your material request has been rejected:

Material: {request_obj.material.material_number} - {request_obj.material.description}
Requested Quantity: {request_obj.quantity_requested} {request_obj.material.unit}
Rejected by: {current_user.username}

{f'Reason: {remarks}' if remarks else ''}

Please contact your manager for more information.

Best regards,
ABB Store Management System
    """
    send_email(request_obj.requester.email, subject, body)
    
    flash('Request rejected successfully!', 'success')
    return redirect(url_for('material_requests'))

@app.route('/requests/<int:id>/issue', methods=['POST'])
@login_required
def issue_material(id):
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('material_requests'))
    
    request_obj = MaterialRequest.query.get_or_404(id)
    
    if request_obj.status != 'approved':
        flash('Only approved requests can be issued.', 'warning')
        return redirect(url_for('material_requests'))
    
    if request_obj.quantity_approved > request_obj.material.current_stock:
        flash('Insufficient stock to issue this material.', 'danger')
        return redirect(url_for('material_requests'))
    
    # Update material stock
    request_obj.material.current_stock -= request_obj.quantity_approved
    request_obj.material.last_updated = datetime.utcnow()
    
    # Update request status
    request_obj.status = 'issued'
    request_obj.issued_by = current_user.id
    request_obj.issued_date = datetime.utcnow()
    
    # Create transaction record
    transaction = Transaction(
        material_id=request_obj.material_id,
        user_id=current_user.id,
        transaction_type='issue',
        quantity=-request_obj.quantity_approved,
        unit_price=request_obj.material.unit_price,
        reference_number=f"REQ-{request_obj.id}",
        purpose=request_obj.purpose,
        remarks=f"Issued to {request_obj.requester.username} ({request_obj.requester.department})"
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    # Send notification to requester
    subject = f"Material Issued - {request_obj.material.material_number}"
    body = f"""
Your requested material has been issued:

Material: {request_obj.material.material_number} - {request_obj.material.description}
Quantity Issued: {request_obj.quantity_approved} {request_obj.material.unit}
Issued by: {current_user.username}
Issue Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Transaction Reference: REQ-{request_obj.id}

Best regards,
ABB Store Management System
    """
    send_email(request_obj.requester.email, subject, body)
    
    flash('Material issued successfully!', 'success')
    return redirect(url_for('material_requests'))

@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    transaction_type = request.args.get('type', '')
    
    query = Transaction.query
    
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    
    transactions = query.order_by(Transaction.transaction_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('transactions.html', transactions=transactions, transaction_type=transaction_type)

@app.route('/reports')
@login_required
def reports():
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Stock summary
    total_materials = Material.query.filter_by(is_active=True).count()
    low_stock_materials = Material.query.filter(
        Material.current_stock <= Material.minimum_stock,
        Material.is_active == True
    ).all()
    
    # Category-wise stock value
    category_stats = db.session.query(
        Material.category,
        db.func.count(Material.id).label('count'),
        db.func.sum(Material.current_stock * Material.unit_price).label('value')
    ).filter_by(is_active=True).group_by(Material.category).all()
    
    # Monthly transaction summary
    monthly_stats = db.session.query(
        db.func.strftime('%Y-%m', Transaction.transaction_date).label('month'),
        Transaction.transaction_type,
        db.func.count(Transaction.id).label('count'),
        db.func.sum(Transaction.quantity * Transaction.unit_price).label('value')
    ).group_by('month', Transaction.transaction_type).order_by('month').all()
    
    return render_template('reports.html',
                         total_materials=total_materials,
                         low_stock_materials=low_stock_materials,
                         category_stats=category_stats,
                         monthly_stats=monthly_stats)

@app.route('/users')
@login_required
def users():
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.username).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = UserRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            employee_id=form.employee_id.data,
            department=form.department.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('users'))
    
    return render_template('user_form.html', form=form, title='Add User')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_materials():
    if not current_user.is_manager():
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('materials'))
    
    form = FileUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            df = pd.read_excel(filepath)
            
            # Expected columns: material_number, description, category, unit, current_stock, minimum_stock, unit_price, location
            required_columns = ['material_number', 'description', 'current_stock']
            
            if not all(col in df.columns for col in required_columns):
                flash(f'Excel file must contain columns: {", ".join(required_columns)}', 'danger')
                return redirect(url_for('upload_materials'))
            
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    material = Material.query.filter_by(material_number=row['material_number']).first()
                    
                    if material:
                        # Update existing material
                        old_stock = material.current_stock
                        material.current_stock = float(row['current_stock'])
                        material.description = row['description']
                        material.category = row.get('category', material.category)
                        material.unit = row.get('unit', material.unit)
                        material.minimum_stock = float(row.get('minimum_stock', material.minimum_stock))
                        material.unit_price = float(row.get('unit_price', material.unit_price))
                        material.location = row.get('location', material.location)
                        material.last_updated = datetime.utcnow()
                        
                        # Log stock adjustment
                        if old_stock != material.current_stock:
                            transaction = Transaction(
                                material_id=material.id,
                                user_id=current_user.id,
                                transaction_type='adjust',
                                quantity=material.current_stock - old_stock,
                                unit_price=material.unit_price,
                                purpose='Bulk upload adjustment',
                                remarks=f'Stock updated via Excel upload'
                            )
                            db.session.add(transaction)
                    else:
                        # Create new material
                        material = Material(
                            material_number=row['material_number'],
                            description=row['description'],
                            category=row.get('category', ''),
                            unit=row.get('unit', 'PCS'),
                            current_stock=float(row['current_stock']),
                            minimum_stock=float(row.get('minimum_stock', 10)),
                            unit_price=float(row.get('unit_price', 0)),
                            location=row.get('location', '')
                        )
                        db.session.add(material)
                        db.session.flush()  # Get the ID
                        
                        # Log initial stock
                        transaction = Transaction(
                            material_id=material.id,
                            user_id=current_user.id,
                            transaction_type='receive',
                            quantity=material.current_stock,
                            unit_price=material.unit_price,
                            purpose='Initial stock via upload',
                            remarks='Material added via Excel upload'
                        )
                        db.session.add(transaction)
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    app.logger.error(f"Error processing row {index}: {str(e)}")
            
            db.session.commit()
            
            flash(f'Upload completed! {success_count} materials processed successfully. {error_count} errors.', 'success')
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
        
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
        
        return redirect(url_for('materials'))
    
    return render_template('upload.html', form=form)

@app.route('/api/low-stock-check')
@login_required
def api_low_stock_check():
    if not current_user.is_manager():
        return jsonify({'error': 'Access denied'}), 403
    
    send_low_stock_alerts()
    return jsonify({'message': 'Low stock alerts sent successfully'})

@app.route('/api/material/<int:id>')
@login_required
def api_material_details(id):
    material = Material.query.get_or_404(id)
    return jsonify({
        'id': material.id,
        'material_number': material.material_number,
        'description': material.description,
        'current_stock': material.current_stock,
        'unit': material.unit,
        'location': material.location,
        'is_low_stock': material.is_low_stock
    })

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# Initialize database
def init_db():
    """Initialize database connection and verify tables exist"""
    try:
        # Test database connection
        with db.engine.connect() as connection:
            result = connection.execute(db.text("SELECT COUNT(*) FROM users WHERE role = 'admin'"))
            admin_count = result.scalar()
            
            if admin_count == 0:
                print("Warning: No admin users found in database")
                print("Please ensure you have run the seed data scripts")
            else:
                print(f"Database connected successfully. Found {admin_count} admin user(s)")
                
        # Verify all tables exist
        inspector = db.inspect(db.engine)
        required_tables = ['users', 'materials', 'material_requests', 'transactions']
        existing_tables = inspector.get_table_names()
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            print(f"Warning: Missing tables: {missing_tables}")
            print("Please run the database setup scripts")
        else:
            print("All required tables found")
            
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        print("Please check your MySQL connection settings")

if __name__ == '__main__':
    try:
        with app.app_context():
            init_db()
        print("Starting ABB Store Management System...")
        print("Access the application at: http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Failed to start application: {str(e)}")
        print("Please check your database connection and configuration")
