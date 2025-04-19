from discord import Member
from discord.ext import commands
from config import BOT_OWNER_IDS, MOD_ROLE_IDS
import logging

logger = logging.getLogger('discord')

def is_bot_owner(user_id: int) -> bool:
    """Check if a user is the bot owner"""
    result = user_id in BOT_OWNER_IDS
    logger.debug(f"Checking bot owner: user_id={user_id}, owner_ids={BOT_OWNER_IDS}, result={result}")
    return result

def is_mod(member) -> bool:
    """Check if a member has a moderator role"""
    # Handle both Member objects and Interaction objects
    if hasattr(member, 'roles'):
        # It's a Member object
        has_mod_role = any(role.id in MOD_ROLE_IDS for role in member.roles)
        logger.debug(f"Checking mod status for {member.name}: roles={[role.id for role in member.roles]}, is_mod={has_mod_role}")
        return has_mod_role
    elif hasattr(member, 'user') and hasattr(member, 'guild'):
        # It's an Interaction object, try to get member from guild
        try:
            guild_member = member.guild.get_member(member.user.id)
            if guild_member:
                return is_mod(guild_member)
        except:
            pass
    
    # Default to False if we can't determine mod status
    return False

def is_admin(member) -> bool:
    """Check if a member has administrator permissions"""
    # Handle both Member objects and Interaction objects
    if hasattr(member, 'guild_permissions'):
        # It's a Member object
        return member.guild_permissions.administrator
    elif hasattr(member, 'user') and hasattr(member, 'guild'):
        # It's an Interaction object, get member from it
        return member.user.guild_permissions.administrator if hasattr(member.user, 'guild_permissions') else False
    elif hasattr(member, 'guild') and hasattr(member, 'guild_permissions'):
        # It's a User object with guild_permissions
        return member.guild_permissions.administrator
    else:
        # Unknown object type, default to False
        return False

class PermissionChecks:
    @staticmethod
    def is_owner():
        """Check if the command user is the bot owner"""
        async def predicate(ctx):
            is_owner = is_bot_owner(ctx.author.id)
            logger.info(f"Owner command attempted by {ctx.author} (ID: {ctx.author.id}): {'✅ Allowed' if is_owner else '❌ Denied'}")
            return is_owner
        return commands.check(predicate)

    @staticmethod
    def is_mod():
        """Check if the command user is a moderator or higher"""
        async def predicate(ctx):
            is_owner_result = is_bot_owner(ctx.author.id)
            is_mod_result = is_mod(ctx.author)
            is_admin_result = is_admin(ctx.author)
            has_permission = is_owner_result or is_mod_result or is_admin_result

            logger.info(
                f"Mod command attempted by {ctx.author} (ID: {ctx.author.id}): "
                f"{'✅ Allowed' if has_permission else '❌ Denied'} "
                f"(Owner: {is_owner_result}, Mod: {is_mod_result}, Admin: {is_admin_result})"
            )
            return has_permission
        return commands.check(predicate)
        
    @staticmethod
    def slash_is_owner():
        """Check if the slash command user is the bot owner (for app_commands)"""
        async def predicate(interaction):
            is_owner = is_bot_owner(interaction.user.id)
            logger.info(f"Owner slash command attempted by {interaction.user} (ID: {interaction.user.id}): {'✅ Allowed' if is_owner else '❌ Denied'}")
            return is_owner
        return predicate
        
    @staticmethod
    def slash_is_mod():
        """Check if the slash command user is a moderator or higher (for app_commands)"""
        async def predicate(interaction):
            is_owner_result = is_bot_owner(interaction.user.id)
            is_mod_result = is_mod(interaction.user)
            is_admin_result = is_admin(interaction.user)
            has_permission = is_owner_result or is_mod_result or is_admin_result

            logger.info(
                f"Mod slash command attempted by {interaction.user} (ID: {interaction.user.id}): "
                f"{'✅ Allowed' if has_permission else '❌ Denied'} "
                f"(Owner: {is_owner_result}, Mod: {is_mod_result}, Admin: {is_admin_result})"
            )
            return has_permission
        return predicate
        
    @staticmethod
    def slash_is_admin():
        """Check if the slash command user has administrator permissions (for app_commands)"""
        async def predicate(interaction):
            is_owner_result = is_bot_owner(interaction.user.id)
            is_admin_result = is_admin(interaction.user)
            has_permission = is_owner_result or is_admin_result

            logger.info(
                f"Admin slash command attempted by {interaction.user} (ID: {interaction.user.id}): "
                f"{'✅ Allowed' if has_permission else '❌ Denied'} "
                f"(Owner: {is_owner_result}, Admin: {is_admin_result})"
            )
            return has_permission
        return predicate