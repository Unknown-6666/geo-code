import discord
import logging
import random
import aiohttp
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed

logger = logging.getLogger('discord')

class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meme_subreddits = [
            'memes',
            'dankmemes',
            'wholesomememes',
            'ProgrammerHumor'
        ]

    @app_commands.command(name="meme", description="Get a random meme")
    async def meme(self, interaction: discord.Interaction):
        """Fetch and send a random meme"""
        await interaction.response.defer()  # Defer the response as API call might take time

        try:
            subreddit = random.choice(self.meme_subreddits)
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://meme-api.com/gimme/{subreddit}') as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        embed = create_embed(
                            title=data['title'],
                            description=f"👍 {data.get('ups', 0)} | From r/{data['subreddit']}"
                        )
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"Posted by u/{data['author']}")
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(
                            embed=create_error_embed("Error", "Failed to fetch meme. Try again later."),
                            ephemeral=True
                        )
        except Exception as e:
            logger.error(f"Error fetching meme: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred while fetching the meme."),
                ephemeral=True
            )

    @app_commands.command(name="memedump", description="Get multiple random memes")
    @app_commands.describe(count="Number of memes to fetch (max 5)")
    async def memedump(self, interaction: discord.Interaction, count: int = 3):
        """Send multiple random memes at once"""
        # Limit the count to prevent spam
        count = min(max(1, count), 5)
        
        await interaction.response.defer()  # Defer the response as this might take time

        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(count):
                    subreddit = random.choice(self.meme_subreddits)
                    async with session.get(f'https://meme-api.com/gimme/{subreddit}') as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            embed = create_embed(
                                title=data['title'],
                                description=f"👍 {data.get('ups', 0)} | From r/{data['subreddit']}"
                            )
                            embed.set_image(url=data['url'])
                            embed.set_footer(text=f"Posted by u/{data['author']}")
                            
                            await interaction.followup.send(embed=embed)
                        else:
                            continue
        except Exception as e:
            logger.error(f"Error in memedump: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred while fetching memes."),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Memes(bot))
