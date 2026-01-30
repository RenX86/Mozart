import discord
from discord.ext import commands
from utils.database import DatabaseManager

class Moderation(commands.Cog):
    def __init__(self, bot, db_manager: DatabaseManager):
        self.bot = bot
        self.db = db_manager
        self.profanity = ["fuck you", "nigga"]

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        # Check for profanity
        for term in self.profanity:
            if term.lower() in msg.content.lower():
                num_warnings = self.db.increase_and_get_warnings(msg.author.id, msg.guild.id)
                
                if num_warnings >= 3:
                    try:
                        await msg.author.ban(reason="Exceeded 3 strikes for using profanity.")
                        await msg.channel.send(f"{msg.author.mention} has been banned for repeated profanity.")
                    except discord.Forbidden:
                        await msg.channel.send("I tried to ban the user but I lack permissions.")
                    except discord.HTTPException as e:
                        await msg.channel.send(f"Failed to ban user: {e}")
                    
                else:
                    await msg.channel.send(
                        f"Warning {num_warnings}/3 {msg.author.mention}. If you reach 3 warnings, you will be banned."
                    )
                    try:
                        await msg.delete()
                    except discord.Forbidden:
                        pass # Ignore if we can't delete
                break # Stop checking other terms if one is found
