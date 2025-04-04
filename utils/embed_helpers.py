import discord
from config import COLORS

def create_embed(title, description, color=COLORS["PRIMARY"]):
    """Create a styled Discord embed"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    return embed

def create_error_embed(title, description):
    """Create an error-styled Discord embed"""
    return create_embed(title, description, COLORS["ERROR"])

def create_success_embed(title, description):
    """Create a success-styled Discord embed"""
    return create_embed(title, description, COLORS["SUCCESS"])

def create_scp079_embed(title, description):
    """Create an SCP-079-styled Discord embed with the appropriate color"""
    embed = create_embed(title, description, COLORS["SCP079"])
    
    # Add a unique footer with an ASCII representation of SCP-079
    ascii_art = "■█■\n█▀█"  # Simple representation of a computer screen
    embed.set_footer(text=f"{ascii_art} | Item #: SCP-079 | Object Class: Euclid")
    
    return embed
