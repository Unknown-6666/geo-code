import discord
import logging
import random
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from utils.embed_helpers import create_embed, create_error_embed
from models.economy import UserEconomy, Item, Inventory, Transaction
from database import session
from typing import Literal

logger = logging.getLogger('discord')

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_economy(self, user_id: str) -> UserEconomy:
        """Get or create user economy profile"""
        user = session.query(UserEconomy).filter_by(user_id=str(user_id)).first()
        if not user:
            user = UserEconomy(user_id=str(user_id))
            session.add(user)
            session.commit()
        return user

    @app_commands.command(name="rob", description="Attempt to steal coins from another user")
    @app_commands.describe(target="The user you want to rob")
    async def rob(self, interaction: discord.Interaction, target: discord.Member):
        """Rob another user"""
        # Can't rob yourself
        if target.id == interaction.user.id:
            await interaction.response.send_message(
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
        if robber.last_rob and now - robber.last_rob < cooldown:
            time_left = cooldown - (now - robber.last_rob)
            minutes, seconds = divmod(time_left.seconds, 60)
            await interaction.response.send_message(
                embed=create_error_embed("Cooldown", f"You can rob again in {minutes}m {seconds}s"),
                ephemeral=True
            )
            return

        # Minimum wallet requirement for robber (100 coins)
        if robber.wallet < 100:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You need at least 100 coins in your wallet to rob someone!"),
                ephemeral=True
            )
            return

        # Minimum wallet requirement for victim (50 coins)
        if victim.wallet < 50:
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"{target.name} doesn't have enough coins to rob!"),
                ephemeral=True
            )
            return

        # 40% success rate
        success = random.random() < 0.4
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
            session.add(transaction1)
            session.add(transaction2)

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
            session.add(transaction)

            embed = create_embed(
                "👮 Caught in the Act!",
                f"You got caught trying to rob {target.name} and had to pay a fine of {fine} coins!",
                color=0xF04747
            )

        session.commit()
        await interaction.response.send_message(embed=embed)

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
        session.add(transaction)
        session.commit()

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
        session.add(transaction)
        session.commit()

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
        session.commit()

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
        session.commit()

        embed = create_embed(
            "🏦 Withdraw",
            f"Withdrew {amount} coins from your bank",
            color=0x43B581
        )
        await interaction.response.send_message(embed=embed)

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
        if amount <= 0:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Bet amount must be positive"),
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

        result = random.choice(["heads", "tails"])
        won = choice == result

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
        session.add(transaction)
        session.commit()

        embed = create_embed(title, description, color=color)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Play the slot machine")
    @app_commands.describe(amount="Amount of coins to bet")
    async def slots(self, interaction: discord.Interaction, amount: int):
        """Play the slot machine"""
        if amount <= 0:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Bet amount must be positive"),
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

        # Update user's wallet
        user.wallet -= amount
        if winnings > 0:
            user.wallet += winnings

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

        # Record transaction
        transaction = Transaction(
            user_id=str(interaction.user.id),
            amount=winnings - amount,
            description="Slots game"
        )
        session.add(transaction)
        session.commit()

        embed = create_embed(title, description, color=color)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="View the item shop")
    async def shop(self, interaction: discord.Interaction):
        """View available items in the shop"""
        items = session.query(Item).filter_by(is_buyable=True).all()

        if not items:
            await interaction.response.send_message(
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_name="Name of the item to buy")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        """Buy an item from the shop"""
        item = session.query(Item).filter_by(name=item_name, is_buyable=True).first()
        if not item:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "That item doesn't exist or isn't available"),
                ephemeral=True
            )
            return

        user = await self.get_user_economy(interaction.user.id)
        if user.wallet < item.price:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You don't have enough coins to buy this item"),
                ephemeral=True
            )
            return

        # Add item to inventory
        inventory = session.query(Inventory).filter_by(
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
            session.add(inventory)

        # Deduct coins
        user.wallet -= item.price

        # Record transaction
        transaction = Transaction(
            user_id=str(interaction.user.id),
            amount=-item.price,
            description=f"Bought {item.name}"
        )
        session.add(transaction)
        session.commit()

        embed = create_embed(
            "✅ Purchase Successful",
            f"You bought {item.emoji} {item.name} for {item.price} coins!",
            color=0x43B581
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inventory", description="View your inventory")
    async def inventory(self, interaction: discord.Interaction):
        """View your inventory"""
        inventory_items = session.query(Inventory).filter_by(
            user_id=str(interaction.user.id)
        ).all()

        if not inventory_items:
            await interaction.response.send_message(
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

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))