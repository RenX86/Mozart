from flask import Flask, render_template, redirect, url_for, flash
import threading
import asyncio
import discord
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey' # Needed for flashing messages

# Global variable to hold the running bot instance
bot = None

def get_music_cog():
    if bot:
        return bot.get_cog('Music')
    return None

def get_active_voice_client():
    if bot and bot.voice_clients:
        return bot.voice_clients[0] # Simplification: control the first active connection
    return None

@app.route('/')
def index():
    music_cog = get_music_cog()
    voice_client = get_active_voice_client()
    
    current_song = music_cog.current_song if music_cog else None
    queue = music_cog.queue if music_cog else []
    
    is_playing = voice_client.is_playing() if voice_client else False
    is_paused = voice_client.is_paused() if voice_client else False
    
    if bot and bot.is_ready():
        return render_template('dashboard.html', 
                               bot_name=bot.user.name,
                               latency=round(bot.latency * 1000),
                               guild_count=len(bot.guilds),
                               current_song=current_song,
                               queue=queue,
                               is_playing=is_playing,
                               is_paused=is_paused,
                               voice_connected=bool(voice_client))
    else:
        return render_template('dashboard.html', 
                               bot_name="Starting...",
                               latency=0,
                               guild_count=0,
                               current_song=None,
                               queue=[],
                               is_playing=False,
                               is_paused=False,
                               voice_connected=False)

@app.route('/pause', methods=['POST'])
def pause():
    vc = get_active_voice_client()
    if vc and vc.is_playing():
        vc.pause()
    return redirect(url_for('index'))

@app.route('/resume', methods=['POST'])
def resume():
    vc = get_active_voice_client()
    if vc and vc.is_paused():
        vc.resume()
    return redirect(url_for('index'))

@app.route('/skip', methods=['POST'])
def skip():
    vc = get_active_voice_client()
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop() # This triggers the after_playing callback which plays next
    return redirect(url_for('index'))

def run_flask_app():
    # Detect environment mode
    # Check for explicit FLASK_DEBUG, FLASK_ENV, or VS Code environment indicators
    is_vscode = os.environ.get('TERM_PROGRAM') == 'vscode' or 'VSCODE_PID' in os.environ
    env_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true' or os.getenv('FLASK_ENV') == 'development'
    
    debug_enabled = env_debug or is_vscode
    
    mode_str = 'DEBUG (VS Code Detected)' if is_vscode else ('DEBUG' if debug_enabled else 'PRODUCTION')
    print(f" * Web Dashboard: Running in {mode_str} mode")
    
    # Run on port 5000
    # use_reloader must be False to avoid spawning a duplicate Discord bot instance
    app.run(host='0.0.0.0', port=5000, debug=debug_enabled, use_reloader=False)