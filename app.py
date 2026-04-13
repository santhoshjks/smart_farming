import os
import random
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    code_expires_at = db.Column(db.DateTime, nullable=True)
    
    def generate_verification_code(self):
        """Generate a 6-digit verification code valid for 10 minutes"""
        self.verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        return self.verification_code
    
    def verify_code(self, code):
        """Check if the provided code is valid and not expired"""
        if not self.verification_code or not self.code_expires_at:
            return False
        if self.verification_code == code and self.code_expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            self.is_verified = True
            self.verification_code = None
            self.code_expires_at = None
            return True
        return False
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# --- Load Disease Detection Dataset & Train Model ---
try:
    disease_df = pd.read_csv('data/Disease_Detection.csv')
    
    # Feature columns used for training
    disease_feature_cols = [
        'avg_red', 'avg_green', 'avg_blue',
        'std_red', 'std_green', 'std_blue',
        'green_ratio', 'disease_ratio', 'brown_ratio', 'yellow_ratio',
        'texture_contrast', 'texture_energy',
        'brightness', 'saturation'
    ]
    
    X_disease = disease_df[disease_feature_cols]
    y_disease = disease_df['label']
    
    # Build treatment lookup from dataset
    disease_treatment_map = disease_df.groupby('label')['treatment'].first().to_dict()
    
    # Train RandomForest model
    disease_model = RandomForestClassifier(n_estimators=100, random_state=42)
    disease_model.fit(X_disease, y_disease)
    print(f"Disease Detection Model trained successfully on {len(disease_df)} samples")
    
except Exception as e:
    print(f"Warning: Failed to load disease model: {e}")
    disease_model = None
    disease_treatment_map = {}

def extract_image_features(image_path):
    """Extract 14 color & texture features from a leaf image for ML prediction."""
    img = Image.open(image_path).convert('RGB')
    img = img.resize((256, 256))
    img_array = np.array(img, dtype=np.float64)
    
    # --- Color Statistics ---
    avg_red = np.mean(img_array[:, :, 0])
    avg_green = np.mean(img_array[:, :, 1])
    avg_blue = np.mean(img_array[:, :, 2])
    std_red = np.std(img_array[:, :, 0])
    std_green = np.std(img_array[:, :, 1])
    std_blue = np.std(img_array[:, :, 2])
    
    # --- Pixel Ratio Features ---
    total_pixels = 256 * 256
    
    # Green ratio: pixels where G channel dominates
    green_pixels = np.sum(
        (img_array[:, :, 1] > img_array[:, :, 0]) & 
        (img_array[:, :, 1] > img_array[:, :, 2])
    )
    green_ratio = green_pixels / total_pixels
    
    # Disease ratio: discolored pixels (R dominant, not healthy green)
    disease_pixels = np.sum(
        (img_array[:, :, 0] > img_array[:, :, 2]) & 
        (img_array[:, :, 0] > img_array[:, :, 1] * 0.8)
    )
    disease_ratio = disease_pixels / total_pixels
    
    # Brown ratio: dark reddish-brown pixels
    brown_pixels = np.sum(
        (img_array[:, :, 0] > 60) & (img_array[:, :, 0] < 160) &
        (img_array[:, :, 1] < img_array[:, :, 0]) &
        (img_array[:, :, 2] < img_array[:, :, 0] * 0.6)
    )
    brown_ratio = brown_pixels / total_pixels
    
    # Yellow ratio: yellowish pixels
    yellow_pixels = np.sum(
        (img_array[:, :, 0] > 120) & (img_array[:, :, 1] > 100) &
        (img_array[:, :, 2] < 80) &
        (np.abs(img_array[:, :, 0] - img_array[:, :, 1]) < 60)
    )
    yellow_ratio = yellow_pixels / total_pixels
    
    # --- Texture Features (simplified GLCM approximation) ---
    gray = np.mean(img_array, axis=2)
    # Contrast: average squared difference between adjacent pixels
    h_diff = np.diff(gray, axis=1) ** 2
    v_diff = np.diff(gray, axis=0) ** 2
    texture_contrast = (np.mean(h_diff) + np.mean(v_diff)) / (2 * 255 * 255)
    
    # Energy: sum of squared normalized pixel values (uniformity measure)
    normalized = gray / 255.0
    texture_energy = np.mean(normalized ** 2)
    
    # --- Global Features ---
    brightness = np.mean(img_array)
    
    # Saturation (simplified HSV saturation)
    max_ch = np.max(img_array, axis=2).astype(np.float64)
    min_ch = np.min(img_array, axis=2).astype(np.float64)
    sat = np.where(max_ch > 0, (max_ch - min_ch) / max_ch, 0)
    saturation = np.mean(sat)
    
    return [
        round(avg_red, 4), round(avg_green, 4), round(avg_blue, 4),
        round(std_red, 4), round(std_green, 4), round(std_blue, 4),
        round(green_ratio, 4), round(disease_ratio, 4),
        round(brown_ratio, 4), round(yellow_ratio, 4),
        round(texture_contrast, 4), round(texture_energy, 4),
        round(brightness, 4), round(saturation, 4)
    ]

