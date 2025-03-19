import discord
from discord.ext import commands
from utils.embed_helpers import create_embed
from config import COLORS

class MemberEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        channel = member.guild.system_channel
        if channel:
            embed = create_embed(
                "Welcome!",
                f"Welcome {member.mention} to {member.guild.name}! 🎉",
                COLORS["SUCCESS"]
            )
            embed.set_footer(text="Type !help to see available commands")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave events"""
        channel = member.guild.system_channel
        if channel:
            embed = create_embed(
                "Goodbye!",
                f"{member.name} has left the server. 👋",
                COLORS["SECONDARY"]
            )
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MemberEvents(bot))
