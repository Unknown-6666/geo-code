import discord
import logging
import random
import traceback
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from utils.embed_helpers import create_embed, create_error_embed
from models.economy import UserEconomy, Item, Inventory, Transaction
from database import db
from typing import Literal

logger = logging.getLogger('discord')

# Set up enhanced logging for economy debugging
debug_logger = logging.getLogger('economy_debug')
debug_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('ECONOMY DEBUG - %(message)s'))
debug_logger.addHandler(handler)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Import app here to avoid circular imports
        from app import app
        self.app = app
        logger.info("Economy cog initialized")
        # Initialize shop items on startup
        with self.app.app_context():
            self.initialize_shop()

    def initialize_shop(self):
        """Initialize the shop with default items"""
        debug_logger.info("Initializing shop items...")
        try:
            # Check if items exist
            item_count = Item.query.count()
            debug_logger.info(f"Found {item_count} existing shop items")
            
            if item_count == 0:
                debug_logger.info("No shop items found, adding default items")
                default_items = [
                    {
                        'name': 'Fishing Rod',
                        'description': 'Used for fishing. Who knows what you might catch!',
                        'price': 500,
                        'emoji': '🎣'
                    },
                    {
                        'name': 'Lucky Coin',
                        'description': 'Increases your chances in gambling games by a small amount',
                        'price': 1000,
                        'emoji': '🪙'
                    },
                    {
                        'name': 'Bank Note',
                        'description': 'Increases your bank capacity by 1000',
                        'price': 2500,
                        'emoji': '📜'
                    },
                    {
                        'name': 'Trophy',
                        'description': 'A symbol of wealth and success',
                        'price': 10000,
                        'emoji': '🏆'
                    }
                ]

                for item_data in default_items:
                    debug_logger.info(f"Adding item: {item_data['name']} - {item_data['price']} coins")
                    item = Item(**item_data)
                    db.session.add(item)

                debug_logger.info("Committing shop items to database...")
                db.session.commit()
                debug_logger.info(f"Successfully added {len(default_items)} default shop items")
            else:
                debug_logger.info("Shop items already exist, verifying...")
                items = Item.query.all()
                for item in items:
                    debug_logger.info(f"Found shop item: {item.name} - {item.price} coins, emoji: {item.emoji}")
        except Exception as e:
            debug_logger.error(f"Error initializing shop items: {str(e)}")
            debug_logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()

    async def get_user_economy(self, user_id: str, username: str = None, display_name: str = None) -> UserEconomy:
        """Get or create user economy profile with username and display name"""
        try:
            debug_logger.info(f"get_user_economy called for user_id: {user_id}")
            
            # Try to get user data from Discord if not provided
            if username is None or display_name is None:
                try:
                    user_obj = await self.bot.fetch_user(int(user_id))
                    if username is None:
                        username = user_obj.name
                    if display_name is None:
                        display_name = user_obj.display_name
                    debug_logger.info(f"Fetched Discord user data: {username} / {display_name}")
                except Exception as e:
                    debug_logger.warning(f"Could not fetch Discord user data: {str(e)}")
            
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(user_id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {user_id} ({username})")
                    user = UserEconomy(
                        user_id=str(user_id),
                        username=username,
                        display_name=display_name,
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    debug_logger.info("Committing new user profile to database...")
                    db.session.commit()
                    debug_logger.info("New user profile created successfully")
                else:
                    # Update username and display_name if changed
                    if (username and user.username != username) or (display_name and user.display_name != display_name):
                        debug_logger.info(f"Updating user data: {user.username} -> {username}, {user.display_name} -> {display_name}")
                        if username:
                            user.username = username
                        if display_name:
                            user.display_name = display_name
                        db.session.commit()
                    
                    debug_logger.info(f"Found profile for {user.display_identifier} - wallet: {user.wallet}, bank: {user.bank}")
                return user
        except Exception as e:
            debug_logger.error(f"Error in get_user_economy: {str(e)}")
            debug_logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    @app_commands.command(name="rob", description="Attempt to steal coins from another user")
    @app_commands.describe(target="The user you want to rob")
    async def rob(self, interaction: discord.Interaction, target: discord.Member):
        """Rob another user"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            # Can't rob yourself
            if target.id == interaction.user.id:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "You can't rob yourself!"),
                    ephemeral=True
                )
                return

            # Get both user profiles
            robber = await self.get_user_economy(
                str(interaction.user.id),
                username=interaction.user.name,
                display_name=interaction.user.display_name
            )
            victim = await self.get_user_economy(
                str(target.id),
                username=target.name,
                display_name=target.display_name
            )

            # Check cooldown (1 hour)
            now = datetime.utcnow()
            cooldown = timedelta(hours=1)
            if hasattr(robber, 'last_rob') and robber.last_rob and now - robber.last_rob < cooldown:
                time_left = cooldown - (now - robber.last_rob)
                minutes, seconds = divmod(time_left.seconds, 60)
                await interaction.followup.send(
                    embed=create_error_embed("Cooldown", f"You can rob again in {minutes}m {seconds}s"),
                    ephemeral=True
                )
                return

            # Minimum wallet requirement for robber (100 coins)
            if robber.wallet < 100:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "You need at least 100 coins in your wallet to rob someone!"),
                    ephemeral=True
                )
                return

            # Minimum wallet requirement for victim (50 coins)
            if victim.wallet < 50:
                await interaction.followup.send(
                    embed=create_error_embed("Error", f"{target.name} doesn't have enough coins to rob!"),
                    ephemeral=True
                )
                return

            # 40% success rate
            success = random.random() < 0.4
            
            # Use app context for all database operations
            with self.app.app_context():
                robber.last_rob = now

                if success:
                    # Steal 20-50% of victim's wallet
                    steal_percentage = random.uniform(0.2, 0.5)
                    amount = int(victim.wallet * steal_percentage)

                    victim.wallet -= amount
                    robber.wallet += amount

                    # Record transactions
                    transaction1 = Transaction(
                        user_id=str(interaction.user.id),
                        username=interaction.user.name,
                        display_name=interaction.user.display_name,
                        amount=amount,
                        description=f"Stole {amount} coins from {target.name}"
                    )
                    transaction2 = Transaction(
                        user_id=str(target.id),
                        username=target.name,
                        display_name=target.display_name,
                        amount=-amount,
                        description=f"Got robbed by {interaction.user.name}"
                    )
                    db.session.add(transaction1)
                    db.session.add(transaction2)

                    embed = create_embed(
                        "🦹 Successful Heist!",
                        f"You stole {amount} coins from {target.name}!",
                        color=0x43B581
                    )
                else:
                    # Fine for failed robbery (100 coins)
                    fine = 100
                    robber.wallet -= fine

                    # Record transaction
                    transaction = Transaction(
                        user_id=str(interaction.user.id),
                        username=interaction.user.name, 
                        display_name=interaction.user.display_name,
                        amount=-fine,
                        description="Fine for failed robbery attempt"
                    )
                    db.session.add(transaction)

                    embed = create_embed(
                        "👮 Caught in the Act!",
                        f"You got caught trying to rob {target.name} and had to pay a fine of {fine} coins!",
                        color=0xF04747
                    )

                db.session.commit()
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in rob command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="balance", aliases=["bal"])
    async def balance_prefix(self, ctx):
        """Check your wallet and bank balance (prefix version)"""
        try:
            user = await self.get_user_economy(
                str(ctx.author.id),
                username=ctx.author.name,
                display_name=ctx.author.display_name
            )
            embed = create_embed(
                "💰 Balance",
                f"Wallet: {user.wallet} coins\nBank: {user.bank}/{user.bank_capacity} coins"
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in balance prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
    
    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction):
        """Check your wallet and bank balance"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing balance command for user ID: {interaction.user.id}")
            
            # Get up-to-date user data with username
            user = await self.get_user_economy(
                str(interaction.user.id),
                username=interaction.user.name,
                display_name=interaction.user.display_name
            )
            
            # Use the display identifier for a more personalized message
            embed = create_embed(
                "💰 Balance",
                f"**User**: {user.display_identifier}\n**ID**: {user.user_id}\n\n**Wallet**: {user.wallet} coins\n**Bank**: {user.bank}/{user.bank_capacity} coins"
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in balance command: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="daily")
    async def daily_prefix(self, ctx):
        """Collect daily rewards (prefix version)"""
        try:
            user = await self.get_user_economy(
                str(ctx.author.id),
                username=ctx.author.name,
                display_name=ctx.author.display_name
            )
            
            now = datetime.utcnow()
            if user.last_daily and now - user.last_daily < timedelta(days=1):
                time_left = timedelta(days=1) - (now - user.last_daily)
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                embed = create_error_embed(
                    "Daily Reward",
                    f"You can claim your next daily reward in {hours}h {minutes}m"
                )
                await ctx.send(embed=embed)
                return
                
            # Use app context for database operations
            with self.app.app_context():
                reward = random.randint(100, 200)
                user.wallet += reward
                user.last_daily = now
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(ctx.author.id),
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    amount=reward,
                    description="Daily reward"
                )
                db.session.add(transaction)
                db.session.commit()
                
            embed = create_embed(
                "📅 Daily Reward",
                f"You received {reward} coins!",
                color=0x43B581
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in daily prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
            
    @app_commands.command(name="daily", description="Collect your daily reward")
    async def daily(self, interaction: discord.Interaction):
        """Collect daily rewards"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing daily command for user ID: {interaction.user.id}")
            
            # Get fresh user data inside app context
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                
                debug_logger.info(f"User data - wallet: {user.wallet}, last_daily: {user.last_daily}")
                
                now = datetime.utcnow()
                if user.last_daily and now - user.last_daily < timedelta(days=1):
                    time_left = timedelta(days=1) - (now - user.last_daily)
                    hours, remainder = divmod(time_left.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    debug_logger.info(f"User on cooldown, {hours}h {minutes}m remaining")
                    
                    embed = create_error_embed(
                        "Daily Reward",
                        f"You can claim your next daily reward in {hours}h {minutes}m"
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                # Generate reward and update user data
                reward = random.randint(100, 200)
                debug_logger.info(f"Daily reward generated: {reward}")
                
                user.wallet += reward
                user.last_daily = now
                debug_logger.info(f"Updated wallet: {user.wallet}")

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    amount=reward,
                    description="Daily reward"
                )
                db.session.add(transaction)
                
                # Explicitly commit changes
                debug_logger.info("Committing changes to database...")
                db.session.commit()
                debug_logger.info("Database commit successful")

            # Get the latest user data after commit for verification
            with self.app.app_context():
                updated_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                debug_logger.info(f"Updated wallet after commit: {updated_user.wallet}")

            embed = create_embed(
                "📅 Daily Reward",
                f"You received {reward} coins!",
                color=0x43B581
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in daily command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="work")
    async def work_prefix(self, ctx):
        """Work to earn coins (prefix version)"""
        try:
            user = await self.get_user_economy(
                str(ctx.author.id),
                username=ctx.author.name,
                display_name=ctx.author.display_name
            )
            
            now = datetime.utcnow()
            if user.last_work and now - user.last_work < timedelta(hours=1):
                time_left = timedelta(hours=1) - (now - user.last_work)
                minutes, seconds = divmod(time_left.seconds, 60)
                embed = create_error_embed(
                    "Work",
                    f"You can work again in {minutes}m {seconds}s"
                )
                await ctx.send(embed=embed)
                return
                
            # Use app context for database operations
            with self.app.app_context():
                earnings = random.randint(10, 50)
                user.wallet += earnings
                user.last_work = now
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(ctx.author.id),
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    amount=earnings,
                    description="Work earnings"
                )
                db.session.add(transaction)
                db.session.commit()
                
            embed = create_embed(
                "💼 Work",
                f"You worked hard and earned {earnings} coins!",
                color=0x43B581
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in work prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
            
    @app_commands.command(name="work", description="Work to earn some coins")
    async def work(self, interaction: discord.Interaction):
        """Work to earn coins"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing work command for user ID: {interaction.user.id}")
            
            # Check for cooldown and fetch latest data in same transaction
            now = datetime.utcnow()
            earnings = 0  # Default value in case we need it
            wallet_amount = 0  # For storing the final wallet amount
            
            with self.app.app_context():
                # Get fresh user data directly in this context
                fresh_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not fresh_user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    fresh_user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(fresh_user)
                    db.session.commit()
                    # Re-fetch after creation
                    fresh_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                    
                debug_logger.info(f"Fresh user data - wallet: {fresh_user.wallet}, bank: {fresh_user.bank}")
                
                # Check cooldown inside the same session
                if fresh_user.last_work and now - fresh_user.last_work < timedelta(hours=1):
                    time_left = timedelta(hours=1) - (now - fresh_user.last_work)
                    minutes, seconds = divmod(time_left.seconds, 60)
                    debug_logger.info(f"User on cooldown, {minutes}m {seconds}s remaining")
                    
                    # Create a snapshot of cooldown data
                    cooldown_minutes = minutes
                    cooldown_seconds = seconds
                    on_cooldown = True
                else:
                    on_cooldown = False
                    # Not on cooldown, so process work
                    earnings = random.randint(10, 50)
                    debug_logger.info(f"Earnings generated: {earnings}")
                    
                    # Update wallet and work timestamp
                    fresh_user.wallet += earnings
                    fresh_user.last_work = now
                    debug_logger.info(f"Updated wallet: {fresh_user.wallet}")
    
                    # Record transaction
                    transaction = Transaction(
                        user_id=str(interaction.user.id),
                        username=interaction.user.name,
                        display_name=interaction.user.display_name,
                        amount=earnings,
                        description="Work earnings"
                    )
                    db.session.add(transaction)
                    
                    # Explicitly commit changes
                    debug_logger.info("Committing changes to database...")
                    db.session.commit()
                    debug_logger.info("Database commit successful")
                    
                    # Store the new wallet amount for use outside this context
                    wallet_amount = fresh_user.wallet
            
            # Respond based on cooldown status
            if on_cooldown:
                embed = create_error_embed(
                    "Work",
                    f"You can work again in {cooldown_minutes}m {cooldown_seconds}s"
                )
            else:
                embed = create_embed(
                    "💼 Work",
                    f"You worked hard and earned {earnings} coins!",
                    color=0x43B581
                )
                debug_logger.info(f"Work complete. New wallet balance: {wallet_amount}")
                
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in work command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="deposit", aliases=["dep"])
    async def deposit_prefix(self, ctx, amount: int):
        """Deposit money into bank (prefix version)"""
        try:
            if amount <= 0:
                await ctx.send(
                    embed=create_error_embed("Error", "Amount must be positive")
                )
                return
                
            user = await self.get_user_economy(
                str(ctx.author.id),
                username=ctx.author.name,
                display_name=ctx.author.display_name
            )
            
            if amount > user.wallet:
                await ctx.send(
                    embed=create_error_embed("Error", "You don't have enough coins in your wallet")
                )
                return
                
            space_available = user.bank_capacity - user.bank
            if amount > space_available:
                await ctx.send(
                    embed=create_error_embed("Error", f"Your bank can only hold {space_available} more coins")
                )
                return
                
            # Use app context for database operations
            with self.app.app_context():
                user.wallet -= amount
                user.bank += amount
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(ctx.author.id),
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    amount=amount,
                    description="Bank deposit"
                )
                db.session.add(transaction)
                db.session.commit()
                
            embed = create_embed(
                "🏦 Deposit",
                f"Deposited {amount} coins into your bank",
                color=0x43B581
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in deposit prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
    
    @app_commands.command(name="deposit", description="Deposit coins into your bank")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        """Deposit money into bank"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing deposit command for user ID: {interaction.user.id}, amount: {amount}")
            
            if amount <= 0:
                debug_logger.info(f"Invalid deposit amount: {amount}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Amount must be positive"),
                    ephemeral=True
                )
                return

            # Get fresh user data inside app context
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                
                debug_logger.info(f"User data - wallet: {user.wallet}, bank: {user.bank}, capacity: {user.bank_capacity}")
                
                if amount > user.wallet:
                    debug_logger.info(f"Insufficient funds: {user.wallet} < {amount}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "You don't have enough coins in your wallet"),
                        ephemeral=True
                    )
                    return
    
                space_available = user.bank_capacity - user.bank
                if amount > space_available:
                    debug_logger.info(f"Insufficient bank space: {space_available} < {amount}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", f"Your bank can only hold {space_available} more coins"),
                        ephemeral=True
                    )
                    return
                
                # Update wallet and bank
                user.wallet -= amount
                user.bank += amount
                debug_logger.info(f"Updated wallet: {user.wallet}, bank: {user.bank}")
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    amount=amount,
                    description="Bank deposit"
                )
                db.session.add(transaction)
                
                # Explicitly commit changes
                debug_logger.info("Committing changes to database...")
                db.session.commit()
                debug_logger.info("Database commit successful")

            # Get the latest user data after commit for verification
            with self.app.app_context():
                updated_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                debug_logger.info(f"Updated data after commit - wallet: {updated_user.wallet}, bank: {updated_user.bank}")

            embed = create_embed(
                "🏦 Deposit",
                f"Deposited {amount} coins into your bank",
                color=0x43B581
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in deposit command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="withdraw", aliases=["with"])
    async def withdraw_prefix(self, ctx, amount: int):
        """Withdraw money from bank (prefix version)"""
        try:
            if amount <= 0:
                await ctx.send(
                    embed=create_error_embed("Error", "Amount must be positive")
                )
                return
                
            user = await self.get_user_economy(
                str(ctx.author.id),
                username=ctx.author.name,
                display_name=ctx.author.display_name
            )
            
            if amount > user.bank:
                await ctx.send(
                    embed=create_error_embed("Error", "You don't have enough coins in your bank")
                )
                return
                
            # Use app context for database operations
            with self.app.app_context():
                user.bank -= amount
                user.wallet += amount
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(ctx.author.id),
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    amount=amount,
                    description="Bank withdrawal"
                )
                db.session.add(transaction)
                db.session.commit()
                
            embed = create_embed(
                "🏦 Withdraw",
                f"Withdrew {amount} coins from your bank",
                color=0x43B581
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in withdraw prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
    
    @app_commands.command(name="withdraw", description="Withdraw coins from your bank")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        """Withdraw money from bank"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing withdraw command for user ID: {interaction.user.id}, amount: {amount}")
            
            if amount <= 0:
                debug_logger.info(f"Invalid withdrawal amount: {amount}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Amount must be positive"),
                    ephemeral=True
                )
                return

            # Get fresh user data inside app context
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                
                debug_logger.info(f"User data - wallet: {user.wallet}, bank: {user.bank}")
                
                if amount > user.bank:
                    debug_logger.info(f"Insufficient bank funds: {user.bank} < {amount}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "You don't have enough coins in your bank"),
                        ephemeral=True
                    )
                    return
                
                # Update wallet and bank
                user.bank -= amount
                user.wallet += amount
                debug_logger.info(f"Updated wallet: {user.wallet}, bank: {user.bank}")
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    amount=amount,
                    description="Bank withdrawal"
                )
                db.session.add(transaction)
                
                # Explicitly commit changes
                debug_logger.info("Committing changes to database...")
                db.session.commit()
                debug_logger.info("Database commit successful")

            # Get the latest user data after commit for verification
            with self.app.app_context():
                updated_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                debug_logger.info(f"Updated data after commit - wallet: {updated_user.wallet}, bank: {updated_user.bank}")

            embed = create_embed(
                "🏦 Withdraw",
                f"Withdrew {amount} coins from your bank",
                color=0x43B581
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in withdraw command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="coinflip", description="Bet your coins on a coin flip")
    @app_commands.describe(
        amount="Amount of coins to bet",
        choice="Choose heads or tails"
    )
    async def coinflip(
        self,
        interaction: discord.Interaction,
        amount: int,
        choice: Literal["heads", "tails"]
    ):
        """Gamble coins on a coin flip"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing coinflip command for user ID: {interaction.user.id}, amount: {amount}, choice: {choice}")
            
            if amount <= 0:
                debug_logger.info(f"Invalid bet amount: {amount}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Bet amount must be positive"),
                    ephemeral=True
                )
                return

            # Get fresh user data inside app context
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                
                debug_logger.info(f"User data - wallet: {user.wallet}, bank: {user.bank}")
                
                if amount > user.wallet:
                    debug_logger.info(f"Insufficient funds: {user.wallet} < {amount}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "You don't have enough coins in your wallet"),
                        ephemeral=True
                    )
                    return

                # Determine result
                result = random.choice(["heads", "tails"])
                won = choice == result
                debug_logger.info(f"Coinflip result: {result}, user chose: {choice}, won: {won}")
                
                # Update user's wallet
                if won:
                    user.wallet += amount
                    color = 0x43B581
                    title = "🎉 You won!"
                    description = f"The coin landed on {result}!\nYou won {amount} coins!"
                else:
                    user.wallet -= amount
                    color = 0xF04747
                    title = "😢 You lost!"
                    description = f"The coin landed on {result}!\nYou lost {amount} coins!"
                
                debug_logger.info(f"Updated wallet: {user.wallet}")

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    amount=amount if won else -amount,
                    description=f"Coinflip: {'won' if won else 'lost'}"
                )
                db.session.add(transaction)
                
                # Explicitly commit changes
                debug_logger.info("Committing changes to database...")
                db.session.commit()
                debug_logger.info("Database commit successful")

            # Get the latest user data after commit for verification
            with self.app.app_context():
                updated_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                debug_logger.info(f"Updated wallet after commit: {updated_user.wallet}")

            embed = create_embed(title, description, color=color)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in coinflip command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="slots", description="Play the slot machine")
    @app_commands.describe(amount="Amount of coins to bet")
    async def slots(self, interaction: discord.Interaction, amount: int):
        """Play the slot machine"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing slots command for user ID: {interaction.user.id}, amount: {amount}")
            
            if amount <= 0:
                debug_logger.info(f"Invalid bet amount: {amount}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Bet amount must be positive"),
                    ephemeral=True
                )
                return

            # Get fresh user data inside app context
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                
                debug_logger.info(f"User data - wallet: {user.wallet}, bank: {user.bank}")
                
                if amount > user.wallet:
                    debug_logger.info(f"Insufficient funds: {user.wallet} < {amount}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "You don't have enough coins in your wallet"),
                        ephemeral=True
                    )
                    return

                # Slot machine symbols and their weights
                symbols = ["🍒", "🍊", "🍋", "🍇", "💎", "7️⃣"]
                weights = [0.3, 0.25, 0.2, 0.15, 0.07, 0.03]

                # Get three random symbols
                result = [random.choices(symbols, weights=weights)[0] for _ in range(3)]
                debug_logger.info(f"Slot results: {result}")

                # Calculate winnings
                winnings = 0
                if result[0] == result[1] == result[2]:  # All three match
                    if result[0] == "7️⃣":
                        winnings = amount * 10  # Jackpot
                        debug_logger.info("JACKPOT! Triple 7s")
                    elif result[0] == "💎":
                        winnings = amount * 5
                        debug_logger.info("Big win! Triple diamonds")
                    else:
                        winnings = amount * 3
                        debug_logger.info(f"Good win! Triple {result[0]}")
                elif result[0] == result[1] or result[1] == result[2]:  # Two match
                    winnings = amount * 1.5
                    debug_logger.info("Small win! Two matching symbols")

                # Round winnings to integer
                winnings = int(winnings)
                debug_logger.info(f"Total winnings: {winnings}")

                # Update user's wallet
                user.wallet -= amount
                if winnings > 0:
                    user.wallet += winnings
                debug_logger.info(f"Updated wallet: {user.wallet}")

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    amount=winnings - amount,
                    description="Slots game"
                )
                db.session.add(transaction)
                
                # Explicitly commit changes
                debug_logger.info("Committing changes to database...")
                db.session.commit()
                debug_logger.info("Database commit successful")

            # Get the latest user data after commit for verification
            with self.app.app_context():
                updated_user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                debug_logger.info(f"Updated wallet after commit: {updated_user.wallet}")

            # Create result message
            display = " ".join(result)
            if winnings > 0:
                title = "🎰 You won!"
                description = f"{display}\nBet: {amount} coins\nWon: {winnings} coins!"
                color = 0x43B581
            else:
                title = "🎰 You lost!"
                description = f"{display}\nBet: {amount} coins\nBetter luck next time!"
                color = 0xF04747

            embed = create_embed(title, description, color=color)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in slots command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="shop")
    async def shop_prefix(self, ctx):
        """View available items in the shop (prefix version)"""
        try:
            # Use app context for database operations
            with self.app.app_context():
                items = Item.query.filter_by(is_buyable=True).all()
                
                if not items:
                    await ctx.send(
                        embed=create_error_embed("Shop", "No items available in the shop right now")
                    )
                    return
                    
                embed = create_embed(
                    "🛍️ Item Shop",
                    "Here are the items available for purchase:"
                )
                
                for item in items:
                    embed.add_field(
                        name=f"{item.emoji} {item.name} - {item.price} coins",
                        value=item.description,
                        inline=False
                    )
                    
                embed.set_footer(text="Use !buy <item> to purchase an item")
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in shop prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
            
    @app_commands.command(name="shop", description="View the item shop")
    async def shop(self, interaction: discord.Interaction):
        """View available items in the shop"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            # Use app context for database operations
            with self.app.app_context():
                items = Item.query.filter_by(is_buyable=True).all()

                if not items:
                    await interaction.followup.send(
                        embed=create_error_embed("Shop", "No items available in the shop right now"),
                        ephemeral=True
                    )
                    return

                embed = create_embed(
                    "🛍️ Item Shop",
                    "Here are the items available for purchase:"
                )

                for item in items:
                    embed.add_field(
                        name=f"{item.emoji} {item.name} - {item.price} coins",
                        value=item.description,
                        inline=False
                    )

                embed.set_footer(text="Use /buy <item> to purchase an item")
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in shop command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="buy")
    async def buy_prefix(self, ctx, *, item_name: str):
        """Buy an item from the shop (prefix version)"""
        try:
            # Use app context for database operations
            with self.app.app_context():
                item = Item.query.filter_by(name=item_name, is_buyable=True).first()
                if not item:
                    await ctx.send(
                        embed=create_error_embed("Error", "That item doesn't exist or isn't available")
                    )
                    return
                    
                user = await self.get_user_economy(
                    str(ctx.author.id),
                    username=ctx.author.name,
                    display_name=ctx.author.display_name
                )
                if user.wallet < item.price:
                    await ctx.send(
                        embed=create_error_embed("Error", "You don't have enough coins to buy this item")
                    )
                    return
                    
                # Add item to inventory
                inventory = Inventory.query.filter_by(
                    user_id=str(ctx.author.id),
                    item_id=item.id
                ).first()
                
                if inventory:
                    inventory.quantity += 1
                else:
                    inventory = Inventory(
                        user_id=str(ctx.author.id),
                        username=ctx.author.name,
                        display_name=ctx.author.display_name,
                        item_id=item.id,
                        quantity=1
                    )
                    db.session.add(inventory)
                    
                # Deduct coins
                user.wallet -= item.price
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(ctx.author.id),
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    amount=-item.price,
                    description=f"Bought {item.name}"
                )
                db.session.add(transaction)
                db.session.commit()
                
                embed = create_embed(
                    "✅ Purchase Successful",
                    f"You bought {item.emoji} {item.name} for {item.price} coins!",
                    color=0x43B581
                )
                
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in buy prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
    
    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_name="Name of the item to buy")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        """Buy an item from the shop"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing buy command for user ID: {interaction.user.id}, item: {item_name}")
            
            # Use app context for database operations
            with self.app.app_context():
                # Find the item
                item = Item.query.filter_by(name=item_name, is_buyable=True).first()
                if not item:
                    debug_logger.info(f"Item not found or not buyable: {item_name}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "That item doesn't exist or isn't available"),
                        ephemeral=True
                    )
                    return
                
                debug_logger.info(f"Item found: {item.name}, price: {item.price}")

                # Get fresh user data
                user = UserEconomy.query.filter_by(user_id=str(interaction.user.id)).first()
                if not user:
                    debug_logger.info(f"Creating new economy profile for user {interaction.user.id}")
                    user = UserEconomy(
                        user_id=str(interaction.user.id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                
                debug_logger.info(f"User data - wallet: {user.wallet}, bank: {user.bank}")
                
                # Check if user has enough money
                if user.wallet < item.price:
                    debug_logger.info(f"Insufficient funds: {user.wallet} < {item.price}")
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "You don't have enough coins to buy this item"),
                        ephemeral=True
                    )
                    return

                # Add item to inventory
                inventory = Inventory.query.filter_by(
                    user_id=str(interaction.user.id),
                    item_id=item.id
                ).first()

                if inventory:
                    inventory.quantity += 1
                    debug_logger.info(f"Updated inventory quantity to: {inventory.quantity}")
                else:
                    inventory = Inventory(
                        user_id=str(interaction.user.id),
                        username=interaction.user.name,
                        display_name=interaction.user.display_name,
                        item_id=item.id,
                        quantity=1
                    )
                    db.session.add(inventory)
                    debug_logger.info("Added new inventory entry")

                # Deduct coins
                user.wallet -= item.price
                debug_logger.info(f"Updated wallet: {user.wallet}")

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    username=interaction.user.name,
                    display_name=interaction.user.display_name,
                    amount=-item.price,
                    description=f"Bought {item.name}"
                )
                db.session.add(transaction)
                
                # Explicitly commit changes
                debug_logger.info("Committing changes to database...")
                db.session.commit()
                debug_logger.info("Database commit successful")

                embed = create_embed(
                    "✅ Purchase Successful",
                    f"You bought {item.emoji} {item.name} for {item.price} coins!",
                    color=0x43B581
                )
                
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in buy command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory_prefix(self, ctx):
        """View your inventory (prefix version)"""
        try:
            # Use app context for database operations
            with self.app.app_context():
                inventory_items = Inventory.query.filter_by(
                    user_id=str(ctx.author.id)
                ).all()
                
                if not inventory_items:
                    await ctx.send(
                        embed=create_error_embed("Inventory", "Your inventory is empty")
                    )
                    return
                    
                embed = create_embed(
                    "🎒 Your Inventory",
                    "Here are your items:"
                )
                
                for inv in inventory_items:
                    embed.add_field(
                        name=f"{inv.item.emoji} {inv.item.name} x{inv.quantity}",
                        value=inv.item.description,
                        inline=False
                    )
                    
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in inventory prefix command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
    
    @app_commands.command(name="inventory", description="View your inventory")
    async def inventory(self, interaction: discord.Interaction):
        """View your inventory"""
        try:
            # First acknowledge the interaction to prevent timeouts
            await interaction.response.defer()
            
            debug_logger.info(f"Processing inventory command for user ID: {interaction.user.id}")
            
            # Use app context for database operations
            with self.app.app_context():
                inventory_items = Inventory.query.filter_by(
                    user_id=str(interaction.user.id)
                ).all()
                
                debug_logger.info(f"Found {len(inventory_items)} inventory items")

                if not inventory_items:
                    debug_logger.info("User has empty inventory")
                    await interaction.followup.send(
                        embed=create_error_embed("Inventory", "Your inventory is empty"),
                        ephemeral=True
                    )
                    return

                embed = create_embed(
                    "🎒 Your Inventory",
                    "Here are your items:"
                )

                for inv in inventory_items:
                    debug_logger.info(f"Adding item to embed: {inv.item.name}, quantity: {inv.quantity}")
                    embed.add_field(
                        name=f"{inv.item.emoji} {inv.item.name} x{inv.quantity}",
                        value=inv.item.description,
                        inline=False
                    )

                debug_logger.info("Sending inventory response")
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in inventory command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    try:
        # Add detailed logging for setup process
        debug_logger.info("Starting Economy cog setup...")
        
        # Register economy commands in app_commands
        debug_logger.info("Creating Economy cog instance...")
        economy_cog = Economy(bot)
        
        debug_logger.info("Adding Economy cog to bot...")
        await bot.add_cog(economy_cog)
        
        # Verify slash commands are registered
        debug_logger.info("Checking registered commands...")
        all_commands = bot.tree.get_commands()
        command_names = [cmd.name for cmd in all_commands]
        debug_logger.info(f"Registered global commands: {', '.join(command_names)}")
        
        # Check if economy commands are registered
        economy_commands = ['balance', 'daily', 'work', 'deposit', 'withdraw', 'rob', 'shop', 'buy', 'inventory']
        missing_commands = [cmd for cmd in economy_commands if cmd not in command_names]
        
        if missing_commands:
            debug_logger.warning(f"Missing economy commands in global tree: {', '.join(missing_commands)}")
        else:
            debug_logger.info("All economy commands registered successfully")
            
        debug_logger.info("Economy cog setup complete")
    except Exception as e:
        debug_logger.error(f"Error in Economy cog setup: {e}")
        debug_logger.error(f"Traceback: {traceback.format_exc()}")
        raise