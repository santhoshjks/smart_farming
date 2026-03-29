import os
import random
import time
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
    
    # Build treatment & severity lookup from dataset
    disease_treatment_map = disease_df.groupby('label')['treatment'].first().to_dict()
    
    # Train model
    disease_model = RandomForestClassifier(n_estimators=50, random_state=42)
    disease_model.fit(X_disease, y_disease)
    print("✅ Disease Detection Model trained successfully on data/Disease_Detection.csv")
    
except Exception as e:
    print(f"⚠️ Failed to load disease model: {e}")
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
    """Predict plant disease using the trained ML model on extracted image features."""
    try:
        features = extract_image_features(image_path)
        
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
            if top_disease == "Healthy":
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
            
            if top_disease != "Healthy":
                result += f"<br><span style='color:{severity_color}; font-weight:bold;'>Severity: {severity}</span>"
            
            result += f"<br><span style='font-size:0.9rem; color:#bdc3c7'>Confidence: {top_confidence:.1f}%</span>"
            
            # Show runner-up if close
            if len(class_probs) > 1 and class_probs[1][1] > 0.10:
                result += f"<br><span style='font-size:0.8rem; color:#95a5a6'>Also possible: {class_probs[1][0]} ({class_probs[1][1]*100:.0f}%)</span>"
            
            # Treatment
            result += f"<br><br><span style='font-size:0.85rem; color:#3498db'>💊 <strong>Treatment:</strong></span>"
            result += f"<br><span style='font-size:0.8rem; color:#bdc3c7'>{treatment}</span>"
            
            result += f"<br><br><span style='font-size:0.7rem; color:#7f8c8d'>🤖 Predicted by ML Model (RandomForest trained on 1,610 samples)</span>"
            
            return result
        else:
            # Fallback to basic heuristic if model failed to load
            img = Image.open(image_path).convert('RGB')
            img = img.resize((256, 256))
            img_array = np.array(img)
            
            green_ratio = features[6]
            disease_ratio = features[7]
            
            if green_ratio > 0.35:
                prediction = "Healthy (No obvious symptoms)"
                confidence = f"{min(green_ratio * 100 + 40, 99):.1f}%"
            elif disease_ratio > 0.15:
                prediction = "Possible Disease Detected"
                confidence = f"{min(disease_ratio * 100 + 50, 98):.1f}%"
            else:
                prediction = "Unknown / Low Leaf Content Detected"
                confidence = "LOW"
            
            return f"{prediction} <br><span style='font-size:0.8rem; color:#bdc3c7'>Confidence: {confidence} (Heuristic fallback - model not loaded)</span>"
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return "Error analyzing image"

# --- Routes ---

# Authentication Routes
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


# Main Routes
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
        
        # Simulate processing time
        time.sleep(1.5) 
        
        prediction = predict_disease_logic(filepath)
        return jsonify({'success': True, 'prediction': prediction, 'image_path': filename})



