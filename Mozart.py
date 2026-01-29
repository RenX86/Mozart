import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import sqlite3
import yt_dlp
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

profanity = ["fuck you", "nigga"]

def create_user_table():
    connection = sqlite3.connect(f"{BASE_DIR}\\user_warning.db")
    cursor = connection.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "users_per_guild" (
            "user_id" INT,
            "warnings_count" INT,
            "guild_id" INT,
            PRIMARY KEY("user_id","guild_id")
        )
    """)
    connection.commit()
    connection.close()
    
create_user_table()

def increase_and_get_warnings(user_id: int, guil_id: int):
    connection = sqlite3.connect(f"{BASE_DIR}\\user_warning.db")
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT warnings_count
        FROM users_per_guild
        WHERE (user_id = ?) AND (guild_id = ?);               
    """,(user_id,guil_id))
    
    result = cursor.fetchone()
    
    if result == None:
        cursor.execute("""
           INSERT INTO users_per_guild (user_id, warnings_count, guild_id)
           VALUES (?,1,?);            
        """, (user_id, guil_id))
        
        connection.commit()
        connection.close()
        
        return 1 
    
    cursor.execute("""
        UPDATE users_per_guild
        SET warnings_count = ?
        WHERE (user_id = ?) AND (guild_id = ?);      
        """,(result[0] + 1, user_id, guil_id)) 
    
    connection.commit()
    connection.close()
    
    return result [0] + 1



load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user} is online! Synced {len(synced)} commands globally.")

@bot.command()
async def sync(ctx):
    """Syncs slash commands to the current guild for instant updates."""
    try:
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Synced {len(synced)} commands to this guild.")
    except Exception as e:
        await ctx.send(f"Error syncing: {e}")
        # Try global sync if guild sync fails or as a fallback
        try:
             await bot.tree.sync()
             await ctx.send("Synced globally.")
        except Exception as e2:
             await ctx.send(f"Global sync also failed: {e2}")

@bot.tree.command(name="play", description="Play a song or add it to the queue.")
@app_commands.describe(song_query="search query")
async def play (interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()
    
    if interaction.user.voice is None:
        await interaction.followup.send("You must be in a voice channel to play music.")
        return

    voice_channel = interaction.user.voice.channel
    
    voice_client = interaction.guild.voice_client
    
    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel) 
    
    ydl_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "nocheckcertificate": True,
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "source_address": "0.0.0.0",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            },
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.youtube.com/",
        },
    }
    
    query = "ytsearch1: " + song_query
    
    # We need to run the download in the executor to avoid blocking the bot
    def download_song(query, opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=True)
            return info

    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(None, lambda: download_song(query, ydl_options))
    except Exception as e:
        await interaction.followup.send(f"Error downloading song: {e}")
        return

    tracks = results.get("entries",[])
    
    if not tracks:
        await interaction.followup.send("No results found.")
        return 
    
    first_track = tracks[0]
    # Calculate the filename based on the id and extension from the info
    filename = f"downloads/{first_track['id']}.{first_track['ext']}"
    
    # Sometimes yt-dlp converts audio (e.g. to m4a or mp3), so we should check what file actually exists if the above simple guess fails
    # Or rely on 'requested_downloads' if available. 
    # A safer way with 'outtmpl' is usually trusting the ID. 
    # Let's verify file existence or search for it.
    if not os.path.exists(filename):
        # Fallback: check the directory for the file starting with the ID
        for f in os.listdir("downloads"):
            if f.startswith(first_track['id']):
                filename = f"downloads/{f}"
                break
    
    title = first_track.get("title","Untitled")
    
    try:
        # Define a cleanup function
        def after_playing(error):
            if error:
                print(f"Player error: {error}")
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception as e:
                print(f"Error deleting file {filename}: {e}")

        source = discord.FFmpegPCMAudio(filename, executable="ffmpeg")
        voice_client.play(source, after=after_playing)
        await interaction.followup.send(f"Playing **{title}**")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while trying to play: {e}")

@bot.tree.command(name="pause", description="Pause the current song.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("Paused the music.")
    else:
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)

@bot.tree.command(name="resume", description="Resume the paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("Resumed the music.")
    else:
        await interaction.response.send_message("The music is not paused.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop the music and disconnect.")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Stopped the music and disconnected.")
    else:
        await interaction.response.send_message("I am not connected to a voice channel.", ephemeral=True)

@bot.tree.command(name="skip", description="Skip the current song.")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Skipped the song.")
    else:
        await interaction.response.send_message("Nothing is playing to skip.", ephemeral=True)
    
@bot.event
async def on_message(msg):
    if msg.author.id != bot.user.id:
        for term in profanity:
            if term.lower() in msg.content.lower():
                num_warnings = increase_and_get_warnings(msg.author.id, msg.guild.id)
                
                if num_warnings >= 3:
                    await msg.author.ban(reason="Exceeded 3 strikes for using the profanity.")
                    await msg.channel.send(f"{msg.author.mention} has been banned for repeated profanity.")
                    
                else:
                    await msg.channel.send(
                        f"Warning {num_warnings}/3 {msg.author.mention}. If you reach 3 warnings, you will be banned."
                    )
                    await msg.delete()
                break
    await bot.process_commands(msg)
    
    
bot.run(TOKEN)