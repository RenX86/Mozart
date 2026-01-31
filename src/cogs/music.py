import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import random
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

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
                self.music_cog.clear_state(guild_id)
            
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
        self.music_cog.shuffle_queue(guild_id)
        await interaction.response.send_message("Queue shuffled 🔀", ephemeral=True)

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.music_cog or not interaction.guild:
            return
        
        guild_id = interaction.guild.id
        queue = self.music_cog.get_queue(guild_id)
        
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
    def __init__(self, bot, download_dir=None):
        self.bot = bot
        self.queues: Dict[int, List[Dict]] = {}
        self.current_songs: Dict[int, Dict] = {}
        self.loop_states: Dict[int, bool] = {}
        
        # Cookie file path for YouTube authentication
        self.cookie_file = os.getenv('YOUTUBE_COOKIE_FILE', 'youtube_cookies.txt')
        
        # Platform search order (YouTube first, then fallbacks)
        self.platforms = [
            {'name': 'YouTube', 'search': 'ytsearch', 'enabled': True},
            {'name': 'SoundCloud', 'search': 'scsearch', 'enabled': True},
            {'name': 'JioSaavn', 'search': 'jssearch', 'enabled': True},
            {'name': 'Bandcamp', 'search': 'bcsearch', 'enabled': True},
        ]
        
    def get_queue(self, guild_id: int) -> List[Dict]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def toggle_loop(self, guild_id: int) -> bool:
        current = self.loop_states.get(guild_id, False)
        self.loop_states[guild_id] = not current
        return not current

    def shuffle_queue(self, guild_id: int):
        if guild_id in self.queues:
            random.shuffle(self.queues[guild_id])

    def clear_state(self, guild_id: int):
        if guild_id in self.queues:
            self.queues[guild_id].clear()
        if guild_id in self.current_songs:
            del self.current_songs[guild_id]
        if guild_id in self.loop_states:
            self.loop_states[guild_id] = False
    
    def get_base_ydl_opts(self, use_cookies=True) -> Dict[str, Any]:
        """Get base yt-dlp options with optional cookie support"""
        opts: Dict[str, Any] = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web', 'tv_embedded'],
                    'skip': ['hls', 'dash'],
                },
            },
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
        }
        
        # Add cookie file if it exists and use_cookies is True
        if use_cookies and os.path.exists(self.cookie_file):
            opts['cookiefile'] = self.cookie_file
            print(f"Using cookie file: {self.cookie_file}")
        
        return opts

    def get_stream_url(self, webpage_url):
        """Extract stream URL with cookie support"""
        ydl_opts = self.get_base_ydl_opts(use_cookies=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(webpage_url, download=False)
            return info.get('url'), info.get('title'), info.get('thumbnail'), info.get('duration')
    
    def search_multi_platform(self, query: str) -> Optional[Dict[str, Any]]:
        """Search across multiple platforms with fallback logic"""
        # Check if it's a direct URL
        if query.startswith('http://') or query.startswith('https://'):
            ydl_opts = self.get_base_ydl_opts(use_cookies=True)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if 'entries' in info:
                        info = info['entries'][0] if info['entries'] else None
                    return info
            except Exception as e:
                print(f"Error extracting URL {query}: {e}")
                return None
        
        # Try each platform in order
        for platform in self.platforms:
            if not platform['enabled']:
                continue
                
            print(f"Trying {platform['name']} for query: {query}")
            
            ydl_opts = self.get_base_ydl_opts(use_cookies=(platform['name'] == 'YouTube'))
            ydl_opts['default_search'] = platform['search']
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    
                    if 'entries' in info and info['entries']:
                        result = info['entries'][0]
                        print(f"✓ Found on {platform['name']}: {result.get('title')}")
                        return result
                    elif info:
                        print(f"✓ Found on {platform['name']}: {info.get('title')}")
                        return info
                        
            except Exception as e:
                print(f"✗ {platform['name']} failed: {str(e)[:100]}")
                continue
        
        print(f"Failed to find '{query}' on any platform")
        return None

    def play_next(self, voice_client):
        if not voice_client or not voice_client.guild:
            return

        guild_id = voice_client.guild.id
        
        if self.loop_states.get(guild_id, False):
            if guild_id in self.current_songs:
                finished_song = self.current_songs[guild_id]
                self.get_queue(guild_id).append(finished_song)

        queue = self.get_queue(guild_id)

        if not queue:
            if guild_id in self.current_songs:
                del self.current_songs[guild_id]
            return

        next_song = queue.pop(0)
        self.current_songs[guild_id] = next_song
        
        webpage_url = next_song['webpage_url']
        channel = next_song['channel']
        requested_title = next_song['title']
        requester = next_song.get('requester', 'User')

        async def play_process():
            try:
                loop = asyncio.get_running_loop()
                stream_url, title, thumb, dur = await loop.run_in_executor(None, lambda: self.get_stream_url(webpage_url))
                
                if not stream_url:
                    if channel:
                        await channel.send(f"Could not play **{title}**.")
                    self.play_next(voice_client)
                    return

                ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }

                def after_playing(error):
                    if error:
                        print(f"Player error: {error}")
                    self.play_next(voice_client)

                if not voice_client.is_connected():
                    return

                source = discord.FFmpegPCMAudio(
                    stream_url,
                    before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    options='-vn'
                )
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
                        minutes = dur // 60
                        seconds = dur % 60
                        duration_str = f"{minutes}:{seconds:02d}"

                    embed.add_field(name="Duration", value=duration_str, inline=True)
                    embed.add_field(name="Requested By", value=requester, inline=True)
                    
                    if queue:
                        next_up_title = queue[0]['title']
                        embed.add_field(name="Next Up", value=next_up_title, inline=False)
                    
                    view = MusicControls(self.bot, voice_client)
                    if self.loop_states.get(guild_id, False):
                         for child in view.children:
                             if isinstance(child, discord.ui.Button) and child.label == "Loop":
                                 child.style = discord.ButtonStyle.success

                    await channel.send(embed=embed, view=view)

            except Exception as e:
                print(f"Error in play_next: {e}")
                if channel:
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
        
        # Search across multiple platforms
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(None, lambda: self.search_multi_platform(song_query))
        except Exception as e:
            await interaction.followup.send(f"Search error: {e}")
            return

        if not info:
            await interaction.followup.send(f"❌ Could not find **{song_query}** on any platform (YouTube, SoundCloud, JioSaavn, Bandcamp).")
            return
        
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
        queue = self.get_queue(guild_id)

        if isinstance(voice_client, discord.VoiceClient) and voice_client.is_playing():
            queue.append(queue_item)
            
            embed = discord.Embed(
                title="Added to Queue", 
                description=f"[{title}]({webpage_url})",
                color=discord.Color.gold()
            )
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            
            duration_str = "Unknown"
            if duration:
                 m = duration // 60
                 s = duration % 60
                 duration_str = f"{m}:{s:02d}"

            embed.add_field(name="Duration", value=duration_str, inline=True)
            embed.set_footer(text=f"Position: {len(queue)}")
            
            await interaction.followup.send(embed=embed)
        else:
            queue.append(queue_item)
            await interaction.followup.send(f"Loading **{title}**...")
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
            self.clear_state(interaction.guild.id)

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