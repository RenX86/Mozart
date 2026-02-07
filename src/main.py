import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import discord.opus
from cogs.music import Music
from cogs.moderation import Moderation
from utils.database import DatabaseManager
import shutil

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "data", "downloads")
DB_PATH = os.path.join(BASE_DIR, "data", "user_warning.db")

# Ensure critical directories exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# One-time cleanup on start (optional)
def cleanup_downloads():
    if os.path.exists(DOWNLOAD_DIR):
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Explicitly load Opus on Linux (Alpine)
if not discord.opus.is_loaded():
    # Common paths for Alpine/Linux
    opus_paths = ['/usr/lib/libopus.so.0', 'libopus.so.0', 'libopus.so']
    for path in opus_paths:
        try:
            discord.opus.load_opus(path)
            print(f"Opus loaded from {path}")
            break
        except Exception:
            pass
    
    if not discord.opus.is_loaded():
        print("Warning: Could not load Opus library. Voice features may fail.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize Utils
db_manager = DatabaseManager(DB_PATH)

@bot.event
async def on_ready():
    cleanup_downloads()
    
    # Add Cogs
    if not bot.get_cog('Music'):
        await bot.add_cog(Music(bot, db_manager, DOWNLOAD_DIR))
    if not bot.get_cog('Moderation'):
        await bot.add_cog(Moderation(bot, db_manager))
    
    print(f"{bot.user} is online! (Commands not synced automatically)")

@bot.command()
async def sync(ctx):
    """Syncs slash commands to the current guild for instant updates."""
    try:
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Synced {len(synced)} commands to this guild.")
    except Exception as e:
        await ctx.send(f"Error syncing: {e}")
        try:
             await bot.tree.sync()
             await ctx.send("Synced globally.")
        except Exception as e2:
             await ctx.send(f"Global sync also failed: {e2}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(TOKEN)
