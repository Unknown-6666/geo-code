import os
import random
import asyncio
import discord
import logging
from discord.ext import commands, tasks
from config import TOKEN, DEFAULT_PREFIX, STATUS_MESSAGES

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=DEFAULT_PREFIX,
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Load cogs and start tasks"""
        logger.info("Setting up bot...")
        # Load all cogs
        await self.load_extension("cogs.basic_commands")
        await self.load_extension("cogs.member_events")
        logger.info("Loaded all cogs successfully")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Successfully logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info('Bot is now ready to receive commands')
        print(f'Logged in as {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print('------')

        # Start status rotation after bot is ready
        if not self.change_status.is_running():
            self.change_status.start()
            logger.info("Started status rotation task")

    @tasks.loop(minutes=5)
    async def change_status(self):
        """Rotate through status messages"""
        try:
            status = random.choice(STATUS_MESSAGES)
            logger.info(f'Changing status to: {status}')
            await self.change_presence(activity=discord.Game(status))
        except Exception as e:
            logger.error(f"Error changing status: {str(e)}")

    async def on_command(self, ctx):
        """Log when commands are used"""
        logger.info(f'Command "{ctx.command}" used by {ctx.author} in {ctx.guild}')

async def main():
    """Main function to run the bot"""
    logger.info("Starting bot...")
    async with Bot() as bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())