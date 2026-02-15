from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import secrets
import qrcode
from io import BytesIO
import base64
import json
import os
import razorpay
from twilio.rest import Client
from sqlalchemy import func
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== DATABASE CONFIGURATION ====================
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'arjun2005')
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'hotel_booking')

USE_MYSQL = os.environ.get('USE_MYSQL', 'false').lower() == 'true'

if USE_MYSQL:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    print("Using MySQL Database")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel_booking.db'
    print("Using SQLite Database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_S68SvYAAXu0cPt')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '41iyf1rzanqDo2tEdY81shL1')

# Twilio Verify Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'AC08881a90f6eb1b605e62ca9b17aeb573')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'ad27eb1342919176ca37c17f7b393f5d')
TWILIO_VERIFY_SERVICE_SID = os.environ.get('TWILIO_VERIFY_SERVICE_SID', 'VA1429ee3f5f671600e432db5bfa23e1ea')

# OTP Configuration
MAX_OTP_RESEND_PER_DAY = 10

# Initialize services
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Initialize Twilio Verify Client
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    print("✅ Twilio Verify initialized successfully")
except Exception as e:
    twilio_client = None
    print(f"⚠️  Twilio not configured: {e}")

# UPI Payment Configuration
UPI_ID = os.environ.get('UPI_ID', '9209329727@ptaxis')
MERCHANT_NAME = os.environ.get('MERCHANT_NAME', 'Aman Rajbhar')

db = SQLAlchemy(app)
mail = Mail(app)

# ==================== JINJA2 CUSTOM FILTERS ====================

@app.template_filter('fromjson')
def fromjson_filter(value):
    """Custom Jinja2 filter to parse JSON strings"""
    if value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []

# ==================== DATABASE MODELS ====================
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        # Uses HMAC-SHA256 equivalent hashing for security
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class User(db.Model):
    """User model with mobile-based authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')
    otp_records = db.relationship('OTPRecord', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.phone}>'

class OTPRecord(db.Model):
    """OTP records for tracking attempts with daily limits"""
    __tablename__ = 'otp_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    purpose = db.Column(db.String(20), nullable=False)  # 'login', 'register'
    verification_sid = db.Column(db.String(100))  # Twilio verification SID
    status = db.Column(db.String(20), default='pending')  # pending, approved, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    verified_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(50))

    def __repr__(self):
        return f'<OTP {self.phone} - {self.status}>'

class Room(db.Model):
    """Room model for hotel room inventory"""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    room_type = db.Column(db.String(50), nullable=False, index=True)
    price_per_night = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    amenities = db.Column(db.Text)  # JSON string
    image_url = db.Column(db.String(200))
    is_available = db.Column(db.Boolean, default=True, index=True)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def __repr__(self):
        return f'<Room {self.room_number} - {self.room_type}>'

class Booking(db.Model):
    """Booking model for reservations"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    check_in = db.Column(db.Date, nullable=False, index=True)
    check_out = db.Column(db.Date, nullable=False, index=True)
    guests = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)
    booking_reference = db.Column(db.String(20), unique=True, index=True)
    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    payment = db.relationship('Payment', backref='booking', uselist=False, lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Booking {self.booking_reference}>'

class Payment(db.Model):
    """Payment model with Razorpay integration"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), default='pending', index=True)
    transaction_id = db.Column(db.String(100), unique=True, index=True)
    
    # Razorpay columns
    razorpay_order_id = db.Column(db.String(100), index=True)
    razorpay_payment_id = db.Column(db.String(100), index=True)
    razorpay_signature = db.Column(db.String(256))
    
    qr_code_data = db.Column(db.Text)
    payment_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.transaction_id}>'

# ==================== HELPER FUNCTIONS ====================

def normalize_phone(phone):
    """Normalize phone number to international format"""
    # Remove all non-digit characters
    phone = ''.join(filter(str.isdigit, phone))
    
    # Add country code if not present (India: +91)
    if len(phone) == 10:
        phone = '+91' + phone
    elif not phone.startswith('+'):
        phone = '+' + phone
    
    return phone

def check_otp_limit(phone):
    """Check if user has exceeded daily OTP limit"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    count = OTPRecord.query.filter(
        OTPRecord.phone == phone,
        OTPRecord.created_at >= today_start
    ).count()
    
    return count < MAX_OTP_RESEND_PER_DAY

