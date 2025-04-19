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


