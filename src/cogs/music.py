import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os
import shutil

class Music(commands.Cog):
    def __init__(self, bot, download_dir):
        self.bot = bot
        self.download_dir = download_dir
        self.queue = []
        self.ensure_download_dir()

    def ensure_download_dir(self):
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def play_next(self, voice_client, previous_filename):
        # Cleanup previous file
        try:
            if os.path.exists(previous_filename):
                os.remove(previous_filename)
        except Exception as e:
            print(f"Error deleting file {previous_filename}: {e}")

        if not self.queue:
            return

        next_song = self.queue.pop(0)
        filename = next_song['filename']
        title = next_song['title']
        channel = next_song['channel']

        def after_playing(error):
            if error:
                print(f"Player error: {error}")
            self.play_next(voice_client, filename)

        try:
            # Check if still connected
            if not voice_client.is_connected():
                return
                
            source = discord.FFmpegPCMAudio(filename, executable="ffmpeg")
            voice_client.play(source, after=after_playing)
            
            # Notify channel
            if channel:
                coro = channel.send(f"Now playing **{title}**")
                asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        except Exception as e:
            print(f"Error playing next song: {e}")
            # Try to play the next one if this one failed
            self.play_next(voice_client, filename)

    @app_commands.command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(song_query="search query")
    async def play(self, interaction: discord.Interaction, song_query: str):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.")
            return

        await interaction.response.defer()
        
        if not isinstance(interaction.user, discord.Member):
             await interaction.followup.send("Something went wrong finding your member info.")
             return

        if interaction.user.voice is None or interaction.user.voice.channel is None:
            await interaction.followup.send("You must be in a voice channel to play music.")
            return

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        
        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            if isinstance(voice_client, discord.VoiceClient):
                await voice_client.move_to(voice_channel) 
        
        if not isinstance(voice_client, discord.VoiceClient):
            await interaction.followup.send("Failed to connect to the voice channel properly.")
            return
        
        ydl_options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "nocheckcertificate": True,
            "outtmpl": os.path.join(self.download_dir, "%(id)s.%(ext)s"),
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
        filename = os.path.join(self.download_dir, f"{first_track['id']}.{first_track['ext']}")
        
        # Fallback check
        if not os.path.exists(filename):
            for f in os.listdir(self.download_dir):
                if f.startswith(first_track['id']):
                    filename = os.path.join(self.download_dir, f)
                    break
        
        title = first_track.get("title","Untitled")
        
        if voice_client.is_playing():
            self.queue.append({
                'filename': filename,
                'title': title,
                'channel': interaction.channel
            })
            await interaction.followup.send(f"Added **{title}** to the queue.")
        else:
            def after_playing(error):
                if error:
                    print(f"Player error: {error}")
                self.play_next(voice_client, filename)

            try:
                source = discord.FFmpegPCMAudio(filename, executable="ffmpeg")
                voice_client.play(source, after=after_playing)
                await interaction.followup.send(f"Playing **{title}**")
            except Exception as e:
                await interaction.followup.send(f"An error occurred while trying to play: {e}")

    @app_commands.command(name="pause", description="Pause the current song.")
    async def pause(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.")
            return
        voice_client = interaction.guild.voice_client
        if isinstance(voice_client, discord.VoiceClient) and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Paused the music.")
        else:
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume the paused song.")
    async def resume(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.")
            return
        voice_client = interaction.guild.voice_client
        if isinstance(voice_client, discord.VoiceClient) and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Resumed the music.")
        else:
            await interaction.response.send_message("The music is not paused.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop the music and disconnect.")
    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.")
            return
        voice_client = interaction.guild.voice_client
        if isinstance(voice_client, discord.VoiceClient):
            self.queue.clear()
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            await voice_client.disconnect()
            await interaction.response.send_message("Stopped the music and disconnected.")
        else:
            await interaction.response.send_message("I am not connected to a voice channel.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.")
            return
        voice_client = interaction.guild.voice_client
        if isinstance(voice_client, discord.VoiceClient) and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Skipped the song.")
        else:
            await interaction.response.send_message("Nothing is playing to skip.", ephemeral=True)