def send_otp_via_twilio(phone):
    """Send OTP using Twilio Verify API"""
    try:
        if not twilio_client:
            print("⚠️  Twilio not configured - using development mode")
            # Generate a random 6-digit code for dev mode
            import random
            dev_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            print("="*60)
            print(f"📱 DEVELOPMENT MODE - OTP for {phone}")
            print(f"🔑 OTP Code: {dev_code}")
            print(f"⏰ Valid for 10 minutes")
            print("="*60)
            return {'success': True, 'sid': f'dev_{secrets.token_hex(8)}'}
        
        # Send verification using Twilio Verify
        verification = twilio_client.verify \
            .v2 \
            .services(TWILIO_VERIFY_SERVICE_SID) \
            .verifications \
            .create(to=phone, channel='sms')
        
        print(f"✅ OTP sent via Twilio Verify to {phone}")
        print(f"   Verification SID: {verification.sid}")
        return {'success': True, 'sid': verification.sid}
        
    except Exception as e:
        print(f"❌ Twilio Error: {e}")
        return {'success': False, 'error': str(e)}

def verify_otp_via_twilio(phone, code):
    """Verify OTP using Twilio Verify API"""
    try:
        if not twilio_client:
            print(f"⚠️  Development mode - accepting any 6-digit code")
            # In dev mode, accept any 6-digit code
            if len(code) == 6 and code.isdigit():
                return {'success': True, 'status': 'approved'}
            return {'success': False, 'error': 'Invalid code format'}
        
        # Verify using Twilio Verify
        verification_check = twilio_client.verify \
            .v2 \
            .services(TWILIO_VERIFY_SERVICE_SID) \
            .verification_checks \
            .create(to=phone, code=code)
        
        print(f"✅ Verification status: {verification_check.status}")
        
        if verification_check.status == 'approved':
            return {'success': True, 'status': 'approved'}
        else:
            return {'success': False, 'status': verification_check.status}
            
    except Exception as e:
        print(f"❌ Verification Error: {e}")
        return {'success': False, 'error': str(e)}

def generate_booking_reference():
    return f"HB{secrets.token_hex(4).upper()}"

def generate_qr_code(payment_data):
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=5)
        qr.add_data(payment_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except Exception as e:
        print(f"QR Code error: {e}")
        return None

def check_room_availability(room_id, check_in, check_out):
    overlapping_bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status.in_(['pending', 'confirmed']),
        db.or_(
            db.and_(Booking.check_in <= check_in, Booking.check_out > check_in),
            db.and_(Booking.check_in < check_out, Booking.check_out >= check_out),
            db.and_(Booking.check_in >= check_in, Booking.check_out <= check_out)
        )
    ).first()
    return overlapping_bookings is None

