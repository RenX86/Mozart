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
    
    # Start Flask in a separate thread
    print("Starting Web Dashboard on http://localhost:5000")
    flask_thread = threading.Thread(target=flask_app.run_flask_app)
    flask_thread.daemon = True # Kills thread when main program exits
    flask_thread.start()
    
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(TOKEN)
