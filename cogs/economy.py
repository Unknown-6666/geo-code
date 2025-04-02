import discord
import logging
import random
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from utils.embed_helpers import create_embed, create_error_embed
from models.economy import UserEconomy, Item, Inventory, Transaction
from database import db
from typing import Literal

logger = logging.getLogger('discord')

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
        logger.info("Initializing shop items...")
        try:
            # Check if items exist
            if Item.query.count() == 0:
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
                    item = Item(**item_data)
                    db.session.add(item)

                db.session.commit()
                logger.info("Shop items initialized successfully")
            else:
                logger.info("Shop items already exist")
        except Exception as e:
            logger.error(f"Error initializing shop items: {str(e)}")
            db.session.rollback()

    async def get_user_economy(self, user_id: str) -> UserEconomy:
        """Get or create user economy profile"""
        try:
            with self.app.app_context():
                user = UserEconomy.query.filter_by(user_id=str(user_id)).first()
                if not user:
                    logger.info(f"Creating new economy profile for user {user_id}")
                    user = UserEconomy(
                        user_id=str(user_id),
                        wallet=0,
                        bank=0,
                        bank_capacity=1000
                    )
                    db.session.add(user)
                    db.session.commit()
                return user
        except Exception as e:
            logger.error(f"Error in get_user_economy: {str(e)}")
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
            robber = await self.get_user_economy(interaction.user.id)
            victim = await self.get_user_economy(target.id)

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
                        amount=amount,
                        description=f"Stole {amount} coins from {target.name}"
                    )
                    transaction2 = Transaction(
                        user_id=str(target.id),
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
            user = await self.get_user_economy(ctx.author.id)
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
            
            user = await self.get_user_economy(interaction.user.id)
            embed = create_embed(
                "💰 Balance",
                f"Wallet: {user.wallet} coins\nBank: {user.bank}/{user.bank_capacity} coins"
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in balance command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.command(name="daily")
    async def daily_prefix(self, ctx):
        """Collect daily rewards (prefix version)"""
        try:
            user = await self.get_user_economy(ctx.author.id)
            
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
            
            user = await self.get_user_economy(interaction.user.id)

            now = datetime.utcnow()
            if user.last_daily and now - user.last_daily < timedelta(days=1):
                time_left = timedelta(days=1) - (now - user.last_daily)
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                embed = create_error_embed(
                    "Daily Reward",
                    f"You can claim your next daily reward in {hours}h {minutes}m"
                )
                await interaction.followup.send(embed=embed)
                return

            # Use app context for database operations
            with self.app.app_context():
                reward = random.randint(100, 200)
                user.wallet += reward
                user.last_daily = now

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
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
            user = await self.get_user_economy(ctx.author.id)
            
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
            
            user = await self.get_user_economy(interaction.user.id)

            now = datetime.utcnow()
            if user.last_work and now - user.last_work < timedelta(hours=1):
                time_left = timedelta(hours=1) - (now - user.last_work)
                minutes, seconds = divmod(time_left.seconds, 60)
                embed = create_error_embed(
                    "Work",
                    f"You can work again in {minutes}m {seconds}s"
                )
                await interaction.followup.send(embed=embed)
                return

            # Use app context for database operations
            with self.app.app_context():
                earnings = random.randint(10, 50)
                user.wallet += earnings
                user.last_work = now

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
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
                
            user = await self.get_user_economy(ctx.author.id)
            
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
            
            if amount <= 0:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Amount must be positive"),
                    ephemeral=True
                )
                return

            user = await self.get_user_economy(interaction.user.id)

            if amount > user.wallet:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "You don't have enough coins in your wallet"),
                    ephemeral=True
                )
                return

            space_available = user.bank_capacity - user.bank
            if amount > space_available:
                await interaction.followup.send(
                    embed=create_error_embed("Error", f"Your bank can only hold {space_available} more coins"),
                    ephemeral=True
                )
                return

            # Use app context for database operations
            with self.app.app_context():
                user.wallet -= amount
                user.bank += amount
                db.session.commit()

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
                
            user = await self.get_user_economy(ctx.author.id)
            
            if amount > user.bank:
                await ctx.send(
                    embed=create_error_embed("Error", "You don't have enough coins in your bank")
                )
                return
                
            # Use app context for database operations
            with self.app.app_context():
                user.bank -= amount
                user.wallet += amount
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
            
            if amount <= 0:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Amount must be positive"),
                    ephemeral=True
                )
                return

            user = await self.get_user_economy(interaction.user.id)

            if amount > user.bank:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "You don't have enough coins in your bank"),
                    ephemeral=True
                )
                return

            # Use app context for database operations
            with self.app.app_context():
                user.bank -= amount
                user.wallet += amount
                db.session.commit()

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
            
            if amount <= 0:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Bet amount must be positive"),
                    ephemeral=True
                )
                return

            user = await self.get_user_economy(interaction.user.id)
            if amount > user.wallet:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "You don't have enough coins in your wallet"),
                    ephemeral=True
                )
                return

            result = random.choice(["heads", "tails"])
            won = choice == result

            # Use app context for database operations
            with self.app.app_context():
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

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    amount=amount if won else -amount,
                    description=f"Coinflip: {'won' if won else 'lost'}"
                )
                db.session.add(transaction)
                db.session.commit()

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
            
            if amount <= 0:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Bet amount must be positive"),
                    ephemeral=True
                )
                return

            user = await self.get_user_economy(interaction.user.id)
            if amount > user.wallet:
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

            # Calculate winnings
            winnings = 0
            if result[0] == result[1] == result[2]:  # All three match
                if result[0] == "7️⃣":
                    winnings = amount * 10  # Jackpot
                elif result[0] == "💎":
                    winnings = amount * 5
                else:
                    winnings = amount * 3
            elif result[0] == result[1] or result[1] == result[2]:  # Two match
                winnings = amount * 1.5

            # Round winnings to integer
            winnings = int(winnings)

            # Use app context for database operations
            with self.app.app_context():
                # Update user's wallet
                user.wallet -= amount
                if winnings > 0:
                    user.wallet += winnings

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
                    amount=winnings - amount,
                    description="Slots game"
                )
                db.session.add(transaction)
                db.session.commit()

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
                    
                user = await self.get_user_economy(ctx.author.id)
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
                        item_id=item.id,
                        quantity=1
                    )
                    db.session.add(inventory)
                    
                # Deduct coins
                user.wallet -= item.price
                
                # Record transaction
                transaction = Transaction(
                    user_id=str(ctx.author.id),
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
            
            # Use app context for database operations
            with self.app.app_context():
                item = Item.query.filter_by(name=item_name, is_buyable=True).first()
                if not item:
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "That item doesn't exist or isn't available"),
                        ephemeral=True
                    )
                    return

                user = await self.get_user_economy(interaction.user.id)
                if user.wallet < item.price:
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
                else:
                    inventory = Inventory(
                        user_id=str(interaction.user.id),
                        item_id=item.id,
                        quantity=1
                    )
                    db.session.add(inventory)

                # Deduct coins
                user.wallet -= item.price

                # Record transaction
                transaction = Transaction(
                    user_id=str(interaction.user.id),
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
            
            # Use app context for database operations
            with self.app.app_context():
                inventory_items = Inventory.query.filter_by(
                    user_id=str(interaction.user.id)
                ).all()

                if not inventory_items:
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
                    embed.add_field(
                        name=f"{inv.item.emoji} {inv.item.name} x{inv.quantity}",
                        value=inv.item.description,
                        inline=False
                    )

                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in inventory command: {str(e)}")
            # If we haven't responded yet, respond with the error
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))