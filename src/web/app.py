from flask import Flask, render_template, redirect, url_for, flash, session, request, abort
import threading
import asyncio
import discord
import os
import requests

app = Flask(__name__)

# Security Configuration
# In production, failure to have a secret key is a critical error.
app.secret_key = os.getenv('FLASK_SECRET_KEY')
if not app.secret_key:
    if os.getenv('FLASK_DEBUG', 'false').lower() == 'true':
        app.secret_key = 'dev-fallback-key'
        print("WARNING: Using fallback FLASK_SECRET_KEY. Do not do this in production!")
    else:
        # We can't safely run without a secret key in prod
        # But raising generic error might crash potential build steps if envs aren't loaded yet.
        # We'll set a dummy one but print a HUGE warning.
        print("CRITICAL WARNING: FLASK_SECRET_KEY not set! Session security is compromised.")
        app.secret_key = 'unsafe-default-key'

# OAuth2 Configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
discord_api_endpoint = "https://discord.com/api/v10"

# Auto-detect or use env var
def get_redirect_uri():
    if os.getenv('OAUTH2_REDIRECT_URI'):
        return os.getenv('OAUTH2_REDIRECT_URI')
    # Fallback for local dev
    return 'http://localhost:5000/callback' 

# Global variable to hold the running bot instance
bot = None

def get_music_cog():
    if bot:
        return bot.get_cog('Music')
    return None

def get_active_voice_client():
    # Improved logic: Return the first active voice client found
    if bot and bot.voice_clients:
        return bot.voice_clients[0] 
    return None

# Auth Decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to access this feature.", "warning")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_dashboard_context():
    music_cog = get_music_cog()
    voice_client = get_active_voice_client()
    
    current_song = None
    queue = []
    
    # If we have an active connection, fetch data specific to THAT guild
    if voice_client and music_cog:
        guild_id = voice_client.guild.id
        # Safely access the dictionary using .get()
        current_song = music_cog.current_songs.get(guild_id)
        
        # Queue is now in DB (async), so we must fetch it safely from the bot's loop
        try:
            if bot and bot.loop:
                 future = asyncio.run_coroutine_threadsafe(music_cog.get_queue(guild_id), bot.loop)
                 queue = future.result(timeout=2) # 2s timeout should be plenty for local DB
            else:
                 queue = []
        except Exception as e:
            print(f"Failed to fetch queue: {e}")
            queue = []
    
    is_playing = voice_client.is_playing() if voice_client else False
    is_paused = voice_client.is_paused() if voice_client else False
    
    # Pass user session info
    user_info = None
    if 'user_id' in session:
        user_info = {
            'username': session.get('username'),
            'avatar': session.get('avatar'),
            'id': session.get('user_id')
        }

    if bot and bot.is_ready():
        return {
            'bot_name': bot.user.name,
            'latency': round(bot.latency * 1000),
            'guild_count': len(bot.guilds),
            'current_song': current_song,
            'queue': queue,
            'is_playing': is_playing,
            'is_paused': is_paused,
            'voice_connected': bool(voice_client),
            'user': user_info,
            # Enhancements
            'volume': int(music_cog.volumes.get(voice_client.guild.id, 0.5) * 100) if voice_client and music_cog else 50,
            'loop_state': music_cog.loop_states.get(voice_client.guild.id, False) if voice_client and music_cog else False
        }
    else:
         return {
            'bot_name': "Starting...",
            'latency': 0,
            'guild_count': 0,
            'current_song': None,
            'queue': [],
            'is_playing': False,
            'is_paused': False,
            'voice_connected': False,
            'user': user_info,
            'volume': 50,
            'loop_state': False
        }

@app.route('/')
def index():
    context = get_dashboard_context()
    return render_template('dashboard.html', **context)

@app.route('/dashboard/partial')
def dashboard_partial():
    context = get_dashboard_context()
    return render_template('partials/dashboard_body.html', **context)

# --- Control APIs ---

@app.route('/api/volume', methods=['POST'])
@login_required
def set_volume():
    try:
        data = request.json
        if not data or 'volume' not in data:
            return "Missing volume", 400
            
        vol_percent = int(data['volume'])
        music_cog = get_music_cog()
        vc = get_active_voice_client()
        
        if music_cog and vc:
            music_cog.set_volume(vc.guild.id, vol_percent / 100.0)
            return "Volume set", 200
        return "Bot not active", 400
    except Exception as e:
        print(f"Volume API Error: {e}")
        return str(e), 500

@app.route('/api/loop', methods=['POST'])
@login_required
def toggle_loop():
    music_cog = get_music_cog()
    vc = get_active_voice_client()
    if music_cog and vc:
        new_state = music_cog.toggle_loop(vc.guild.id)
        return str(new_state).lower(), 200
    return "Bot not active", 400