def send_booking_confirmation_email(user_email, booking_details):
    if not user_email:
        return False
    try:
        msg = Message('Booking Confirmation - Hotel Luxe', sender=app.config['MAIL_USERNAME'], recipients=[user_email])
        msg.body = f"""Dear {booking_details['user_name']},

Your booking has been confirmed!

Booking Reference: {booking_details['reference']}
Room Type: {booking_details['room_type']}
Room Number: {booking_details.get('room_number', 'TBA')}
Check-in: {booking_details['check_in']}
Check-out: {booking_details['check_out']}
Guests: {booking_details.get('guests', 'N/A')}
Total Amount: ₹{booking_details['total_price']}

Thank you for choosing Hotel Luxe!
"""
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to mobile number using Twilio Verify"""
    try:
        data = request.get_json()
        phone = normalize_phone(data.get('phone', ''))
        purpose = data.get('purpose', 'login')  # 'login' or 'register'
        
        if not phone or len(phone) < 12:
            return jsonify({'success': False, 'message': 'Invalid phone number'}), 400
        
        # Check daily OTP limit
        if not check_otp_limit(phone):
            return jsonify({
                'success': False, 
                'message': f'Maximum {MAX_OTP_RESEND_PER_DAY} OTP attempts per day exceeded. Try again tomorrow.'
            }), 429
        
        # Check if user exists
        existing_user = User.query.filter_by(phone=phone).first()
        
        if purpose == 'register' and existing_user:
            return jsonify({'success': False, 'message': 'Phone number already registered. Please login.'}), 400
        
        if purpose == 'login' and not existing_user:
            return jsonify({'success': False, 'message': 'Phone number not registered. Please register first.'}), 404
        
        # Send OTP via Twilio Verify
        result = send_otp_via_twilio(phone)
        
        if not result['success']:
            return jsonify({'success': False, 'message': 'Failed to send OTP'}), 500
        
        # Save OTP record
        otp_record = OTPRecord(
            user_id=existing_user.id if existing_user else None,
            phone=phone,
            purpose=purpose,
            verification_sid=result.get('sid'),
            ip_address=request.remote_addr
        )
        
        db.session.add(otp_record)
        db.session.commit()
        
        # Get remaining attempts
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        used_count = OTPRecord.query.filter(
            OTPRecord.phone == phone,
            OTPRecord.created_at >= today_start
        ).count()
        
        return jsonify({
            'success': True,
            'message': f'OTP sent to {phone}',
            'expires_in': 10,
            'attempts_remaining': MAX_OTP_RESEND_PER_DAY - used_count
        })
            
    except Exception as e:
        db.session.rollback()
        print(f"Send OTP error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error sending OTP'}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP using Twilio Verify and login/register user"""
    try:
        data = request.get_json()
        phone = normalize_phone(data.get('phone', ''))
        otp_code = data.get('otp', '')
        purpose = data.get('purpose', 'login')
        
        if not phone or not otp_code:
            return jsonify({'success': False, 'message': 'Phone and OTP required'}), 400
        
        # Verify OTP with Twilio
        verification_result = verify_otp_via_twilio(phone, otp_code)
        
        if not verification_result['success'] or verification_result.get('status') != 'approved':
            return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 401
        
        # Update OTP record
        otp_record = OTPRecord.query.filter_by(
            phone=phone,
            purpose=purpose
        ).order_by(OTPRecord.created_at.desc()).first()
        
        if otp_record:
            otp_record.status = 'approved'
            otp_record.verified_at = datetime.utcnow()
        
        if purpose == 'register':
            # Create new user
            full_name = data.get('full_name', '')
            email = data.get('email', '').lower().strip() if data.get('email') else None
            
            if not full_name:
                return jsonify({'success': False, 'message': 'Full name required'}), 400
            
            # Check if email already exists (if provided)
            if email and User.query.filter_by(email=email).first():
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            
            new_user = User(
                phone=phone,
                email=email,
                full_name=full_name,
                is_verified=True,
                last_login=datetime.utcnow()
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['user_name'] = new_user.full_name
            session['user_phone'] = new_user.phone
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': {
                    'id': new_user.id,
                    'name': new_user.full_name,
                    'phone': new_user.phone,
                    'email': new_user.email
                }
            })
        
        else:  # Login
            user = User.query.filter_by(phone=phone).first()
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['user_phone'] = user.phone
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'name': user.full_name,
                    'phone': user.phone,
                    'email': user.email
                }
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"Verify OTP error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Verification failed'}), 500

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP with daily limit check"""
    return send_otp()

# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rooms')
def rooms():
    all_rooms = Room.query.filter_by(is_available=True).all()
    return render_template('rooms.html', rooms=all_rooms)

@app.route('/login')
def login():
    return render_template('login_otp.html')

@app.route('/register')
def register():
    return render_template('register_otp.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get_or_404(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user = User.query.get_or_404(session['user_id'])
        
        if data.get('full_name'):
            user.full_name = data['full_name']
            session['user_name'] = user.full_name
        
        if data.get('email'):
            email = data['email'].lower().strip()
            existing = User.query.filter(User.email == email, User.id != user.id).first()
            if existing:
                return jsonify({'success': False, 'message': 'Email already in use'}), 400
            user.email = email
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== BOOKING ROUTES ====================

@app.route('/check-availability', methods=['POST'])
def check_availability():
    try:
        data = request.get_json()
        check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        
        if check_out <= check_in:
            return jsonify({'success': False, 'message': 'Invalid date range'}), 400
        
        query = Room.query.filter_by(is_available=True)
        if data.get('room_type'):
            query = query.filter_by(room_type=data['room_type'])
        
        available_rooms = []
        for room in query.all():
            if check_room_availability(room.id, check_in, check_out):
                available_rooms.append({
                    'id': room.id,
                    'room_number': room.room_number,
                    'room_type': room.room_type,
                    'price_per_night': room.price_per_night,
                    'capacity': room.capacity,
                    'description': room.description,
                    'amenities': json.loads(room.amenities) if room.amenities else [],
                    'image_url': room.image_url
                })
        
        return jsonify({'success': True, 'rooms': available_rooms})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error checking availability'}), 500

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
            
            if check_out <= check_in:
                return jsonify({'success': False, 'message': 'Invalid date range'}), 400
            
            if not check_room_availability(data['room_id'], check_in, check_out):
                return jsonify({'success': False, 'message': 'Room not available'}), 400
            
            room = Room.query.get(data['room_id'])
            if not room:
                return jsonify({'success': False, 'message': 'Room not found'}), 404
            
            nights = (check_out - check_in).days
            new_booking = Booking(
                user_id=session['user_id'],
                room_id=data['room_id'],
                check_in=check_in,
                check_out=check_out,
                guests=data['guests'],
                total_price=room.price_per_night * nights,
                booking_reference=generate_booking_reference(),
                special_requests=data.get('special_requests', '')
            )
            
            db.session.add(new_booking)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'booking_id': new_booking.id,
                'booking_reference': new_booking.booking_reference,
                'total_price': new_booking.total_price
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Booking failed'}), 500
    
    return render_template('booking.html')

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            payment_method = data['payment_method']
            
            payment = Payment(
                booking_id=booking_id,
                amount=booking.total_price,
                payment_method=payment_method,
                transaction_id=f"TXN{secrets.token_hex(6).upper()}"
            )
            
            if payment_method == 'razorpay':
                amount_in_paise = int(booking.total_price * 100)
                razorpay_order = razorpay_client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'receipt': booking.booking_reference,
                    'notes': {'booking_id': booking.id, 'user_id': session['user_id']}
                })
                
                payment.razorpay_order_id = razorpay_order['id']
                db.session.add(payment)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'payment_id': payment.id,
                    'transaction_id': payment.transaction_id,
                    'razorpay_order_id': razorpay_order['id'],
                    'razorpay_key_id': RAZORPAY_KEY_ID,
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'booking_reference': booking.booking_reference
                })
            
            elif payment_method == 'qr_code':
                upi_string = f"upi://pay?pa={UPI_ID}&pn={MERCHANT_NAME}&am={booking.total_price}&tr={payment.transaction_id}&tn=Booking{booking.booking_reference}"
                payment.qr_code_data = generate_qr_code(upi_string)
                db.session.add(payment)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'payment_id': payment.id,
                    'transaction_id': payment.transaction_id,
                    'qr_code': payment.qr_code_data
                })
            
        except Exception as e:
            db.session.rollback()
            print(f"Payment error: {e}")
            return jsonify({'success': False, 'message': f'Payment failed: {str(e)}'}), 500
    
    return render_template('payment.html', booking=booking, razorpay_key_id=RAZORPAY_KEY_ID)

@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        payment = Payment.query.filter_by(razorpay_order_id=data['razorpay_order_id']).first()
        
        if not payment or payment.booking.user_id != session['user_id']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })
        
        payment.razorpay_payment_id = data['razorpay_payment_id']
        payment.razorpay_signature = data['razorpay_signature']
        payment.payment_status = 'completed'
        payment.payment_date = datetime.utcnow()
        payment.booking.status = 'confirmed'
        db.session.commit()
        
        user = User.query.get(session['user_id'])
        if user.email:
            send_booking_confirmation_email(user.email, {
                'user_name': user.full_name,
                'reference': payment.booking.booking_reference,
                'room_type': payment.booking.room.room_type,
                'room_number': payment.booking.room.room_number,
                'check_in': payment.booking.check_in.strftime('%Y-%m-%d'),
                'check_out': payment.booking.check_out.strftime('%Y-%m-%d'),
                'guests': payment.booking.guests,
                'total_price': payment.booking.total_price
            })
        
        return jsonify({'success': True, 'message': 'Payment verified', 'booking_reference': payment.booking.booking_reference})
        
    except razorpay.errors.SignatureVerificationError:
        payment.payment_status = 'failed'
        db.session.commit()
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/confirm-payment/<int:payment_id>', methods=['POST'])
def confirm_payment(payment_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        payment = Payment.query.get_or_404(payment_id)
        if payment.booking.user_id != session['user_id']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        payment.payment_status = 'completed'
        payment.payment_date = datetime.utcnow()
        payment.booking.status = 'confirmed'
        db.session.commit()
        
        user = User.query.get(session['user_id'])
        if user.email:
            send_booking_confirmation_email(user.email, {
                'user_name': user.full_name,
                'reference': payment.booking.booking_reference,
                'room_type': payment.booking.room.room_type,
                'room_number': payment.booking.room.room_number,
                'check_in': payment.booking.check_in.strftime('%Y-%m-%d'),
                'check_out': payment.booking.check_out.strftime('%Y-%m-%d'),
                'guests': payment.booking.guests,
                'total_price': payment.booking.total_price
            })
        
        return jsonify({'success': True, 'message': 'Payment confirmed'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
        

@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('my_bookings.html', bookings=Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.created_at.desc()).all())

@app.route('/booking-details/<int:booking_id>')
def booking_details(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    return render_template('booking_details.html', booking=booking)

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        booking = Booking.query.get_or_404(booking_id)
        if booking.user_id != session['user_id']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        if booking.status in ['cancelled', 'completed']:
            return jsonify({'success': False, 'message': 'Cannot cancel'}), 400
        
        booking.status = 'cancelled'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Booking cancelled'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Admin routes - completely separate
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.json
        # Check admin credentials (separate from user login)
        if data['username'] == 'admin' and data['password'] == 'admin123':
            session['admin_authenticated'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    return render_template('admin-login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_authenticated'):
        return redirect('/admin/login')

    # Fetch all bookings and join with User and Room for complete details
    all_bookings = Booking.query.join(User).join(Room).order_by(Booking.id.desc()).all()
    
    # Calculate revenue for the dashboard cards
    total_rev = db.session.query(func.sum(Payment.amount)).filter(
        Payment.payment_status == 'completed'
    ).scalar() or 0

    return render_template('admin_dashboard.html', 
                           bookings=all_bookings, 
                           total_revenue=total_rev)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/admin/login')
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('index.html'), 500

# ==================== INITIALIZE DATABASE ====================

def init_db():
    with app.app_context():
        # COMMENT OUT OR DELETE THIS LINE TO PREVENT DATA LOSS IN THE FUTURE:
        # db.drop_all() 
            
        # This will create the tables if they are missing
        db.create_all()
        
        # Check if rooms exist so we don't duplicate them
        if Room.query.first() is None:
            rooms_data = [
                {'room_number': '101', 'room_type': 'Deluxe', 'price_per_night': 3500, 'capacity': 2, 'description': 'Luxurious deluxe room', 'amenities': json.dumps(['WiFi', 'AC', 'TV', 'Mini Bar']), 'image_url': '/static/images/deluxe-room.svg'},
                # ... other rooms ...
            ]
            for room_data in rooms_data:
                db.session.add(Room(**room_data))
            db.session.commit()
            print("✅ Database initialized and sample rooms added.")

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)