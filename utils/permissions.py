from discord import Member
from discord.ext import commands
from config import BOT_OWNER_ID, MOD_ROLE_IDS

def is_bot_owner(user_id: int) -> bool:
    """Check if a user is the bot owner"""
    return user_id == BOT_OWNER_ID

def is_mod(member: Member) -> bool:
    """Check if a member has a moderator role"""
    return any(role.id in MOD_ROLE_IDS for role in member.roles)

def is_admin(member: Member) -> bool:
    """Check if a member has administrator permissions"""
    return member.guild_permissions.administrator

class PermissionChecks:
    @staticmethod
    def is_owner():
        """Check if the command user is the bot owner"""
        async def predicate(ctx):
            return is_bot_owner(ctx.author.id)
        return commands.check(predicate)

    @staticmethod
    def is_mod():
        """Check if the command user is a moderator or higher"""
        async def predicate(ctx):
            return (is_bot_owner(ctx.author.id) or 
                   is_mod(ctx.author) or 
                   is_admin(ctx.author))
        return commands.check(predicate)
