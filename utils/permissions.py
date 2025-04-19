from discord import Member
from discord.ext import commands
from config import BOT_OWNER_IDS, MOD_ROLE_IDS
import logging

logger = logging.getLogger('discord')

# Custom exception class for permission errors
class PermissionError(commands.CheckFailure):
    """Exception raised when a permission check fails and has already been handled with a response."""
    def __init__(self, message="Permission check failed and was already handled"):
        self.message = message
        super().__init__(self.message)

def is_bot_owner(user_id: int) -> bool:
    """Check if a user is the bot owner"""
    # Ensure user_id is an integer (Discord API can sometimes return IDs as strings)
    if not isinstance(user_id, int):
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user_id type for owner check: {type(user_id)} - {user_id}")
            return False
    
    # Explicitly check each owner ID to ensure proper type comparison
    for owner_id in BOT_OWNER_IDS:
        # Convert owner_id to int if it's not already
        owner_id_int = owner_id if isinstance(owner_id, int) else int(owner_id)
        if user_id == owner_id_int:
            logger.info(f"Owner check passed: user_id={user_id}, matched={owner_id_int}")
            return True
    
    logger.info(f"Owner check failed: user_id={user_id}, owner_ids={BOT_OWNER_IDS}")
    return False

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
            
            # If not owner, send error message
            if not is_owner:
                # Try to respond if interaction hasn't been responded to yet
                if not interaction.response.is_done():
                    try:
                        from discord import Embed
                        await interaction.response.send_message(
                            embed=Embed(
                                title="Access Denied",
                                description="You don't have permission to use this command. Only the bot owner can use it.",
                                color=0xFF0000
                            ),
                            ephemeral=True
                        )
                        logger.info(f"Sent owner-only access denied message to {interaction.user.id}")
                    except Exception as e:
                        logger.error(f"Error sending permission denied message: {e}")
                
                # Raise our custom exception to signal that we've already handled the error response
                raise PermissionError(f"User {interaction.user.id} is not the bot owner")
                
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
            
            # If permission check fails, send error message and raise our custom exception
            if not has_permission:
                # Try to respond if interaction hasn't been responded to yet
                if not interaction.response.is_done():
                    try:
                        from discord import Embed
                        await interaction.response.send_message(
                            embed=Embed(
                                title="Access Denied",
                                description="You don't have permission to use this command. Only moderators or higher can use it.",
                                color=0xFF0000
                            ),
                            ephemeral=True
                        )
                        logger.info(f"Sent mod-only access denied message to {interaction.user.id}")
                    except Exception as e:
                        logger.error(f"Error sending permission denied message: {e}")
                
                # Raise our custom exception to signal that we've already handled the error response
                raise PermissionError(f"User {interaction.user.id} is not a moderator")
                
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