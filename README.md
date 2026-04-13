# 🌿 SmartFarming AI

A premium, AI-powered web application that helps farmers make data-driven decisions. Built with Flask and scikit-learn, the platform offers intelligent crop recommendations, fertilizer advice, plant disease detection, and an interactive crop growth simulator — all wrapped in a modern glassmorphism UI with bilingual (English/Tamil) support.

---

## ✨ Features

### 🌾 Crop Recommendation
- Select soil type, season, and water availability to get the **top 3 recommended crops**.
- Uses a **RandomForest classifier** trained on a 630K+ sample dataset.
- Supports **real-time location-based weather data** via browser geolocation and the OpenWeatherMap API, with seasonal fallback defaults.

### 🧪 Fertilizer Advisor
- Provides tailored fertilizer recommendations based on **crop type, soil type, and observed symptoms**.
- Calculates the **required fertilizer quantity** based on user-specified land size (acres, hectares, or sq. meters).
- Data-driven lookup from a curated `Fertilizer_Recommendation.csv` dataset.

### 🦠 Disease Detection
- Upload a leaf image and get an **instant disease diagnosis** powered by a **RandomForest model** trained on 330K+ samples.
- Extracts **14 image features** (color statistics, pixel ratios, texture, brightness, saturation) for prediction.
- Includes **severity assessment** (Mild / Moderate / Severe) and **treatment recommendations**.
- Built-in **leaf validation** gate — rejects non-leaf images gracefully.

### 📊 Crop Growth Simulator
- Interactive, canvas-based **plant growth simulation** with adjustable weather, soil, and irrigation parameters.
- Visualize how different conditions affect crop development over time.
- Fully responsive design optimized for both mobile and desktop.

### 🔐 User Authentication
- Secure registration & login with **bcrypt password hashing**.
- **Email verification** with 6-digit OTP codes (10-minute expiry).
- Session management via Flask-Login with "Remember Me" support.

### 🌐 Bilingual Support (English / Tamil)
- Floating language toggle button to switch the entire UI between **English and Tamil**.
- Client-side translation engine that updates all static text and dynamic prediction results.
- Language preference **persisted across sessions** via localStorage.

---

## 🛠️ Tech Stack

| Layer       | Technology                                       |
| ----------- | ------------------------------------------------ |
| Backend     | Python 3, Flask, Flask-SQLAlchemy, Flask-Login    |
| ML / AI     | scikit-learn (RandomForest), Pandas, NumPy, Pillow |
| Database    | SQLite (via SQLAlchemy)                           |
| Frontend    | HTML5, Vanilla CSS (glassmorphism), JavaScript    |
| Auth        | Flask-Bcrypt, OTP email verification              |

---

## 📁 Project Structure

```
smart_farming/
├── app.py                        # Flask application & API routes
├── requirements.txt              # Python dependencies
├── README.md
├── data/
│   ├── Crop_Recommendation.csv   # Training data for crop model
│   ├── Disease_Detection.csv     # Training data for disease model
│   └── Fertilizer_Recommendation.csv
├── instance/
│   └── users.db                  # SQLite user database (auto-created)
├── static/
│   ├── css/
│   │   └── style.css             # Global styles & design system
│   ├── js/
│   │   └── main.js               # Client-side logic & translations
│   └── uploads/                  # Uploaded leaf images
└── templates/
    ├── base.html                 # Base layout template
    ├── index.html                # Landing page with feature cards
    ├── login.html                # Login page
    ├── register.html             # Registration page
    ├── verify_email.html         # Email OTP verification
    ├── crop.html                 # Crop recommendation interface
    ├── fertilizer.html           # Fertilizer advisor interface
    ├── disease.html              # Disease detection (image upload)
    └── simulation.html           # Interactive crop growth simulator
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** installed on your system.

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/santhoshjks/smart_farming.git
   cd smart_farming
   ```

2. **Create a virtual environment** *(recommended)*
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   Navigate to `http://127.0.0.1:5000`

> **Note:** The ML models are trained automatically on startup from the CSV files in the `data/` directory — no pre-trained model files are needed.

---

## 📡 API Endpoints

| Method | Endpoint                           | Description                          | Auth Required |
| ------ | ---------------------------------- | ------------------------------------ | ------------- |
| POST   | `/api/predict-crop-simplified`     | Get top 3 crop recommendations       | No            |
| POST   | `/api/predict-fertilizer-simplified` | Get fertilizer advice & quantity   | No            |
| POST   | `/api/predict-disease`             | Upload leaf image for diagnosis       | No            |
| POST   | `/register`                        | Create a new user account             | No            |
| POST   | `/login`                           | Authenticate & start session          | No            |
| GET    | `/logout`                          | End the current session               | Yes           |
| POST   | `/verify-email`                    | Verify email with OTP code            | No            |
| POST   | `/resend-code`                     | Resend verification OTP               | No            |

---

## 📦 Dependencies

```
Flask
gunicorn
Flask-SQLAlchemy
Flask-Login
Flask-Bcrypt
Pillow
numpy
pandas
scikit-learn
```

---

## 🔒 Security Notes

- Change the `SECRET_KEY` in `app.py` before deploying to production.
- The SQLite database is auto-created in the `instance/` directory.
- File uploads are limited to **16 MB** and saved securely via `werkzeug.utils.secure_filename`.

---

## 📄 License

This project is open source. See the repository for license details.

---

## 📬 Contact

- **GitHub:** [santhoshjks/smart_farming](https://github.com/santhoshjks/smart_farming)
- **Email:** jkssanthosh38@gmail.com
- **Location:** Chennai, Tamil Nadu, India