@app.route('/api/shuffle', methods=['POST'])
@login_required
def shuffle_queue():
    music_cog = get_music_cog()
    vc = get_active_voice_client()
    if music_cog and vc and bot and bot.loop:
        asyncio.run_coroutine_threadsafe(music_cog.shuffle_queue(vc.guild.id), bot.loop)
        return "Shuffled", 200
    return "Bot or event loop not active", 400

@app.route('/api/clear', methods=['POST'])
@login_required
def clear_queue():
    music_cog = get_music_cog()
    vc = get_active_voice_client()
    if music_cog and vc and bot and bot.loop:
        asyncio.run_coroutine_threadsafe(music_cog.clear_state(vc.guild.id), bot.loop)
        # Note: clear_state also stops the player usually, but let's check config
        # Actually in music.py clear_state clears DB and current_song dict
        return "Cleared", 200
    return "Bot or event loop not active", 400

@app.route('/api/remove/<int:song_id>', methods=['POST'])
@login_required
def remove_song(song_id):
    music_cog = get_music_cog()
    vc = get_active_voice_client()
    if music_cog and vc and bot and bot.loop:
        asyncio.run_coroutine_threadsafe(music_cog.remove_song(vc.guild.id, song_id), bot.loop)
        return "Removed", 200
    return "Bot or event loop not active", 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        client_secret = request.form.get('client_secret')
        
        if not client_id or not client_secret:
            flash("Both Client ID and Secret are required.", "danger")
            return redirect(url_for('login'))
        
        # Store in session for the callback
        session['discord_client_id'] = client_id
        session['discord_client_secret'] = client_secret
        
        redirect_uri = get_redirect_uri()
        scope = "identify"
        discord_login_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={client_id}"
            f"&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
        )
        return redirect(discord_login_url)

    # GET request - show form
    return render_template('login.html')

@app.route('/callback')
def callback():
    # Retrieve credentials from session
    client_id = session.get('discord_client_id')
    client_secret = session.get('discord_client_secret')

    if not client_id or not client_secret:
        flash("Session expired or missing credentials. Please try again.", "danger")
        return redirect(url_for('login'))
        
    code = request.args.get('code')
    if not code:
        return "No code provided", 400

    redirect_uri = get_redirect_uri()
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'scope': 'identify'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        r = requests.post(f'{discord_api_endpoint}/oauth2/token', data=data, headers=headers)
        r.raise_for_status()
        tokens = r.json()
        access_token = tokens['access_token']
        
        # Get User Info
        headers = {
            'Authorization': f"Bearer {access_token}"
        }
        r_user = requests.get(f'{discord_api_endpoint}/users/@me', headers=headers)
        r_user.raise_for_status()
        user_data = r_user.json()
        
        # Save to session (keep the credentials for potential token refresh if we implemented that, 
        # but for now just the user info is enough for the dashboard)
        session['user_id'] = user_data['id']
        session['username'] = user_data['username']
        session['avatar'] = user_data['avatar']
        
        # Clear secrets from session if we want to be extra paranoid, 
        # but keep them if we needed to refresh tokens. 
        # For this simple implementation, we can clean them up or leave them.
        # Leaving them allows re-auth without re-typing if the token expires quickly 
        # (though we aren't handling refresh logic here).
        
        flash(f"Welcome, {user_data['username']}!", 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"OAuth Error: {e}")
        return f"Authentication failed: {e}", 500

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", 'info')
    return redirect(url_for('index'))

@app.route('/pause', methods=['POST'])
@login_required
def pause():
    vc = get_active_voice_client()
    if vc and vc.is_playing():
        vc.pause()
    return redirect(url_for('index'))

@app.route('/resume', methods=['POST'])
@login_required
def resume():
    vc = get_active_voice_client()
    if vc and vc.is_paused():
        vc.resume()
    return redirect(url_for('index'))

@app.route('/skip', methods=['POST'])
@login_required
def skip():
    vc = get_active_voice_client()
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop() # This triggers the after_playing callback which plays next
    return redirect(url_for('index'))

@app.route('/health')

def health_check():

    return {"status": "healthy", "bot_ready": bot.is_ready() if bot else False}, 200



def run_flask_app():

    # Detect environment mode

    env_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true' or os.getenv('FLASK_ENV') == 'development'

    

    port = int(os.environ.get('PORT', 5000))



    if env_debug:

        print(f" * Web Dashboard: Running in DEBUG mode on port {port}")

        # use_reloader must be False to avoid spawning a duplicate Discord bot instance

        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)

    else:

        print(f" * Web Dashboard: Running in PRODUCTION mode (Waitress) on port {port}")

        from waitress import serve

        serve(app, host='0.0.0.0', port=port, threads=4)
