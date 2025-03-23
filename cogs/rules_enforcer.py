import discord
import re
import json
import os
import logging
import datetime
from discord.ext import commands
from discord import app_commands
from utils.embed_helpers import create_embed, create_error_embed, create_success_embed
from utils.permissions import PermissionChecks

logger = logging.getLogger('discord')

# Define the server rules with detection patterns
RULES = {
    1: {
        "name": "Illegal Content", 
        "description": "If it isn't legal irl, chances are the same applies here.",
        "patterns": [
            r"\bdrug(s)?\s+deal(ing|er|s)?",
            r"\billegal\s+(substance|content)",
            r"\bcp\b", 
            r"how\s+to\s+(make|create|build)\s+bomb"
        ],
        "severity": 3  # 1-3 scale, 3 being most severe
    },
    2: {
        "name": "Respect Beliefs",
        "description": "Do not go out of your way to make fun of others' beliefs.",
        "patterns": [
            r"(your|ur)\s+(religion|beliefs?)\s+(is|are)\s+(stupid|dumb|trash|garbage)",
            r"(imagine|lol|lmao)\s+believing\s+in",
            r"only\s+(idiots|morons)\s+believe"
        ],
        "severity": 2
    },
    3: {
        "name": "E-Dating",
        "description": "I don't really care if you e-date or whatever, just keep the shit outta chat please.",
        "patterns": [
            r"(i|we)\s+(love|miss)\s+you\s+baby",
            r"(i|we)\s+should\s+date",
            r"(be|are)\s+my\s+(e(-)?|online\s+)?(gf|bf|girlfriend|boyfriend)",
            r"dating\s+application"
        ],
        "severity": 1
    },
    4: {
        "name": "NSFW Content", 
        "description": "No nsfw outside of nsfw channels (explicit images).",
        "patterns": [
            r"(check|look\s+at)\s+this\s+(nude|naked|porn|hentai)",
            r"(send(ing)?|post(ing)?|sharing)\s+(nudes|porn)",
            r"(explicit|nsfw)\s+(image|content|picture)"
        ],
        "severity": 2,
        "exception": r"The\s+Plowed"  # Rule 4.5 exception
    },
    6: {
        "name": "Harassment",
        "description": "Don't be weird. Harassment, unsolicited nudes, etc.",
        "patterns": [
            r"(shut|stfu|fuck)\s+(up|off)",
            r"(kill|kys|die|neck)\s+(yourself|urself|u)",
            r"(you're|youre|ur)\s+(stupid|dumb|idiot|retard)",
            r"(go|get)\s+(away|lost)",
            r"(send|dm)\s+me\s+(nudes|pics)"
        ],
        "severity": 3
    },
    7: {
        "name": "Age Honesty",
        "description": "Please do not lie about your age.",
        "patterns": [
            r"(i('m|\s+am)|im)\s+(\d{2})\s+but\s+(actually|really)",
            r"(pretending|lying)\s+(to\s+be|about)\s+(\d{2})",
            r"(fake|false)\s+age"
        ],
        "severity": 3
    },
    # VC Rules (these will only apply in voice chat text channels)
    "vc1": {
        "name": "Voice Chat Spam",
        "description": "If you noise spam you'll be muted.",
        "vc_only": True,
        "patterns": [
            r"(spam(ming)?|loud)\s+(noise|mic|sound)",
            r"ear\s+rape"
        ],
        "severity": 2
    },
    "vc3": {
        "name": "Explicit VC Activity",
        "description": "Please do not do anything explicit in vc.",
        "vc_only": True,
        "patterns": [
            r"(doing|making)\s+(sex|porn|explicit)",
            r"(moaning|groaning)\s+(in|on)\s+(vc|voice|mic)",
            r"sexual\s+sounds"
        ],
        "severity": 3
    }
}

