import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from typing import Any, Dict, List, Optional

class Music(commands.Cog):
    def __init__(self, bot, download_dir=None):
        self.bot = bot
        # Dictionary mapping guild_id -> List of song dicts
        self.queues: Dict[int, List[Dict]] = {}
        # Dictionary mapping guild_id -> current song dict
        self.current_songs: Dict[int, Dict] = {}
        
    def get_queue(self, guild_id: int) -> List[Dict]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def get_stream_url(self, webpage_url):
        ydl_opts: Any = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                },
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(webpage_url, download=False)
            return info.get('url'), info.get('title')

    def play_next(self, voice_client):
        guild_id = voice_client.guild.id
        queue = self.get_queue(guild_id)

        if not queue:
            # No more songs for this guild
            if guild_id in self.current_songs:
                del self.current_songs[guild_id]
            return

        next_song = queue.pop(0)
        self.current_songs[guild_id] = next_song
        
        webpage_url = next_song['webpage_url']
        channel = next_song['channel']
        requested_title = next_song['title']

        # Run extraction in executor to avoid blocking
        async def play_process():
            try:
                loop = asyncio.get_running_loop()
                # Re-extract info to get a fresh stream URL
                stream_url, title = await loop.run_in_executor(None, lambda: self.get_stream_url(webpage_url))
                
                if not stream_url:
                    print(f"Could not extract stream URL for {title}")
                    if channel:
                        await channel.send(f"Could not play **{title}** (stream URL missing).")
                    self.play_next(voice_client)
                    return

                # FFmpeg options for stable streaming
                ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }

                def after_playing(error):
                    if error:
                        print(f"Player error: {error}")
                    self.play_next(voice_client)

                # Check connection before playing
                if not voice_client.is_connected():
                    return

                # Explicitly pass arguments to avoid type checker confusion
                source = discord.FFmpegPCMAudio(
                    stream_url,
                    before_options=ffmpeg_options['before_options'],
                    options=ffmpeg_options['options']
                )
                voice_client.play(source, after=after_playing)
                
                if channel:
                    await channel.send(f"Now playing **{title}**")

            except Exception as e:
                print(f"Error in play_next: {e}")
                if channel:
                    await channel.send(f"Error playing **{requested_title}**: {e}")
                self.play_next(voice_client)

        asyncio.run_coroutine_threadsafe(play_process(), self.bot.loop)

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

        # Search options
        ydl_opts: Any = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'default_search': 'ytsearch', # Auto search if not a URL
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                },
            },
        }
        
        def search_song(query):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # extract_info with download=False is fast
                info = ydl.extract_info(query, download=False)
                return info

        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(None, lambda: search_song(song_query))
        except Exception as e:
            await interaction.followup.send(f"Error searching song: {e}")
            return

        # Handle search results (entries) or direct URL
        if 'entries' in info:
            if not info['entries']:
                await interaction.followup.send("No results found.")
                return
            # Take the first result
            info = info['entries'][0]
        
        webpage_url = info.get('webpage_url')
        title = info.get('title', 'Untitled')
        
        queue_item = {
            'webpage_url': webpage_url,
            'title': title,
            'channel': interaction.channel
        }

        # Get the specific queue for this guild
        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)

        if voice_client.is_playing():
            queue.append(queue_item)
            await interaction.followup.send(f"Added **{title}** to the queue.")
        else:
            # Add to queue and play immediately (play_next logic handles popping)
            queue.append(queue_item)
            # Send initial message
            await interaction.followup.send(f"Queued **{title}**. Starting playback...")
            # Trigger playback
            self.play_next(voice_client)

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
            # Clear this guild's queue
            if interaction.guild.id in self.queues:
                self.queues[interaction.guild.id].clear()
            if interaction.guild.id in self.current_songs:
                del self.current_songs[interaction.guild.id]
                
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
