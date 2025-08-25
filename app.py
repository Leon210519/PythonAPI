from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_babel import Babel, _
import hashlib
import os
import requests
import config
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "change_this_in_production"
app.permanent_session_lifetime = timedelta(minutes=30)

# 🌐 Spracheinstellungen
app.config['LANGUAGES'] = {
    'en': 'English',
    'de': 'Deutsch'
}
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# Lokalisierung festlegen
def get_locale():
    return session.get('lang', 'en')

# Richtiges Initialisieren von Babel (wichtig!)
babel = Babel(app, locale_selector=get_locale)

@app.context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)

# Sprache ändern
@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    if lang_code in app.config['LANGUAGES']:
        session.permanent = True
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('dashboard'))

# ✅ Route
@app.route('/check_lang')
def check_lang():
    return f"Current language: {get_locale()}"

# 🔐 Nutzerverwaltung
USERS_FILE = "userdaten.txt"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    users = {}
    with open(USERS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                username, hashed = parts[0], parts[1]
                users[username] = hashed
    return users

def save_user(username, password):
    with open(USERS_FILE, 'a') as f:
        f.write(f"{username},{hash_password(password)}\n")

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            error = _("Please fill in all fields.")
        else:
            users = load_users()
            if username in users:
                error = _("Username already exists.")
            else:
                save_user(username, password)
                flash(_("Registration successful. Please login."))
                return redirect(url_for('login'))

    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            error = _("All fields are required.")
        else:
            users = load_users()
            hashed = hash_password(password)
            if users.get(username) == hashed:
                session.permanent = True
                session['username'] = username
                flash(_("Logged in successfully."))
                return redirect(url_for('dashboard'))
            else:
                error = _("Invalid username or password.")

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    flash(_("You have been logged out."))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/currency')
def show_currencies():
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))
    return render_template('currency.html')

@app.route('/weather', methods=['GET', 'POST'])
def show_weather():
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))

    weather_data = None
    error = None

    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        if city:
            api_key = config.WEATHER_API_KEY
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang={get_locale()}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('cod') == 200:
                    timezone_offset = data.get('timezone', 0)
                    local_time = datetime.utcfromtimestamp(int(time.time()) + timezone_offset)

                    weather_data = {
                        'city': data['name'],
                        'temp': data['main']['temp'],
                        'description': data['weather'][0]['description'],
                        'icon': data['weather'][0]['icon'],
                        'sunrise': datetime.utcfromtimestamp(data['sys']['sunrise'] + timezone_offset).strftime('%H:%M'),
                        'sunset': datetime.utcfromtimestamp(data['sys']['sunset'] + timezone_offset).strftime('%H:%M'),
                        'local_time': local_time.strftime('%H:%M'),
                        'weather_id': data['weather'][0]['id'],
                    }
                else:
                    error = _("City not found.")
            else:
                error = _("Error fetching data.")
        else:
            error = _("Please enter a city name.")

    return render_template('weather.html', weather=weather_data, error=error)

@app.route('/news')
def show_news():
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))

    lang = get_locale()
    country = 'eg' if lang == 'ar' else 'us'

    url = f"https://newsapi.org/v2/top-headlines?country={country}&apiKey={config.NEWS_API_KEY}&language={lang}"

    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get('articles', [])[:5]
    except Exception as e:
        articles = []
        flash(_("Failed to load news."))

    return render_template('news.html', articles=articles)

if __name__ == '__main__':
    app.run(debug=True)
