import sys
import os
import threading
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

from src.web import app as flask_app  # Import our new web module

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from src.main import bot, TOKEN
    
    # Inject the bot instance into the Flask app
    flask_app.bot = bot
    
    # Get port from environment
    port = int(os.environ.get('PORT', 5000))
    
    # Start Discord Bot in a separate thread
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment.")
    else:
        print(f"Starting Discord Bot...")
        bot_thread = threading.Thread(target=bot.run, args=(TOKEN,), daemon=True)
        bot_thread.start()
    
    # Start Flask on the main thread (blocking)
    # This keeps the process alive and the port open for Render
    print(f"Starting Web Dashboard on port {port}")
    flask_app.run_flask_app()
