import discord
import logging
import random
import aiohttp
import asyncio
from collections import deque
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
        # Store last 10 meme IDs to prevent duplicates
        self.meme_history = deque(maxlen=10)

    async def get_unique_meme(self):
        """Fetch a meme that hasn't been shown in the last 10 memes"""
        max_attempts = 5  # Prevent infinite loops
        attempts = 0

        while attempts < max_attempts:
            try:
                # Try to get a meme using the primary API
                meme_data = await self._get_meme_from_meme_api()
                
                if meme_data:
                    return meme_data
                
                # If primary API fails, try the backup API
                logger.info("Primary API failed, trying backup Reddit JSON API...")
                meme_data = await self._get_meme_from_reddit_json()
                
                if meme_data:
                    return meme_data
                    
            except Exception as e:
                logger.error(f"Exception in get_unique_meme: {str(e)}")
                
            attempts += 1
            logger.info(f"Attempt {attempts}/{max_attempts} failed, trying again...")

        # If we couldn't get a unique meme, return None
        logger.warning("Could not find a unique meme after maximum attempts")
        return None
        
    async def _get_meme_from_meme_api(self):
        """Try to get a meme from the meme-api.com API"""
        try:
            subreddit = random.choice(self.meme_subreddits)
            logger.info(f"Fetching meme from meme-api.com, subreddit: {subreddit}")
            
            async with aiohttp.ClientSession() as session:
                request_url = f'https://meme-api.com/gimme/{subreddit}'
                logger.info(f"Making request to: {request_url}")
                
                async with session.get(request_url, timeout=5) as response:
                    logger.info(f"Response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Received meme data: Title: {data.get('title', 'No title')}")
                        
                        meme_id = data.get('postLink', '')  # Use post link as unique identifier
                        if not meme_id:
                            logger.warning(f"Meme data missing postLink: {data}")
                            return None
                            
                        # If meme hasn't been shown recently, use it
                        if meme_id not in self.meme_history:
                            self.meme_history.append(meme_id)
                            return data
                        else:
                            logger.info(f"Skipping duplicate meme: {meme_id}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Error response from meme API: Status {response.status}, Response: {error_text}")
        except Exception as e:
            logger.error(f"Error in primary meme API: {str(e)}")
            
        return None
        
    async def _get_meme_from_reddit_json(self):
        """Try to get a meme directly from Reddit JSON API"""
        try:
            subreddit = random.choice(self.meme_subreddits)
            logger.info(f"Fetching meme from Reddit JSON API, subreddit: {subreddit}")
            
            async with aiohttp.ClientSession() as session:
                # Using Reddit's JSON API directly
                request_url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit=20'
                headers = {
                    'User-Agent': 'discord-bot:v1.0 (by /u/DiscordBot)'
                }
                
                logger.info(f"Making request to Reddit API: {request_url}")
                async with session.get(request_url, headers=headers, timeout=5) as response:
                    logger.info(f"Reddit API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        posts = data['data']['children']
                        
                        # Filter out pinned posts, non-image posts, etc.
                        valid_posts = [
                            post['data'] for post in posts 
                            if not post['data'].get('stickied', False)
                            and not post['data'].get('is_self', True)
                            and post['data'].get('post_hint', '') == 'image'
                        ]
                        
                        if not valid_posts:
                            logger.warning(f"No valid image posts found in r/{subreddit}")
                            return None
                            
                        # Select a random post
                        post = random.choice(valid_posts)
                        
                        # Create a response in the same format as meme-api
                        meme_id = post['permalink']
                        
                        if meme_id in self.meme_history:
                            logger.info(f"Skipping duplicate Reddit meme: {meme_id}")
                            return None
                            
                        # Add to history
                        self.meme_history.append(meme_id)
                        
                        formatted_data = {
                            'title': post['title'],
                            'url': post['url'],
                            'subreddit': subreddit,
                            'postLink': f"https://reddit.com{post['permalink']}",
                            'author': post['author'],
                            'ups': post['ups']
                        }
                        
                        logger.info(f"Successfully retrieved Reddit meme: {formatted_data['title']}")
                        return formatted_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Error from Reddit API: Status {response.status}, Response: {error_text}")
        except Exception as e:
            logger.error(f"Error in backup Reddit API: {str(e)}")
            
        return None

    @app_commands.command(name="meme", description="Get a random meme")
    async def meme(self, interaction: discord.Interaction):
        """Fetch and send a random meme"""
        logger.info(f"Meme command invoked by {interaction.user.name} (ID: {interaction.user.id})")
        
        # Immediately tell Discord we're processing the command
        # This sets a 15-minute window to respond instead of 3 seconds
        try:
            await interaction.response.defer()
            logger.info("Successfully deferred interaction response")
        except Exception as defer_error:
            logger.error(f"Failed to defer response: {str(defer_error)}")
            # If we can't defer, we'll try to respond directly
            try:
                await interaction.response.send_message("Getting a meme for you...", ephemeral=True)
                logger.info("Sent immediate response instead of deferring")
                return  # Exit early since we can't properly handle this interaction
            except Exception:
                logger.error("Could not respond to interaction at all, it may have timed out")
                return

        try:
            logger.info("Attempting to fetch a unique meme...")
            
            # Pre-construct an error embed in case we need it
            error_embed = create_error_embed("Meme Error", "Something went wrong while fetching a meme. Try again in a moment.")
            
            # Fetch the meme with a short timeout to prevent hanging
            try:
                data = await asyncio.wait_for(self.get_unique_meme(), timeout=8.0)
            except asyncio.TimeoutError:
                logger.error("Timeout while fetching meme")
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return
            
            if not data:
                logger.warning("No unique meme found after all attempts")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Couldn't find a unique meme. Try again later."),
                    ephemeral=True
                )
                return
                
            logger.info(f"Meme found successfully - Title: {data.get('title', 'No title')}")
            
            # Check if all required fields are present
            required_fields = ['title', 'url', 'subreddit', 'author']
            missing_fields = [field for field in required_fields if field not in data or not data[field]]
            
            if missing_fields:
                logger.error(f"Meme data missing required fields: {missing_fields}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", f"The meme data is incomplete. Missing: {', '.join(missing_fields)}"),
                    ephemeral=True
                )
                return
            
            # Create and send the embed
            try:
                embed = create_embed(
                    title=data['title'],
                    description=f"👍 {data.get('ups', 0)} | From r/{data['subreddit']}"
                )
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"Posted by u/{data['author']}")
                
                logger.info(f"Sending meme embed with image URL: {data['url']}")
                await interaction.followup.send(embed=embed)
                logger.info("Meme sent successfully")
            except Exception as embed_error:
                logger.error(f"Error creating or sending embed: {str(embed_error)}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", f"Error displaying the meme: {str(embed_error)}"),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error fetching meme: {str(e)}", exc_info=True)
            try:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "An error occurred while fetching the meme."),
                    ephemeral=True
                )
            except Exception:
                logger.error("Failed to send error message")
                # At this point we can't do anything else

    @app_commands.command(name="memedump", description="Get multiple random memes")
    @app_commands.describe(count="Number of memes to fetch (max 5)")
    async def memedump(self, interaction: discord.Interaction, count: int = 3):
        """Send multiple random memes at once"""
        # Limit the count to prevent spam
        count = min(max(1, count), 5)

        await interaction.response.defer()  # Defer the response as this might take time

        try:
            memes_sent = 0
            max_attempts = count * 2  # Allow some extra attempts to find unique memes
            attempts = 0

            while memes_sent < count and attempts < max_attempts:
                data = await self.get_unique_meme()
                if data:
                    embed = create_embed(
                        title=data['title'],
                        description=f"👍 {data.get('ups', 0)} | From r/{data['subreddit']}"
                    )
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"Posted by u/{data['author']}")

                    await interaction.followup.send(embed=embed)
                    memes_sent += 1

                attempts += 1

            if memes_sent < count:
                await interaction.followup.send(
                    embed=create_error_embed("Note", "Could not find enough unique memes."),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error in memedump: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred while fetching memes."),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Memes(bot))