# --- Load Data & Train Model on Startup ---
try:
    # Load the "Kaggle" dataset (Mock version created locally)
    df = pd.read_csv('data/Crop_Recommendation.csv')
    
    # Prepare features and labels
    X = df[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
    y = df['label']
    
    # Train the model
    # optimizing for generalizability on small data
    crop_model = RandomForestClassifier(n_estimators=20, random_state=42) 
    crop_model.fit(X, y)
    print("✅ Model trained successfully on data/Crop_Recommendation.csv")
    
except Exception as e:
    print(f"⚠️ Failed to load dataset/train model: {e}")
    crop_model = None

@app.route('/api/predict-crop-simplified', methods=['POST'])
def predict_crop_simplified():
    try:
        data = request.json
        soil_type = data.get('soil_type')
        season = data.get('season')
        water = data.get('water')

        # Heuristic Mapping: Soil Type -> Avg Nutrient Content
        # (These are estimations based on general agricultural science)
        # We need these to convert user's "Clay Soil" selection into N, P, K numbers the model understands.
        soil_profile = {
            'clay': {'N': 90, 'P': 55, 'K': 40, 'ph': 5.8}, # Good for Rice
            'sandy': {'N': 20, 'P': 40, 'K': 50, 'ph': 5.5}, # Watermelon / Maize
            'loamy': {'N': 100, 'P': 40, 'K': 190, 'ph': 6.5}, # Grapes / cotton
            'black': {'N': 110, 'P': 50, 'K': 50, 'ph': 7.0}, # Cotton
            'red': {'N': 50, 'P': 50, 'K': 50, 'ph': 6.0} 
        }

        # Heuristic Mapping: Season -> Avg Weather
        season_profile = {
            'summer': {'temp': 30, 'humidity': 50, 'rain': 100},
            'winter': {'temp': 18, 'humidity': 20, 'rain': 50},
            'monsoon': {'temp': 25, 'humidity': 80, 'rain': 250},
            'autumn': {'temp': 24, 'humidity': 60, 'rain': 100}
        }

        profile = soil_profile.get(soil_type, soil_profile['loamy'])
        
        # Check if real-time data is provided
        real_temp = data.get('real_temp')
        real_humidity = data.get('real_humidity')
        
        if real_temp is not None and real_humidity is not None:
            # Use Real-time data
            try:
                weather = {
                    'temp': float(real_temp),
                    'humidity': float(real_humidity),
                    'rain': 100 # Default moderate rain if unknown, or infer from water availability
                }
            except (TypeError, ValueError):
                weather = season_profile.get(season, season_profile['autumn'])
        else:
            # Fallback to Season selection
            weather = season_profile.get(season, season_profile['autumn'])
        
        # Adjust rainfall based on water availability input
        if water == 'low': weather['rain'] -= 40
        if water == 'high': weather['rain'] += 80
        weather['rain'] = max(10, weather['rain']) # Prevent negative rain

        # Prediction Logic
        if crop_model:
            # Use the trained Machine Learning Model
            input_data = [[
                profile['N'], 
                profile['P'], 
                profile['K'],
                weather['temp'], 
                weather['humidity'], 
                profile['ph'], 
                weather['rain']
            ]]
            
            # Get probabilities for all classes
            probs = crop_model.predict_proba(input_data)[0]
            classes = crop_model.classes_
            
            # Create a list of (crop, probability) tuples
            class_probs = list(zip(classes, probs))
            
            # Sort by probability (highest first)
            class_probs.sort(key=lambda x: x[1], reverse=True)
            
            # Get Top 3 crops with > 10% confidence
            top_crops = [
                f"{c[0]} ({c[1]*100:.0f}%)" 
                for c in class_probs[:3] 
                if c[1] > 0.1
            ]
            
            if not top_crops:
                prediction = "No specific crop recommended (Low confidence)"
            else:
                prediction = "<br>".join(top_crops)
            
        else:
            prediction = "Model not loaded"

        return jsonify({'success': True, 'prediction': prediction})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Load Fertilizer Data & Train Model ---
try:
    fert_df = pd.read_csv('data/Fertilizer_Recommendation.csv')
    
    # New Kaggle Dataset Format
    # Temparature,Humidity ,Moisture,Soil Type,Crop Type,Nitrogen,Potassium,Phosphorous,Fertilizer Name
    soil_factors = pd.factorize(fert_df['Soil Type'])
    crop_factors = pd.factorize(fert_df['Crop Type'])
    label_factors = pd.factorize(fert_df['Fertilizer Name'])

    fert_df['Soil_Code'] = soil_factors[0]
    fert_df['Crop_Code'] = crop_factors[0]
    fert_df['Label_Code'] = label_factors[0]

    # Features and Target
    X_fert = fert_df[['Temparature', 'Humidity ', 'Moisture', 'Soil_Code', 'Crop_Code', 'Nitrogen', 'Potassium', 'Phosphorous']]
    y_fert = fert_df['Label_Code']

    # Train Model
    fert_model = RandomForestClassifier(n_estimators=20, random_state=42)
    fert_model.fit(X_fert, y_fert)
    print("✅ Fertilizer Model trained successfully on Kaggle data.")

    # Save encoders for reference
    crop_encoder = {name.lower() if isinstance(name, str) else name: i for i, name in enumerate(crop_factors[1])}
    soil_encoder = {name.lower() if isinstance(name, str) else name: i for i, name in enumerate(soil_factors[1])}
    label_decoder = {i: name for i, name in enumerate(label_factors[1])}

except Exception as e:
    print(f"⚠️ Failed to load fertilizer model: {e}")
    fert_model = None
    crop_encoder = {}
    soil_encoder = {}
    label_decoder = {}

@app.route('/api/predict-fertilizer-simplified', methods=['POST'])
def predict_fertilizer_simplified():
    try:
        data = request.json
        symptoms_input = data.get('symptoms', 'healthy')
        crop_input = data.get('crop_type', '')
        soil_input = data.get('soil_type', '')

        if fert_model:
            # 1. Best Effort Matching: Convert User Input to Model Codes
            crop_map_key = next((k for k in crop_encoder.keys() if crop_input.lower() in str(k)), list(crop_encoder.keys())[0])
            crop_code = crop_encoder[crop_map_key]
            
            soil_map_key = next((k for k in soil_encoder.keys() if soil_input.lower() in str(k)), list(soil_encoder.keys())[0])
            soil_code = soil_encoder[soil_map_key]
            
            # Heuristic Mapping: Soil Type -> Avg Nutrient Content
            soil_profile = {
                'clay': {'N': 90, 'P': 55, 'K': 40, 'moisture': 70}, 
                'sandy': {'N': 20, 'P': 40, 'K': 50, 'moisture': 30}, 
                'loamy': {'N': 100, 'P': 40, 'K': 190, 'moisture': 50}, 
                'black': {'N': 110, 'P': 50, 'K': 50, 'moisture': 60}, 
                'red': {'N': 50, 'P': 50, 'K': 50, 'moisture': 40} 
            }
            profile = soil_profile.get(soil_input.lower(), soil_profile['loamy'])

            # Modify profile based on symptoms heuristic
            N_val = profile['N']
            P_val = profile['P']
            K_val = profile['K']
            
            if symptoms_input == 'yellow_leaves': N_val = max(10, N_val - 30) # Nitrogen deficiency
            elif symptoms_input == 'stunted': P_val = max(5, P_val - 20) # Phosphorous deficiency
            elif symptoms_input == 'burnt_edges': K_val = max(10, K_val - 30) # Potassium deficiency

            # Default average temp and humidity
            temp_val = 28
            humidity_val = 60
            moist_val = profile['moisture']

            # 2. Predict using ['Temparature', 'Humidity ', 'Moisture', 'Soil_Code', 'Crop_Code', 'Nitrogen', 'Potassium', 'Phosphorous']
            input_features = [[temp_val, humidity_val, moist_val, soil_code, crop_code, N_val, K_val, P_val]]
            pred_code = fert_model.predict(input_features)[0]
            base_recommendation = label_decoder[pred_code]
            
            # 3. Calculate Quantity based on Land Size
            land_size = float(data.get('land_size', 1))
            land_unit = data.get('land_unit', 'acres')
            
            if land_unit == 'hectares':
                land_size = land_size * 2.47
            elif land_unit == 'sq_meter':
                land_size = land_size / 4046.86
                
            dosage_rate = 50 
            if 'Urea' in base_recommendation: dosage_rate = 45
            elif 'DAP' in base_recommendation: dosage_rate = 35
            elif 'MOP' in base_recommendation: dosage_rate = 25
            elif 'NPK' in base_recommendation: dosage_rate = 60
            elif '14-35-14' in base_recommendation: dosage_rate = 55
            elif '10-26-26' in base_recommendation: dosage_rate = 50
            
            total_qty = dosage_rate * land_size
            
            qty_str = f"{total_qty:.1f} kg"
            if total_qty > 1000:
                qty_str = f"{total_qty/1000:.2f} Tonnes"

            recommendation = f"{base_recommendation}<br>"
            recommendation += f"<span style='font-size:1rem; color:#f1c40f; display:block; margin-top:8px;'>Required Quantity: <strong>{qty_str}</strong></span>"
            recommendation += f"<span style='font-size:0.8rem; color:#bdc3c7'>(Calculated for {data.get('land_size')} {land_unit} based on standard dosage)</span>"
            
        else:
            recommendation = "Generic Fertilizer (NPK 19-19-19)"
            if symptoms_input == 'yellow_leaves': recommendation = "Urea (Nitrogen)"
            elif symptoms_input == 'stunted': recommendation = "DAP (Phosphorus)"

        return jsonify({'success': True, 'prediction': recommendation})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