def predict_disease_logic(image_path):
    """Predict plant disease using the trained RandomForest model on extracted image features."""
    try:
        features = extract_image_features(image_path)
        
        # Check if the image contains enough plant matter (leaf)
        green_ratio = features[6]
        disease_ratio = features[7]
        brown_ratio = features[8]
        yellow_ratio = features[9]
        
        plant_matter_ratio = green_ratio + disease_ratio + brown_ratio + yellow_ratio
        
        if plant_matter_ratio < 0.05:
            return "<strong style='font-size:1.2rem; color:#e74c3c;'>No Leaf Detected!</strong><br><br><span style='font-size:0.9rem; color:#bdc3c7'>Please upload a clear, focused image of a plant leaf. We could not detect enough plant matter in this photo.</span>"
        
        if disease_model:
            # Get probabilities for all classes
            probs = disease_model.predict_proba([features])[0]
            classes = disease_model.classes_
            
            # Sort by probability
            class_probs = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
            
            top_disease = class_probs[0][0]
            top_confidence = class_probs[0][1] * 100
            
            # Get treatment recommendation
            treatment = disease_treatment_map.get(top_disease, "Consult an agricultural expert.")
            
            # Determine severity from features
            dr = features[7]  # disease_ratio
            if "healthy" in top_disease.lower():
                severity = "None"
                severity_color = "#2ecc71"
            elif dr < 0.20:
                severity = "Mild"
                severity_color = "#f1c40f"
            elif dr < 0.35:
                severity = "Moderate"
                severity_color = "#e67e22"
            else:
                severity = "Severe"
                severity_color = "#e74c3c"
            
            # Build result string
            result = f"<strong style='font-size:1.2rem;'>{top_disease}</strong>"
            
            if "healthy" not in top_disease.lower():
                result += f"<br><span style='color:{severity_color}; font-weight:bold;'>Severity: {severity}</span>"
            
            
            
            # Show runner-up if close
            if len(class_probs) > 1 and class_probs[1][1] > 0.10:
               
            
            # Treatment
                result += f"<br><br><span style='font-size:0.85rem; color:#3498db'>💊 <strong>Treatment:</strong></span>"
                result += f"<br><span style='font-size:0.8rem; color:#bdc3c7'>{treatment}</span>"
            
                result += f"<br><br><span style='font-size:0.7rem; color:#7f8c8d'>🤖 Predicted by RandomForest model trained on {len(disease_df)} samples</span>"
            
            return result
        else:
            return "Disease detection model not available. Please check server logs."
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return "Error analyzing image"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('register'))
        
        # Check if user exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.is_verified:
                flash('Username or email already exists.', 'error')
                return redirect(url_for('register'))
            else:
                # Delete unverified user and allow re-registration
                db.session.delete(existing_user)
                db.session.commit()
        
        # Create new user (unverified)
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password, is_verified=False)
        verification_code = new_user.generate_verification_code()
        db.session.add(new_user)
        db.session.commit()
        
        # Store email in session for verification page
        session['pending_verification_email'] = email
        session['verification_code'] = verification_code  # For EmailJS to access
        
        flash('Please verify your email to complete registration.', 'info')
        return redirect(url_for('verify_email'))
    
    return render_template('register.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    email = session.get('pending_verification_email')
    
    if not email:
        flash('No pending verification. Please register first.', 'error')
        return redirect(url_for('register'))
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash('User not found. Please register again.', 'error')
        return redirect(url_for('register'))
    
    if user.is_verified:
        session.pop('pending_verification_email', None)
        session.pop('verification_code', None)
        flash('Email already verified! Please login.', 'success')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        if user.verify_code(code):
            db.session.commit()
            session.pop('pending_verification_email', None)
            session.pop('verification_code', None)
            flash('Email verified successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired verification code.', 'error')
    
    return render_template('verify_email.html', email=email, verification_code=session.get('verification_code'))

@app.route('/resend-code', methods=['POST'])
def resend_code():
    email = session.get('pending_verification_email')
    
    if not email:
        return jsonify({'success': False, 'error': 'No pending verification'})
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'})
    
    if user.is_verified:
        return jsonify({'success': False, 'error': 'Already verified'})
    
    # Generate new code
    new_code = user.generate_verification_code()
    db.session.commit()
    session['verification_code'] = new_code
    
    return jsonify({'success': True, 'code': new_code, 'message': 'New verification code generated'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            if not user.is_verified:
                # User exists but not verified - redirect to verification
                session['pending_verification_email'] = email
                verification_code = user.generate_verification_code()
                db.session.commit()
                session['verification_code'] = verification_code
                flash('Please verify your email first.', 'info')
                return redirect(url_for('verify_email'))
            
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            # Prevent open redirect — only allow relative URLs
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page if next_page else url_for('home'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/crop')
@login_required
def crop_page():
    return render_template('crop.html')

@app.route('/fertilizer')
@login_required
def fertilizer_page():
    return render_template('fertilizer.html')

@app.route('/disease')
@login_required
def disease_page():
    return render_template('disease.html')

@app.route('/simulation')
@login_required
def simulation_page():
    return render_template('simulation.html')

@app.route('/api/predict-disease', methods=['POST'])
def predict_disease():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        prediction = predict_disease_logic(filepath)
        return jsonify({'success': True, 'prediction': prediction, 'image_path': filename})

# --- Load Data & Train Crop Model on Startup ---
try:
    df = pd.read_csv('data/Crop_Recommendation.csv')
    print(f"Crop Data loaded with {len(df)} samples")
    
    # Train Random Forest
    from sklearn.preprocessing import LabelEncoder
    soil_encoder = LabelEncoder()
    season_encoder = LabelEncoder()
    water_encoder = LabelEncoder()

    df['soil_encoded'] = soil_encoder.fit_transform(df['soil_type'])
    df['season_encoded'] = season_encoder.fit_transform(df['season'])
    df['water_encoded'] = water_encoder.fit_transform(df['water'])

    X_crop = df[['soil_encoded', 'season_encoded', 'water_encoded', 'temperature', 'humidity']]
    y_crop = df['label']

    crop_rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    crop_rf_model.fit(X_crop, y_crop)
    print("Crop Random Forest Model trained successfully")
    
except Exception as e:
    print(f"Warning: Failed to load dataset or train crop model: {e}")
    df = None
    crop_rf_model = None

@app.route('/api/predict-crop-simplified', methods=['POST'])
def predict_crop_simplified():
    try:
        data = request.json
        soil_type = data.get('soil_type')
        season = data.get('season')
        water = data.get('water')


        # Season -> average weather fallback (aligned with new CSV data)
        season_profile = {
            'summer':  {'temp': 32, 'humidity': 45},
            'winter':  {'temp': 18, 'humidity': 25},
            'monsoon': {'temp': 26, 'humidity': 85},
            'autumn':  {'temp': 24, 'humidity': 60}
        }


        # Check if real-time weather data was provided from geolocation
        real_temp = data.get('real_temp')
        real_humidity = data.get('real_humidity')
        location_name = data.get('location_name', '')
        using_realtime = False

        if real_temp is not None and real_humidity is not None and str(real_temp).strip() != '':
            try:
                weather = {
                    'temp': float(real_temp),
                    'humidity': float(real_humidity)
                }
                using_realtime = True
            except (TypeError, ValueError):
                weather = season_profile.get(season, season_profile['autumn'])
        else:
            weather = season_profile.get(season, season_profile['autumn'])


        # Prediction (using Random Forest)
        if crop_rf_model is not None:
            try:
                soil_encoded_val = soil_encoder.transform([soil_type])[0]
            except Exception:
                soil_encoded_val = 0
                
            try:
                season_encoded_val = season_encoder.transform([season])[0]
            except Exception:
                season_encoded_val = 0
                
            try:
                water_encoded_val = water_encoder.transform([water])[0]
            except Exception:
                water_encoded_val = 0
                
            X_input = pd.DataFrame([[soil_encoded_val, season_encoded_val, water_encoded_val, weather['temp'], weather['humidity']]], columns=['soil_encoded', 'season_encoded', 'water_encoded', 'temperature', 'humidity'])
            
            # Get top 3 predictions
            probs = crop_rf_model.predict_proba(X_input)[0]
            classes = crop_rf_model.classes_
            top3_idx = np.argsort(probs)[-3:][::-1]
            top_crops = [classes[i] for i in top3_idx]
            
            prediction_list = [f"{str(c).capitalize()}" for c in top_crops]
            prediction = "<br>".join(prediction_list)
            prediction += "<br><span style='font-size:0.7rem; color:#7f8c8d'>🤖 Predicted by RandomForest model</span>"
        else:
            prediction = "Crop model not available. Please check server logs."

        # Build response with weather context
        response = {'success': True, 'prediction': prediction}
        response['weather_used'] = {
            'temperature': round(weather['temp'], 1),
            'humidity': round(weather['humidity'], 1),
            'source': 'realtime' if using_realtime else 'season_estimate'
        }
        if location_name:
            response['location'] = location_name

        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Load Fertilizer Data ---
try:
    fert_df = pd.read_csv('data/Fertilizer_Recommendation.csv')
    print(f"Fertilizer Data loaded with {len(fert_df)} samples.")
except Exception as e:
    print(f"Warning: Failed to load fertilizer data: {e}")
    fert_df = None

@app.route('/api/predict-fertilizer-simplified', methods=['POST'])
def predict_fertilizer_simplified():
    try:
        data = request.json
        symptoms_input = str(data.get('symptoms', 'healthy')).strip().lower()
        crop_input = str(data.get('crop_type', '')).strip().lower()
        soil_input = str(data.get('soil_type', '')).strip().lower()

        recommended_fertilizer = None

        # Load fresh data to ensure new additions are included immediately
        current_fert_df = pd.read_csv('data/Fertilizer_Recommendation.csv')
        
        if current_fert_df is not None:
            # Match case-insensitively and stripped from the CSV
            temp_df = current_fert_df.copy()
            temp_df['crop_type'] = temp_df['crop_type'].str.strip().str.lower()
            temp_df['soil_type'] = temp_df['soil_type'].str.strip().str.lower()
            temp_df['symptoms'] = temp_df['symptoms'].str.strip().str.lower()

            match = temp_df[
                (temp_df['crop_type'] == crop_input) & 
                (temp_df['soil_type'] == soil_input) & 
                (temp_df['symptoms'] == symptoms_input)
            ]
            
            if not match.empty:
                recommended_fertilizer = match['fertilizer_name'].iloc[0]

        if recommended_fertilizer is None:
            return jsonify({'success': True, 'prediction': "No exact fertilizer recommendation found for these conditions."})

        # 3. Calculate Quantity based on Land Size
        land_size = float(data.get('land_size', 1))
        land_unit = data.get('land_unit', 'acres')
        
        if land_unit == 'hectares':
            land_size = land_size * 2.47
        elif land_unit == 'sq_meter':
            land_size = land_size / 4046.86
            
        dosage_rate = 50 
        if 'Urea' in recommended_fertilizer: dosage_rate = 45
        elif 'DAP' in recommended_fertilizer: dosage_rate = 35
        elif 'MOP' in recommended_fertilizer: dosage_rate = 25
        elif 'NPK' in recommended_fertilizer: dosage_rate = 60
        elif '14-35-14' in recommended_fertilizer: dosage_rate = 55
        elif '10-26-26' in recommended_fertilizer: dosage_rate = 50
        elif 'Ammonium' in recommended_fertilizer: dosage_rate = 40
        elif '28-28' in recommended_fertilizer: dosage_rate = 50
        elif '17-17-17' in recommended_fertilizer: dosage_rate = 50
        
        total_qty = dosage_rate * land_size
        
        qty_str = f"{total_qty:.1f} kg"
        if total_qty > 1000:
            qty_str = f"{total_qty/1000:.2f} Tonnes"

        recommendation = f"{recommended_fertilizer}<br>"
        recommendation += f"<span style='font-size:1rem; color:#f1c40f; display:block; margin-top:8px;'>Required Quantity: <strong>{qty_str}</strong></span>"
        recommendation += f"<span style='font-size:0.8rem; color:#bdc3c7'>(Calculated for {data.get('land_size')} {land_unit} based on standard dosage)</span>"
        
        return jsonify({'success': True, 'prediction': recommendation})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