class RulesEnforcer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/rules_config.json"
        self.rule_violations = {}  # Track violations per user
        self.warned_messages = set()  # Track messages already warned for
        self.load_config()
        
        # Create vc channel detection
        self.vc_text_channels = [
            "voice-chat", "vc-text", "voice-text",
            "music-commands", "music-requests", "vc-chat"
        ]
        
    def load_config(self):
        """Load rule violations from config file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.rule_violations = config.get('rule_violations', {})
                    logger.info(f"Loaded rules enforcer config with {sum(len(v) for v in self.rule_violations.values())} rule violations")
            except Exception as e:
                logger.error(f"Error loading rules config: {str(e)}")
                self.rule_violations = {}
        else:
            logger.info("No rules config found, creating new one")
            self.save_config()
            
    def save_config(self):
        """Save current rule violations to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'rule_violations': self.rule_violations}, f, indent=4)
            logger.info("Saved rules enforcer configuration")
        except Exception as e:
            logger.error(f"Error saving rules config: {str(e)}")
            
    def is_vc_channel(self, channel_name):
        """Check if a channel is related to voice chat"""
        return any(vc_name in channel_name.lower() for vc_name in self.vc_text_channels)
        
    def check_rule_violation(self, message_content, channel_name):
        """Check if a message violates any rules"""
        message_content = message_content.lower()
        is_vc = self.is_vc_channel(channel_name)
        
        for rule_id, rule in RULES.items():
            # Skip VC rules if not in a VC channel
            if rule.get('vc_only', False) and not is_vc:
                continue
                
            # Check for rule exception first (e.g., "The Plowed" emote exception)
            if "exception" in rule and re.search(rule["exception"], message_content, re.IGNORECASE):
                continue
                
            # Check all patterns for this rule
            for pattern in rule["patterns"]:
                if re.search(pattern, message_content, re.IGNORECASE):
                    return rule_id, rule
                    
        return None, None
        
    def add_violation(self, user_id, guild_id, rule_id):
        """Add a rule violation to a user's record"""
        user_id = str(user_id)
        guild_id = str(guild_id)
        rule_id = str(rule_id)
        
        if guild_id not in self.rule_violations:
            self.rule_violations[guild_id] = {}
            
        if user_id not in self.rule_violations[guild_id]:
            self.rule_violations[guild_id][user_id] = []
            
        # Add violation with timestamp
        timestamp = datetime.datetime.utcnow().isoformat()
        self.rule_violations[guild_id][user_id].append({
            "rule_id": rule_id,
            "timestamp": timestamp
        })
        
        self.save_config()
        return len(self.rule_violations[guild_id][user_id])
    
    def get_recent_violations(self, user_id, guild_id, days=30):
        """Get recent rule violations for a user"""
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        if guild_id not in self.rule_violations or user_id not in self.rule_violations[guild_id]:
            return []
            
        # Filter violations within the past X days
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        recent = []
        
        for violation in self.rule_violations[guild_id][user_id]:
            try:
                violation_time = datetime.datetime.fromisoformat(violation["timestamp"])
                if violation_time >= cutoff:
                    recent.append(violation)
            except:
                # Handle any timestamp parsing errors
                recent.append(violation)
                
        return recent
        
    def reset_violations(self, user_id, guild_id):
        """Reset rule violations for a user"""
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        if guild_id in self.rule_violations and user_id in self.rule_violations[guild_id]:
            self.rule_violations[guild_id][user_id] = []
            self.save_config()
            return True
        return False
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Check messages for rule violations"""
        # Ignore messages from bots
        if message.author.bot:
            return
            
        # Ignore DMs
        if not isinstance(message.channel, discord.TextChannel):
            return
            
        # Check if message was already warned for
        if message.id in self.warned_messages:
            return
            
        # Check for rule violations
        rule_id, rule = self.check_rule_violation(message.content, message.channel.name)
        if rule_id and rule:
            logger.info(f"Rule violation detected - Rule {rule_id}: {rule['name']} by {message.author.name} in {message.guild.name}")
            
            # Add violation to user's record
            violation_count = self.add_violation(message.author.id, message.guild.id, rule_id)
            
            # Create warning embed
            embed = discord.Embed(
                title=f"⚠️ Rule Violation: {rule['name']}",
                description=f"Your message may violate server rule {rule_id}: {rule['description']}",
                color=discord.Color.yellow()
            )
            
            embed.add_field(name="Violation Count", value=f"This is violation #{violation_count} in the past 30 days", inline=False)
            embed.add_field(name="Severity", value=f"{'🟥' * rule['severity']}{'⬜' * (3 - rule['severity'])}", inline=False)
            
            # What happens at this severity?
            if rule['severity'] == 1:
                embed.add_field(name="Action", value="Warning only", inline=False)
            elif rule['severity'] == 2:
                embed.add_field(name="Action", value="Message may be removed", inline=False)
                # Consider deleting the message for severity 2+
                try:
                    if violation_count > 1:  # Only delete if repeated offense
                        await message.delete()
                        logger.info(f"Deleted message from {message.author.name} for rule violation")
                except:
                    logger.warning(f"Could not delete message from {message.author.name}")
            elif rule['severity'] == 3:
                embed.add_field(name="Action", value="Message removed and moderators notified", inline=False)
                # Always delete for severity 3
                try:
                    await message.delete()
                    logger.info(f"Deleted message from {message.author.name} for severe rule violation")
                except:
                    logger.warning(f"Could not delete message from {message.author.name}")
                
                # Notify mods for severity 3
                try:
                    mod_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                    if not mod_channel:
                        mod_channel = discord.utils.get(message.guild.text_channels, name="logs")
                        
                    if mod_channel:
                        mod_embed = discord.Embed(
                            title="🚨 Severe Rule Violation",
                            description=f"User {message.author.mention} violated rule {rule_id}",
                            color=discord.Color.red()
                        )
                        mod_embed.add_field(name="Rule", value=f"{rule['name']}: {rule['description']}", inline=False)
                        mod_embed.add_field(name="Message Content", value=message.content, inline=False)
                        mod_embed.add_field(name="Channel", value=message.channel.mention, inline=False)
                        mod_embed.add_field(name="Time", value=f"<t:{int(datetime.datetime.now().timestamp())}:F>", inline=False)
                        
                        await mod_channel.send(embed=mod_embed)
                except Exception as e:
                    logger.error(f"Error notifying mods: {str(e)}")
            
            # Mark this message as warned
            self.warned_messages.add(message.id)
            
            # Send warning to user via DM
            try:
                await message.author.send(embed=embed)
                logger.info(f"Sent rule violation warning to {message.author.name}")
            except:
                # If DM fails, warn in channel
                logger.warning(f"Could not DM {message.author.name}, sending warning in channel")
                try:
                    response = await message.channel.send(
                        f"{message.author.mention} Please review the server rules.", 
                        embed=embed,
                        delete_after=15
                    )
                except:
                    logger.error(f"Could not send warning to channel for {message.author.name}")
    
    @app_commands.command(name="violations", description="Check rule violations for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def check_violations(self, interaction: discord.Interaction, user: discord.Member):
        """Check rule violations for a user"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Get user's violations
        violations = self.get_recent_violations(user.id, interaction.guild.id)
        
        if not violations:
            await interaction.response.send_message(f"{user.display_name} has no rule violations in the past 30 days.", ephemeral=True)
            return
            
        # Create violations embed
        embed = discord.Embed(
            title=f"Rule Violations: {user.display_name}",
            description=f"Found {len(violations)} violations in the past 30 days",
            color=discord.Color.orange()
        )
        
        # Count violations by rule
        rule_counts = {}
        for v in violations:
            rule_id = v["rule_id"]
            if rule_id not in rule_counts:
                rule_counts[rule_id] = 0
            rule_counts[rule_id] += 1
            
        # Add fields for each rule violation
        for rule_id, count in rule_counts.items():
            rule_info = RULES.get(int(rule_id) if rule_id.isdigit() else rule_id, {"name": "Unknown Rule", "description": "Rule details not found"})
            embed.add_field(
                name=f"Rule {rule_id}: {rule_info['name']} ({count})",
                value=rule_info["description"],
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="resetviolations", description="Reset rule violations for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def reset_user_violations(self, interaction: discord.Interaction, user: discord.Member):
        """Reset rule violations for a user"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Reset violations
        if self.reset_violations(user.id, interaction.guild.id):
            await interaction.response.send_message(f"Reset rule violations for {user.mention}.", ephemeral=False)
            logger.info(f"User {interaction.user.name} reset rule violations for {user.name} in {interaction.guild.name}")
        else:
            await interaction.response.send_message(f"{user.display_name} has no rule violations to reset.", ephemeral=True)
            
    @commands.command(name="violations")
    @commands.has_permissions(manage_messages=True)
    async def check_violations_prefix(self, ctx, user: discord.Member):
        """Check rule violations for a user (prefix command)"""
        # Get user's violations
        violations = self.get_recent_violations(user.id, ctx.guild.id)
        
        if not violations:
            await ctx.send(f"{user.display_name} has no rule violations in the past 30 days.")
            return
            
        # Create violations embed
        embed = discord.Embed(
            title=f"Rule Violations: {user.display_name}",
            description=f"Found {len(violations)} violations in the past 30 days",
            color=discord.Color.orange()
        )
        
        # Count violations by rule
        rule_counts = {}
        for v in violations:
            rule_id = v["rule_id"]
            if rule_id not in rule_counts:
                rule_counts[rule_id] = 0
            rule_counts[rule_id] += 1
            
        # Add fields for each rule violation
        for rule_id, count in rule_counts.items():
            rule_info = RULES.get(int(rule_id) if rule_id.isdigit() else rule_id, {"name": "Unknown Rule", "description": "Rule details not found"})
            embed.add_field(
                name=f"Rule {rule_id}: {rule_info['name']} ({count})",
                value=rule_info["description"],
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.command(name="resetviolations")
    @commands.has_permissions(manage_messages=True)
    async def reset_violations_prefix(self, ctx, user: discord.Member):
        """Reset rule violations for a user (prefix command)"""
        # Reset violations
        if self.reset_violations(user.id, ctx.guild.id):
            await ctx.send(f"Reset rule violations for {user.mention}.")
            logger.info(f"User {ctx.author.name} reset rule violations for {user.name} in {ctx.guild.name}")
        else:
            await ctx.send(f"{user.display_name} has no rule violations to reset.")
            
    @app_commands.command(name="rules", description="Display server rules")
    async def show_rules(self, interaction: discord.Interaction):
        """Display the server rules"""
        embed = discord.Embed(
            title="Soda's Server Rules",
            description="Please follow these rules to keep our server a friendly place:",
            color=discord.Color.blue()
        )
        
        # Add regular rules
        for i in range(1, 9):
            if i in RULES:
                rule = RULES[i]
                embed.add_field(
                    name=f"Rule {i}: {rule['name']}",
                    value=rule['description'],
                    inline=False
                )
                
        # Add VC rules section
        embed.add_field(name="Voice Chat Rules", value="Rules for voice chat channels:", inline=False)
        
        # Add VC rules
        for rule_id, rule in RULES.items():
            if isinstance(rule_id, str) and rule_id.startswith("vc"):
                embed.add_field(
                    name=f"VC Rule {rule_id[2:]}: {rule['name']}",
                    value=rule['description'],
                    inline=False
                )
                
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(RulesEnforcer(bot))
    logger.info("Rules enforcer cog loaded")