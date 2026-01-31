import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import random
import os
from typing import Any, Dict, List, Optional

class MusicControls(discord.ui.View):
    def __init__(self, bot, voice_client):
        super().__init__(timeout=None)
        self.bot = bot
        self.voice_client = voice_client
        self.music_cog = bot.get_cog("Music")

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary, emoji="⏸️", row=0)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(self.voice_client, discord.VoiceClient) or not self.voice_client.is_connected():
            await interaction.response.send_message("Bot is not connected correctly.", ephemeral=True)
            return

        if self.voice_client.is_playing():
            self.voice_client.pause()
            button.label = "Resume"
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
        elif self.voice_client.is_paused():
            self.voice_client.resume()
            button.label = "Pause"
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary, emoji="⏭️", row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(self.voice_client, discord.VoiceClient) or not self.voice_client.is_connected():
            await interaction.response.send_message("Bot is not connected correctly.", ephemeral=True)
            return
            
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            await interaction.response.send_message("Skipped.", ephemeral=True)
        else:
             await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️", row=0)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(self.voice_client, discord.VoiceClient) and self.voice_client.guild:
            # Clear queue and loop state
            guild_id = self.voice_client.guild.id
            if self.music_cog:
                await self.music_cog.clear_state(guild_id)
            
            self.voice_client.stop()
            await self.voice_client.disconnect()
        await interaction.response.send_message("Stopped and disconnected.", ephemeral=True)
        self.stop() 

    @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="🔁", row=1)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.music_cog or not interaction.guild:
            return
        
        guild_id = interaction.guild.id
        is_looping = self.music_cog.toggle_loop(guild_id)
        
        if is_looping:
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("Looping enabled 🔁", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("Looping disabled.", ephemeral=True)

    @discord.ui.button(label="Shuffle", style=discord.ButtonStyle.secondary, emoji="🔀", row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.music_cog or not interaction.guild:
            return
        
        guild_id = interaction.guild.id
        guild_id = interaction.guild.id
        await self.music_cog.shuffle_queue(guild_id)
        await interaction.response.send_message("Queue shuffled 🔀", ephemeral=True)

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.music_cog or not interaction.guild:
            return
        
        guild_id = interaction.guild.id
        queue = await self.music_cog.get_queue(guild_id)
        
        if not queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
            
        desc = ""
        for i, song in enumerate(queue[:10], 1):
            desc += f"`{i}.` {song['title']} \n"
        
        if len(queue) > 10:
            desc += f"\n*...and {len(queue) - 10} more*"
            
        embed = discord.Embed(title="Upcoming Songs", description=desc, color=discord.Color.light_grey())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot, db_manager, download_dir=None):
        self.bot = bot
        self.db = db_manager
        # self.queues removed in favor of DB
        self.current_songs: Dict[int, Dict] = {}
        self.loop_states: Dict[int, bool] = {} 
        self.volumes: Dict[int, float] = {} # Store volume per guild (0.0 - 1.0)
        
    async def get_queue(self, guild_id: int) -> List[Dict]:
        # Now async and fetches from DB
        db_queue = await self.db.get_queue(guild_id)
        # We need to resolve channel_id to actual objects for the cog to work seamlessly
        # or update the consumers to handle IDs. Let's resolve here for compatibility.
        resolved_queue = []
        for item in db_queue:
            # item is a dict (from Row)
            item['channel'] = self.bot.get_channel(item['channel_id'])
            resolved_queue.append(item)
        return resolved_queue

    def set_volume(self, guild_id: int, volume: float):
        # Clamp between 0.0 and 1.0
        volume = max(0.0, min(1.0, volume))
        self.volumes[guild_id] = volume
        
        # If currently playing, update immediate source
        voice_client = self.bot.get_guild(guild_id).voice_client if self.bot.get_guild(guild_id) else None
        if voice_client and voice_client.source and isinstance(voice_client.source, discord.PCMVolumeTransformer):
            voice_client.source.volume = volume

    async def remove_song(self, guild_id: int, song_id: int):
        await self.db.remove_from_queue(guild_id, song_id)

    def toggle_loop(self, guild_id: int) -> bool:
        current = self.loop_states.get(guild_id, False)
        self.loop_states[guild_id] = not current
        return not current

    async def shuffle_queue(self, guild_id: int):
        await self.db.shuffle_queue(guild_id)

    async def clear_state(self, guild_id: int):
        await self.db.clear_queue(guild_id)
        if guild_id in self.current_songs:
            del self.current_songs[guild_id]
        if guild_id in self.loop_states:
            self.loop_states[guild_id] = False

    def get_stream_url(self, webpage_url):
        ydl_opts: Any = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web','ios'],
                },
            },
        }
        
        # Apply strict SoundCloud filter if URL identifies as such
        if "soundcloud.com" in webpage_url:
             ydl_opts['format'] = 'bestaudio[protocol=http]'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(webpage_url, download=False)
            return info.get('url'), info.get('title'), info.get('thumbnail'), info.get('duration')

    def play_next(self, voice_client):
        if not voice_client or not voice_client.guild:
            return

        guild_id = voice_client.guild.id
        
        # We need to run this async because we're in a synchronous callback (after=...)
        # or just a synchronous chain.
        async def play_process():
            try:
                # 1. Handle Loop Logic
                if self.loop_states.get(guild_id, False):
                    # If looping, re-add the song that just finished
                    if guild_id in self.current_songs:
                        finished_song = self.current_songs[guild_id]
                        # We need to re-add it to the DB
                        await self.db.add_to_queue(guild_id, finished_song)

                # 2. Get next song from DB (pop)
                next_song = await self.db.pop_from_queue(guild_id)

                if not next_song:
                    # Queue empty
                    if guild_id in self.current_songs:
                         del self.current_songs[guild_id]
                    # Disconnect if desired? For now just stop.
                    # await voice_client.disconnect() 
                    return

                # Resolve Channel Object (DB returned ID)
                channel_id = next_song.get('channel_id')
                channel = self.bot.get_channel(channel_id) if channel_id else None
                
                # Update current song state WITH channel object
                next_song['channel'] = channel
                self.current_songs[guild_id] = next_song
                
                webpage_url = next_song['webpage_url']
                requested_title = next_song['title']
                requester = next_song.get('requester', 'User')

                loop = asyncio.get_running_loop()
                stream_url, title, thumb, dur = await loop.run_in_executor(None, lambda: self.get_stream_url(webpage_url))
                
                if not stream_url:
                    if channel:
                        await channel.send(f"Could not play **{title}**.")
                    # Recursively call play_next (unsafe if infinite loop of failures?)
                    # Better to just schedule it again
                    self.play_next(voice_client)
                    return

                def after_playing(error):
                    if error:
                        print(f"Player error: {error}")
                    self.play_next(voice_client)

                if not voice_client.is_connected():
                    return

                if not voice_client.is_connected():
                    return

                # Create Audio Source
                original_source = discord.FFmpegPCMAudio(
                    stream_url,
                    before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -protocol_whitelist file,http,https,tcp,tls',
                    options='-vn'
                )
                
                # Wrap in Volume Transformer
                # We need to store the volume state somewhere if we want it to persist between songs
                # For now, let's default to self.volumes.get(guild_id, 0.5)
                current_vol = self.volumes.get(guild_id, 0.5) # Default 50%
                source = discord.PCMVolumeTransformer(original_source, volume=current_vol)
                
                voice_client.play(source, after=after_playing)
                
                if channel:
                    embed = discord.Embed(
                        title="Now Playing", 
                        description=f"[{title}]({webpage_url})",
                        color=discord.Color.from_rgb(0, 229, 255)
                    )
                    if thumb:
                        embed.set_thumbnail(url=thumb)
                    
                    duration_str = "Unknown"
                    if dur:
                        minutes = int(dur // 60)
                        seconds = int(dur % 60)
                        duration_str = f"{minutes}:{seconds:02d}"

                    embed.add_field(name="Duration", value=duration_str, inline=True)
                    embed.add_field(name="Requested By", value=requester, inline=True)
                    
                    # Peek at next song (without popping)
                    queue = await self.db.get_queue(guild_id)
                    if queue:
                        next_up_title = queue[0]['title']
                        embed.add_field(name="Next Up", value=next_up_title, inline=False)
                    
                    view = MusicControls(self.bot, voice_client)
                    # Update loop button state
                    if self.loop_states.get(guild_id, False):
                         for child in view.children:
                             if isinstance(child, discord.ui.Button) and child.label == "Loop":
                                 child.style = discord.ButtonStyle.success

                    await channel.send(embed=embed, view=view)

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error in play_next: {e} | Type: {type(e)}")
                if channel: # channel might be None if resolved failed
                    await channel.send(f"Error playing song: {e}")
                self.play_next(voice_client)

        asyncio.run_coroutine_threadsafe(play_process(), self.bot.loop)

    @app_commands.command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(song_query="search query")
    async def play(self, interaction: discord.Interaction, song_query: str):
        if not interaction.guild:
            await interaction.response.send_message("Servers only.")
            return

        await interaction.response.defer() 
        
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Join a voice channel first.")
            return

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        
        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            if isinstance(voice_client, discord.VoiceClient):
                await voice_client.move_to(voice_channel) 
        
        ydl_opts: Any = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'default_search': 'ytsearch',
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
        }
        
        def search_song(query):
            # Attempt 1: Default (YouTube)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    return info, "YouTube"
            except Exception as e:
                print(f"YouTube search failed: {e}")
                # Attempt 2: SoundCloud (Force progressive HTTP MP3 to avoid HLS issues entirely)
                sc_opts = ydl_opts.copy()
                sc_opts['default_search'] = 'scsearch'
                # Strictly prefer HTTP protocol (progressive download)
                sc_opts['format'] = 'bestaudio[protocol=http]'
                with yt_dlp.YoutubeDL(sc_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    print(f"SoundCloud Fallback: Selected URL: {info.get('url')} | Ext: {info.get('ext')}")
                    return info, "SoundCloud"

        loop = asyncio.get_running_loop()
        try:
            info, source_platform = await loop.run_in_executor(None, lambda: search_song(song_query))
        except Exception as e:
            await interaction.followup.send(f"Error finding song on YouTube and SoundCloud: {e}")
            return

        if 'entries' in info:
            if not info['entries']:
                await interaction.followup.send("No results.")
                return
            info = info['entries'][0]
        
        webpage_url = info.get('webpage_url')
        title = info.get('title', 'Untitled')
        thumbnail = info.get('thumbnail')
        duration = info.get('duration')
        
        queue_item = {
            'webpage_url': webpage_url,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'channel': interaction.channel,
            'requester': interaction.user.display_name
        }

        guild_id = interaction.guild.id
        guild_id = interaction.guild.id
        # Use DB Count or Fetch
        # We can just add it blindly first
        await self.db.add_to_queue(guild_id, queue_item)
        
        # Determine if we are already playing to decide response
        if isinstance(voice_client, discord.VoiceClient) and voice_client.is_playing():
            # Fetch queue for position info
            queue = await self.db.get_queue(guild_id)
            
            embed = discord.Embed(
                title="Added to Queue", 
                description=f"[{title}]({webpage_url})",
                color=discord.Color.gold()
            )
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            
            duration_str = "Unknown"
            if duration:
                 m = int(duration // 60)
                 s = int(duration % 60)
                 duration_str = f"{m}:{s:02d}"

            embed.add_field(name="Duration", value=duration_str, inline=True)
            
            footer_text = f"Position: {len(queue)}"
            if source_platform == "SoundCloud":
                 footer_text += " | Source: SoundCloud ☁️"
            embed.set_footer(text=footer_text)
            
            await interaction.followup.send(embed=embed)
        else:
            msg = f"Loading **{title}**..."
            if source_platform == "SoundCloud":
                msg += " (via SoundCloud ☁️)"
            await interaction.followup.send(msg)
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
            await self.clear_state(interaction.guild.id)

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