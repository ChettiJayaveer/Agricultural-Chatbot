import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# --- IMPORT YOUR RAG LOGIC ---
from chatbot_logic import get_response 

load_dotenv()

app = Flask(__name__)
# Secret key for session security
app.secret_key = os.getenv("FLASK_SECRET_KEY", "agri_secret_786")

# API Keys and Resource IDs
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
DATAGOV_API_KEY = os.getenv("DATAGOV_API_KEY")
MANDI_RESOURCE_ID = "9ef2731d-98d9-4278-8537-01b0791f074a" 

# Database and Upload Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- DATABASE MODELS ---
class User(db.Model):
    """Stores user info using the single 'name' field from signup."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_pic = db.Column(db.String(255), default='default_user.png')

class ChatHistory(db.Model):
    """Tracks conversations for personalized assistance."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def home():
    """Renders the landing page with justified matter."""
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles registration and profile picture uploads."""
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        file = request.files.get('profile_pic')
        filename = 'default_user.png'
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=hashed_pw,
            profile_pic=filename
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "Registration Error: This email is already registered."
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticates user and sets session variables."""
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_pic'] = user.profile_pic
            return redirect(url_for('index'))
        return "Invalid email or password."
    return render_template('login.html')

@app.route('/index')
def index():
    """Protected chat dashboard route."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/get_dashboard')
def get_dashboard():
    """Fetches real-time 5-hour forecast and mandi prices based on city input."""
    city = request.args.get('city', 'Kakinada').strip() 
    forecast_data = []
    
    # 1. Weather Fetch (Hourly/3-hour blocks)
    try:
        # cnt=5 ensures we get the next 5 intervals (~15 hours)
        w_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&cnt=5"
        w_res = requests.get(w_url, timeout=5).json()
        if str(w_res.get("cod")) == "200":
            for item in w_res['list']:
                forecast_data.append({
                    "time": item['dt_txt'].split(" ")[1][:5], # Extract HH:MM
                    "temp": round(item['main']['temp']),
                    "desc": item['weather'][0]['main']
                })
    except: 
        forecast_data = [{"time": "N/A", "temp": "--", "desc": "Offline"}]

    # 2. Mandi Price Fetch (Data.gov.in)
    mandi_data = []
    try:
        m_url = f"https://api.data.gov.in/resource/{MANDI_RESOURCE_ID}?api-key={DATAGOV_API_KEY}&format=json&filters[market]={city}"
        m_res = requests.get(m_url, timeout=5).json()
        mandi_data = m_res.get('records', [])
    except: pass

    return jsonify({"city": city, "forecast": forecast_data, "prices": mandi_data})

@app.route('/ask', methods=['POST'])
def ask():
    """Interfaces with the AI RAG engine and saves history."""
    if 'user_id' not in session:
        return jsonify({"answer": "Please login to chat."})
    
    user_query = request.form.get('messageText', '')
    
    # Process query through Gemini 2.5 Flash logic
    bot_response = get_response(user_query)

    # Save to history for session persistence
    new_chat = ChatHistory(
        user_id=session['user_id'], 
        user_message=user_query, 
        bot_response=bot_response
    )
    db.session.add(new_chat)
    db.session.commit()
    
    return jsonify({"answer": bot_response})

@app.route('/logout')
def logout():
    """Clears all session data and redirects to Home."""
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)