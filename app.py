"""Flask application providing a simple multilingual dashboard.

The app demonstrates user authentication, language switching via Flask-Babel and
integration with a few public APIs (weather, news and currency exchange). All
configuration values are loaded from :mod:`config` or environment variables so
that deployments can be customised without code changes.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_babel import Babel, _
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import requests
import config
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# Secret key and session lifetime are configurable through environment
# variables to ease deployment in different environments.
app.secret_key = os.getenv("SECRET_KEY", "change_this_in_production")
app.permanent_session_lifetime = timedelta(
    minutes=int(os.getenv("SESSION_LIFETIME_MINUTES", 30))
)

# 🌐 Language configuration --------------------------------------------------------
app.config['LANGUAGES'] = {
    'en': 'English',
    'de': 'Deutsch'
}
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'


def get_locale():
    """Return the currently active language code."""
    return session.get('lang', 'en')


# Initialise Babel with the locale selector.
babel = Babel(app, locale_selector=get_locale)


@app.context_processor
def inject_get_locale():
    """Make ``get_locale`` available inside templates."""
    return dict(get_locale=get_locale)


@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    """Persist the selected ``lang_code`` in the session."""
    if lang_code in app.config['LANGUAGES']:
        session.permanent = True
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/check_lang')
def check_lang():
    """Simple diagnostics route showing the current language."""
    return f"Current language: {get_locale()}"


# 🔐 User management ---------------------------------------------------------------
USERS_DB = os.getenv("USERS_DB", "users.db")


def init_db() -> None:
    """Ensure the user database exists."""
    conn = sqlite3.connect(USERS_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )"""
    )
    conn.commit()
    conn.close()


init_db()


def load_users() -> dict:
    """Return all users from the database as a ``username: hash`` mapping."""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password_hash FROM users")
    rows = cursor.fetchall()
    conn.close()
    return {username: pw_hash for username, pw_hash in rows}


def save_user(username: str, password: str) -> None:
    """Insert a new user into the database."""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password)),
    )
    conn.commit()
    conn.close()


@app.route('/')
def home():
    """Redirect to the login page."""
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
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
    """Authenticate the user and start a session."""
    error = ""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            error = _("All fields are required.")
        else:
            users = load_users()
            hashed = users.get(username)
            if hashed and check_password_hash(hashed, password):
                session.permanent = True
                session['username'] = username
                flash(_("Logged in successfully."))
                return redirect(url_for('dashboard'))
            else:
                error = _("Invalid username or password.")

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Log the current user out and clear the session."""
    session.clear()
    flash(_("You have been logged out."))
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    """Display the main dashboard if the user is logged in."""
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])


@app.route('/currency')
def show_currencies():
    """Render the currency conversion tool."""
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))
    return render_template('currency.html')


@app.route('/weather', methods=['GET', 'POST'])
def show_weather():
    """Display weather information for a requested city."""
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))

    weather_data = None
    error = None

    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        if city:
            api_key = config.WEATHER_API_KEY
            url = (
                f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang={get_locale()}"
            )
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('cod') == 200:
                    timezone_offset = data.get('timezone', 0)
                    local_time = datetime.utcfromtimestamp(
                        int(time.time()) + timezone_offset
                    )

                    weather_data = {
                        'city': data['name'],
                        'temp': data['main']['temp'],
                        'description': data['weather'][0]['description'],
                        'icon': data['weather'][0]['icon'],
                        'sunrise': datetime.utcfromtimestamp(
                            data['sys']['sunrise'] + timezone_offset
                        ).strftime('%H:%M'),
                        'sunset': datetime.utcfromtimestamp(
                            data['sys']['sunset'] + timezone_offset
                        ).strftime('%H:%M'),
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
    """Fetch and display the latest news headlines."""
    if 'username' not in session:
        flash(_("Please login first."))
        return redirect(url_for('login'))

    lang = get_locale()
    # Map language codes to the NewsAPI country parameter.
    country_map = {'en': 'us', 'de': 'de'}
    country = country_map.get(lang, 'us')

    url = (
        f"https://newsapi.org/v2/top-headlines?country={country}&apiKey={config.NEWS_API_KEY}&language={lang}"
    )

    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get('articles', [])[:5]
    except Exception:
        articles = []
        flash(_("Failed to load news."))

    return render_template('news.html', articles=articles)


if __name__ == '__main__':
    # Enable debug mode only when FLASK_DEBUG is set to "1".
    # This should be used for development environments only.
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')
