import discord
import logging
import random
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from utils.embed_helpers import create_embed, create_error_embed
from models.economy import UserEconomy, Item, Inventory, Transaction
from database import db

logger = logging.getLogger('discord')

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_economy(self, user_id: str) -> UserEconomy:
        """Get or create user economy profile"""
        from dashboard.app import app
        with app.app_context():
            user = UserEconomy.query.filter_by(user_id=str(user_id)).first()
            if not user:
                user = UserEconomy(user_id=str(user_id))
                db.session.add(user)
                db.session.commit()
            return user

    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction):
        """Check your wallet and bank balance"""
        user = await self.get_user_economy(interaction.user.id)
        embed = create_embed(
            "💰 Balance",
            f"Wallet: {user.wallet} coins\nBank: {user.bank}/{user.bank_capacity} coins"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Collect your daily reward")
    async def daily(self, interaction: discord.Interaction):
        """Collect daily rewards"""
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
            await interaction.response.send_message(embed=embed)
            return

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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Work to earn some coins")
    async def work(self, interaction: discord.Interaction):
        """Work to earn coins"""
        user = await self.get_user_economy(interaction.user.id)

        now = datetime.utcnow()
        if user.last_work and now - user.last_work < timedelta(hours=1):
            time_left = timedelta(hours=1) - (now - user.last_work)
            minutes, seconds = divmod(time_left.seconds, 60)
            embed = create_error_embed(
                "Work",
                f"You can work again in {minutes}m {seconds}s"
            )
            await interaction.response.send_message(embed=embed)
            return

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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="deposit", description="Deposit coins into your bank")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        """Deposit money into bank"""
        if amount <= 0:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Amount must be positive"),
                ephemeral=True
            )
            return

        user = await self.get_user_economy(interaction.user.id)

        if amount > user.wallet:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You don't have enough coins in your wallet"),
                ephemeral=True
            )
            return

        space_available = user.bank_capacity - user.bank
        if amount > space_available:
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"Your bank can only hold {space_available} more coins"),
                ephemeral=True
            )
            return

        user.wallet -= amount
        user.bank += amount
        db.session.commit()

        embed = create_embed(
            "🏦 Deposit",
            f"Deposited {amount} coins into your bank",
            color=0x43B581
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="withdraw", description="Withdraw coins from your bank")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        """Withdraw money from bank"""
        if amount <= 0:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Amount must be positive"),
                ephemeral=True
            )
            return

        user = await self.get_user_economy(interaction.user.id)

        if amount > user.bank:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You don't have enough coins in your bank"),
                ephemeral=True
            )
            return

        user.bank -= amount
        user.wallet += amount
        db.session.commit()

        embed = create_embed(
            "🏦 Withdraw",
            f"Withdrew {amount} coins from your bank",
            color=0x43B581
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))