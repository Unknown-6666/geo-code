import asyncio
import discord
import json
import random
import string
from datetime import datetime, timedelta
from discord import app_commands, utils, Interaction, ButtonStyle
from discord.ext import commands
from discord.ui import Button, View
from typing import Dict, List, Optional, Union, Literal

from app import db
from models.verification import VerificationSetting, VerificationLog

# Simple captcha generation function (using text and basic math)
def generate_captcha():
    """Generate a simple captcha with question and answer"""
    captcha_type = random.choice(["simple_math", "character_count", "reverse_word"])
    
    if captcha_type == "simple_math":
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operator = random.choice(["+", "-", "*"])
        
        if operator == "+":
            answer = num1 + num2
        elif operator == "-":
            # Ensure positive result
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
        else:  # multiplication
            # Keep it simpler for multiplication
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            answer = num1 * num2
            
        question = f"What is {num1} {operator} {num2}?"
        answer = str(answer)
        
    elif captcha_type == "character_count":
        word = random.choice(["verification", "discord", "security", "community", "authenticate", "captcha"])
        question = f"How many characters are in the word '{word}'?"
        answer = str(len(word))
        
    else:  # reverse_word
        word = random.choice(["bot", "chat", "game", "role", "text", "code"])
        question = f"Spell the word '{word}' backwards:"
        answer = word[::-1]
        
    return {"question": question, "answer": answer}


# Main verification view with buttons
class VerificationView(View):
    def __init__(self, cog, user_id, guild_id):
        super().__init__(timeout=None)  # No timeout for verification
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id

    @discord.ui.button(label="Start Verification", style=ButtonStyle.primary, custom_id="start_verification")
    async def start_verification(self, interaction: Interaction, button: Button):
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This verification is not for you.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        # Start the verification process
        await self.cog.start_user_verification(interaction, self.guild_id)


# Captcha verification view
class CaptchaView(View):
    def __init__(self, cog, verification_log, captcha_data):
        super().__init__(timeout=300)  # 5 minutes to complete the captcha
        self.cog = cog
        self.verification_log = verification_log
        self.captcha_data = captcha_data
        self.answer = captcha_data["answer"]
    
    @discord.ui.button(label="Refresh Captcha", style=ButtonStyle.secondary, custom_id="refresh_captcha")
    async def refresh_captcha(self, interaction: Interaction, button: Button):
        # Generate a new captcha
        self.captcha_data = generate_captcha()
        self.answer = self.captcha_data["answer"]
        
        # Send the new captcha
        await interaction.response.send_message(
            f"**New Captcha**: {self.captcha_data['question']}\n"
            "Please use the Submit button with your answer.",
            ephemeral=True
        )
    
    @discord.ui.button(label="Submit Answer", style=ButtonStyle.primary, custom_id="submit_captcha")
    async def submit_captcha(self, interaction: Interaction, button: Button):
        # Create a modal for user to submit answer
        modal = CaptchaModal(self.cog, self.verification_log, self.captcha_data)
        await interaction.response.send_modal(modal)


# Modal for captcha submission
class CaptchaModal(discord.ui.Modal):
    def __init__(self, cog, verification_log, captcha_data):
        super().__init__(title="Captcha Verification")
        self.cog = cog
        self.verification_log = verification_log
        self.captcha_data = captcha_data
        self.answer = captcha_data["answer"]
        
        # Add the captcha question as a label
        self.add_item(
            discord.ui.TextInput(
                label=captcha_data["question"],
                placeholder="Enter your answer here",
                required=True,
                max_length=100
            )
        )
    
    async def on_submit(self, interaction: Interaction):
        user_answer = self.children[0].value.strip().lower()
        correct_answer = self.answer.lower()
        
        # Update attempt count
        self.verification_log.captcha_attempts += 1
        db.session.commit()
        
        if user_answer == correct_answer:
            # Mark captcha as completed
            self.verification_log.captcha_completed = True
            db.session.commit()
            
            await interaction.response.send_message(
                "✅ Captcha verification successful! Moving to the next step...",
                ephemeral=True
            )
            
            # Continue verification process
            await self.cog.continue_verification(interaction, self.verification_log)
        else:
            # Check if too many attempts
            if self.verification_log.captcha_attempts >= 3:
                self.verification_log.success = False
                self.verification_log.failure_reason = "Too many failed captcha attempts"
                self.verification_log.completed_at = datetime.utcnow()
                db.session.commit()
                
                await interaction.response.send_message(
                    "❌ You've made too many incorrect attempts. Please contact a server moderator for assistance.",
                    ephemeral=True
                )
            else:
                # Allow retry
                await interaction.response.send_message(
                    f"❌ Incorrect answer. You have {3 - self.verification_log.captcha_attempts} attempts remaining.\n"
                    f"Please try again with the captcha: {self.captcha_data['question']}",
                    ephemeral=True,
                    view=CaptchaView(self.cog, self.verification_log, self.captcha_data)
                )


# Custom questions view
class QuestionsView(View):
    def __init__(self, cog, verification_log, questions):
        super().__init__(timeout=600)  # 10 minutes to answer questions
        self.cog = cog
        self.verification_log = verification_log
        self.questions = questions
    
    @discord.ui.button(label="Answer Questions", style=ButtonStyle.primary, custom_id="answer_questions")
    async def answer_questions(self, interaction: Interaction, button: Button):
        # Create a modal for user to answer questions
        modal = QuestionsModal(self.cog, self.verification_log, self.questions)
        await interaction.response.send_modal(modal)


# Modal for custom questions
class QuestionsModal(discord.ui.Modal):
    def __init__(self, cog, verification_log, questions):
        super().__init__(title="Server Verification Questions")
        self.cog = cog
        self.verification_log = verification_log
        self.questions = questions
        
        # Add up to 5 questions (Discord modal limit)
        for i, q in enumerate(questions[:5]):
            self.add_item(
                discord.ui.TextInput(
                    label=q["question"][:45],  # Discord limits label length
                    placeholder="Enter your answer here",
                    required=True,
                    max_length=100
                )
            )
    
    async def on_submit(self, interaction: Interaction):
        # Update attempt count
        self.verification_log.questions_attempts += 1
        db.session.commit()
        
        # Check answers
        all_correct = True
        incorrect_questions = []
        
        for i, child in enumerate(self.children):
            user_answer = child.value.strip().lower()
            correct_answers = [a.lower() for a in self.questions[i]["answers"]]
            
            if not any(user_answer == answer for answer in correct_answers):
                all_correct = False
                incorrect_questions.append(self.questions[i]["question"])
        
        if all_correct:
            # Mark questions as completed
            self.verification_log.questions_completed = True
            db.session.commit()
            
            await interaction.response.send_message(
                "✅ All questions answered correctly! Moving to the next step...",
                ephemeral=True
            )
            
            # Continue verification process
            await self.cog.continue_verification(interaction, self.verification_log)
        else:
            # Check if too many attempts
            if self.verification_log.questions_attempts >= 3:
                self.verification_log.success = False
                self.verification_log.failure_reason = "Too many failed question attempts"
                self.verification_log.completed_at = datetime.utcnow()
                db.session.commit()
                
                await interaction.response.send_message(
                    "❌ You've made too many incorrect attempts. Please contact a server moderator for assistance.",
                    ephemeral=True
                )
            else:
                # Allow retry
                await interaction.response.send_message(
                    f"❌ Some answers were incorrect. You have {3 - self.verification_log.questions_attempts} attempts remaining.\n"
                    f"Please try again with the questions.",
                    ephemeral=True,
                    view=QuestionsView(self.cog, self.verification_log, self.questions)
                )


# Role acceptance view
class RoleAcceptView(View):
    def __init__(self, cog, verification_log):
        super().__init__(timeout=600)  # 10 minutes to accept roles
        self.cog = cog
        self.verification_log = verification_log
    
    @discord.ui.button(label="I Accept the Rules", style=ButtonStyle.success, custom_id="accept_rules")
    async def accept_rules(self, interaction: Interaction, button: Button):
        # Mark role acceptance as completed
        self.verification_log.role_accept_completed = True
        db.session.commit()
        
        await interaction.response.send_message(
            "✅ You've accepted the server rules. Moving to the next step...",
            ephemeral=True
        )
        
        # Continue verification process
        await self.cog.continue_verification(interaction, self.verification_log)
    
    @discord.ui.button(label="Decline", style=ButtonStyle.danger, custom_id="decline_rules")
    async def decline_rules(self, interaction: Interaction, button: Button):
        # Mark verification as failed
        self.verification_log.success = False
        self.verification_log.failure_reason = "User declined rules"
        self.verification_log.completed_at = datetime.utcnow()
        db.session.commit()
        
        await interaction.response.send_message(
            "You've declined the server rules and cannot proceed with verification.",
            ephemeral=True
        )


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache for active verification sessions
        self.active_verifications = {}
    
    def cog_unload(self):
        # Cleanup resources when cog is unloaded
        self.active_verifications.clear()
    
    def get_welcome_message(self, guild):
        """Get the default welcome message for a guild"""
        return (
            f"👋 Welcome to **{guild.name}**!\n\n"
            f"To gain access to the server, you need to complete the verification process.\n"
            f"This helps us maintain a safe and secure community."
        )
    
    async def get_verification_settings(self, guild_id: str) -> Optional[VerificationSetting]:
        """Get or create verification settings for a guild"""
        from app import app
        
        with app.app_context():
            settings = db.session.query(VerificationSetting).filter_by(guild_id=guild_id).first()
            
            if not settings:
                # Create default settings
                settings = VerificationSetting(guild_id=guild_id)
                db.session.add(settings)
                db.session.commit()
                
            return settings
    
    async def create_verification_log(self, user_id: str, guild_id: str, setting_id: int) -> VerificationLog:
        """Create a new verification log entry"""
        from app import app
        
        with app.app_context():
            log = VerificationLog(
                user_id=user_id,
                guild_id=guild_id,
                setting_id=setting_id
            )
            db.session.add(log)
            db.session.commit()
            return log
    
    async def start_user_verification(self, interaction: Interaction, guild_id: str):
        """Start the verification process for a user"""
        user_id = str(interaction.user.id)
        
        # Get verification settings
        settings = await self.get_verification_settings(guild_id)
        
        # Check if any verification is required
        if not any([
            settings.require_captcha,
            settings.require_questions,
            settings.require_role_accept,
            settings.require_account_age
        ]):
            await interaction.followup.send(
                "No verification is required for this server. You are already verified!",
                ephemeral=True
            )
            return
        
        # Check account age if required
        if settings.require_account_age and settings.min_account_age_days > 0:
            account_age = (datetime.utcnow() - interaction.user.created_at).days
            if account_age < settings.min_account_age_days:
                await interaction.followup.send(
                    f"Your Discord account must be at least {settings.min_account_age_days} days old to join this server. "
                    f"Your account is {account_age} days old.",
                    ephemeral=True
                )
                return
        
        # Create verification log
        verification_log = await self.create_verification_log(user_id, guild_id, settings.id)
        
        # Cache this verification session
        self.active_verifications[f"{user_id}_{guild_id}"] = verification_log.id
        
        # Start the verification process
        await self.continue_verification(interaction, verification_log)
    
    async def continue_verification(self, interaction: Interaction, verification_log: VerificationLog):
        """Continue the verification process from where the user left off"""
        # Get verification settings
        settings = await self.get_verification_settings(verification_log.guild_id)
        
        # Check if verification is already completed
        if verification_log.success is not None:
            if verification_log.success:
                await interaction.followup.send(
                    "You have already completed verification!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Your verification has failed: {verification_log.failure_reason}\n"
                    "Please contact a server moderator for assistance.",
                    ephemeral=True
                )
            return
        
        # Determine which verification step to show next
        if settings.require_captcha and not verification_log.captcha_completed:
            # Show captcha verification
            captcha_data = generate_captcha()
            await interaction.followup.send(
                f"**Captcha Verification**\n{captcha_data['question']}",
                ephemeral=True,
                view=CaptchaView(self, verification_log, captcha_data)
            )
            return
            
        if settings.require_questions and not verification_log.questions_completed:
            # Show custom questions
            if not settings.custom_questions:
                # No questions configured, mark as completed
                verification_log.questions_completed = True
                db.session.commit()
            else:
                questions = settings.custom_questions
                await interaction.followup.send(
                    "**Server Verification Questions**\n"
                    "Please answer the following questions to verify yourself:",
                    ephemeral=True,
                    view=QuestionsView(self, verification_log, questions)
                )
                return
        
        if settings.require_role_accept and not verification_log.role_accept_completed:
            # Show role acceptance
            guild = self.bot.get_guild(int(verification_log.guild_id))
            
            # Create rules message
            rules_message = "**Server Rules**\n\n"
            
            # Try to find rules channel
            rules_channel = None
            for channel in guild.channels:
                if "rule" in channel.name.lower() and channel.permissions_for(guild.me).read_messages:
                    rules_channel = channel
                    break
            
            if rules_channel:
                rules_message += f"Please read the rules in {rules_channel.mention} before accepting.\n\n"
            
            rules_message += (
                "By accepting, you agree to follow all server rules and understand that "
                "breaking these rules may result in warnings or bans."
            )
            
            await interaction.followup.send(
                rules_message,
                ephemeral=True,
                view=RoleAcceptView(self, verification_log)
            )
            return
        
        # If we got here, all verification steps are complete
        await self.complete_verification(interaction, verification_log)
    
    async def complete_verification(self, interaction: Interaction, verification_log: VerificationLog):
        """Complete the verification process"""
        from app import app
        
        with app.app_context():
            # Mark verification as successful
            verification_log.success = True
            verification_log.completed_at = datetime.utcnow()
            
            # Update settings stats
            settings = await self.get_verification_settings(verification_log.guild_id)
            settings.successful_verifications += 1
            
            db.session.commit()
        
        # Get the guild and user
        guild = self.bot.get_guild(int(verification_log.guild_id))
        member = guild.get_member(int(verification_log.user_id))
        
        if not member:
            # User left the server during verification
            await interaction.followup.send(
                "You appear to have left the server during verification.",
                ephemeral=True
            )
            return
        
        # Assign verified role if configured
        if settings.verified_role_id:
            try:
                role = guild.get_role(int(settings.verified_role_id))
                if role:
                    await member.add_roles(role, reason="Completed verification")
            except Exception as e:
                print(f"Error assigning verified role: {e}")
        
        # Send completion message to user
        await interaction.followup.send(
            "🎉 **Verification Complete!** 🎉\n\n"
            f"You now have access to {guild.name}. Welcome to the community!",
            ephemeral=True
        )
        
        # Send welcome message if configured
        if settings.welcome_channel_id and settings.welcome_message:
            try:
                channel = guild.get_channel(int(settings.welcome_channel_id))
                if channel:
                    welcome_msg = settings.welcome_message.replace("{user}", member.mention)
                    await channel.send(welcome_msg)
            except Exception as e:
                print(f"Error sending welcome message: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Trigger verification when a new member joins"""
        # Skip bots
        if member.bot:
            return
            
        guild_id = str(member.guild.id)
        
        # Get verification settings
        settings = await self.get_verification_settings(guild_id)
        
        # Skip if no verification required
        if not any([
            settings.require_captcha,
            settings.require_questions,
            settings.require_role_accept,
            settings.require_account_age
        ]):
            return
        
        # Check account age if required
        if settings.require_account_age and settings.min_account_age_days > 0:
            account_age = (datetime.utcnow() - member.created_at).days
            if account_age < settings.min_account_age_days:
                try:
                    await member.send(
                        f"Your Discord account must be at least {settings.min_account_age_days} days old to join {member.guild.name}. "
                        f"Your account is {account_age} days old."
                    )
                except:
                    pass
                    
                # Kick the member with appropriate reason
                try:
                    await member.guild.kick(
                        member, 
                        reason=f"Account too new: {account_age} days old (minimum: {settings.min_account_age_days} days)"
                    )
                except:
                    pass
                return
        
        # Create verification channel if configured
        verification_channel = None
        if settings.verification_channel_id:
            verification_channel = member.guild.get_channel(int(settings.verification_channel_id))
        
        # Send DM to user with verification instructions
        try:
            guild = member.guild
            welcome_msg = self.get_welcome_message(guild)
            
            view = VerificationView(self, str(member.id), guild_id)
            
            await member.send(
                welcome_msg,
                view=view
            )
            
            # If there's a verification channel, mention the user there
            if verification_channel:
                await verification_channel.send(
                    f"{member.mention} Please check your DMs for verification instructions. "
                    f"If you didn't receive a DM, make sure your privacy settings allow messages from server members."
                )
                
        except discord.Forbidden:
            # Cannot DM the user
            if verification_channel:
                await verification_channel.send(
                    f"{member.mention} I couldn't send you a DM with verification instructions. "
                    f"Please enable DMs from server members and try again by leaving and rejoining the server."
                )

    # === ADMIN COMMANDS ===
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.command(name="setup_verification", description="Set up the verification system for your server")
    async def setup_verification(self, interaction: Interaction):
        """Set up the verification system for your server"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        
        # Get current settings
        settings = await self.get_verification_settings(guild_id)
        
        # Create setup message
        setup_message = (
            "**Verification System Setup**\n\n"
            "Use the following commands to configure verification:\n\n"
            "`/verification toggle captcha` - Require captcha verification\n"
            "`/verification toggle questions` - Require custom questions\n"
            "`/verification toggle role_accept` - Require users to accept rules\n"
            "`/verification toggle account_age` - Require minimum account age\n\n"
            "`/verification set min_age <days>` - Set minimum account age\n"
            "`/verification set verification_channel <channel>` - Set verification channel\n"
            "`/verification set verified_role <role>` - Set role to assign after verification\n"
            "`/verification set welcome_channel <channel>` - Set channel for welcome messages\n"
            "`/verification set welcome_message <message>` - Set welcome message (use {user} for mention)\n\n"
            "`/verification add_question <question> <answer1,answer2,...>` - Add a custom question\n"
            "`/verification remove_question <index>` - Remove a custom question\n"
            "`/verification list_questions` - List all custom questions\n\n"
            "`/verification status` - Show current verification settings\n\n"
            "**Current Status:**\n"
        )
        
        # Add current settings to the message
        setup_message += f"Captcha verification: {'✅' if settings.require_captcha else '❌'}\n"
        setup_message += f"Custom questions: {'✅' if settings.require_questions else '❌'}\n"
        setup_message += f"Role acceptance: {'✅' if settings.require_role_accept else '❌'}\n"
        setup_message += f"Account age check: {'✅' if settings.require_account_age else '❌'}\n"
        
        if settings.require_account_age:
            setup_message += f"Minimum account age: {settings.min_account_age_days} days\n"
        
        if settings.verification_channel_id:
            channel = interaction.guild.get_channel(int(settings.verification_channel_id))
            setup_message += f"Verification channel: {channel.mention if channel else 'Invalid channel'}\n"
        
        if settings.verified_role_id:
            role = interaction.guild.get_role(int(settings.verified_role_id))
            setup_message += f"Verified role: {role.mention if role else 'Invalid role'}\n"
        
        if settings.welcome_channel_id:
            channel = interaction.guild.get_channel(int(settings.welcome_channel_id))
            setup_message += f"Welcome channel: {channel.mention if channel else 'Invalid channel'}\n"
        
        if settings.custom_questions:
            setup_message += f"Custom questions: {len(settings.custom_questions)} configured\n"
        
        await interaction.followup.send(setup_message, ephemeral=True)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.command(name="verification", description="Configure the verification system")
    @app_commands.describe(
        action="The action to perform",
        setting="The setting to modify",
        value="The value to set",
        index="The index of the question to remove (starting at 1)",
        channel="The channel to set",
        role="The role to set",
        message="The message to set"
    )
    async def verification_command(
        self, 
        interaction: Interaction,
        action: Literal["toggle", "set", "add_question", "remove_question", "list_questions", "status"],
        setting: Optional[Literal["captcha", "questions", "role_accept", "account_age", "min_age", 
                                "verification_channel", "verified_role", "welcome_channel", "welcome_message"]] = None,
        value: Optional[str] = None,
        index: Optional[int] = None,
        channel: Optional[discord.TextChannel] = None,
        role: Optional[discord.Role] = None,
        message: Optional[str] = None
    ):
        """Configure the verification system"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        
        # Get current settings
        settings = await self.get_verification_settings(guild_id)
        
        if action == "toggle":
            if not setting:
                await interaction.followup.send("Please specify a setting to toggle.", ephemeral=True)
                return
                
            if setting == "captcha":
                settings.require_captcha = not settings.require_captcha
                toggle_status = "enabled" if settings.require_captcha else "disabled"
                await interaction.followup.send(f"Captcha verification {toggle_status}.", ephemeral=True)
                
            elif setting == "questions":
                settings.require_questions = not settings.require_questions
                toggle_status = "enabled" if settings.require_questions else "disabled"
                await interaction.followup.send(f"Custom questions {toggle_status}.", ephemeral=True)
                
            elif setting == "role_accept":
                settings.require_role_accept = not settings.require_role_accept
                toggle_status = "enabled" if settings.require_role_accept else "disabled"
                await interaction.followup.send(f"Role acceptance {toggle_status}.", ephemeral=True)
                
            elif setting == "account_age":
                settings.require_account_age = not settings.require_account_age
                toggle_status = "enabled" if settings.require_account_age else "disabled"
                await interaction.followup.send(f"Account age check {toggle_status}.", ephemeral=True)
                
            else:
                await interaction.followup.send(f"Unknown setting: {setting}", ephemeral=True)
                return
                
            db.session.commit()
            
        elif action == "set":
            if not setting:
                await interaction.followup.send("Please specify a setting to set.", ephemeral=True)
                return
                
            if setting == "min_age":
                if not value:
                    await interaction.followup.send("Please specify a minimum age in days.", ephemeral=True)
                    return
                    
                try:
                    min_age = int(value)
                    if min_age < 0:
                        await interaction.followup.send("Minimum age must be a positive number.", ephemeral=True)
                        return
                        
                    settings.min_account_age_days = min_age
                    db.session.commit()
                    await interaction.followup.send(f"Minimum account age set to {min_age} days.", ephemeral=True)
                except ValueError:
                    await interaction.followup.send("Please provide a valid number for minimum age.", ephemeral=True)
                    
            elif setting == "verification_channel":
                if not channel:
                    await interaction.followup.send("Please specify a channel.", ephemeral=True)
                    return
                    
                settings.verification_channel_id = str(channel.id)
                db.session.commit()
                await interaction.followup.send(f"Verification channel set to {channel.mention}.", ephemeral=True)
                
            elif setting == "verified_role":
                if not role:
                    await interaction.followup.send("Please specify a role.", ephemeral=True)
                    return
                    
                settings.verified_role_id = str(role.id)
                db.session.commit()
                await interaction.followup.send(f"Verified role set to {role.mention}.", ephemeral=True)
                
            elif setting == "welcome_channel":
                if not channel:
                    await interaction.followup.send("Please specify a channel.", ephemeral=True)
                    return
                    
                settings.welcome_channel_id = str(channel.id)
                db.session.commit()
                await interaction.followup.send(f"Welcome channel set to {channel.mention}.", ephemeral=True)
                
            elif setting == "welcome_message":
                if not message:
                    await interaction.followup.send("Please specify a welcome message.", ephemeral=True)
                    return
                    
                settings.welcome_message = message
                db.session.commit()
                
                # Preview the message
                preview = message.replace("{user}", interaction.user.mention)
                await interaction.followup.send(
                    f"Welcome message set to:\n\n{preview}\n\n"
                    f"Use {{user}} to mention the new member.",
                    ephemeral=True
                )
                
            else:
                await interaction.followup.send(f"Unknown setting: {setting}", ephemeral=True)
                
        elif action == "add_question":
            if not value:
                await interaction.followup.send(
                    "Please specify a question and answers in the format: `question|answer1,answer2,...`", 
                    ephemeral=True
                )
                return
                
            # Split into question and answers
            parts = value.split('|')
            if len(parts) != 2:
                await interaction.followup.send(
                    "Invalid format. Use: `question|answer1,answer2,...`", 
                    ephemeral=True
                )
                return
                
            question = parts[0].strip()
            answers = [a.strip() for a in parts[1].split(',')]
            
            if not question or not answers:
                await interaction.followup.send("Question and at least one answer are required.", ephemeral=True)
                return
                
            # Add the question
            if not settings.custom_questions:
                settings.custom_questions = []
                
            settings.custom_questions.append({"question": question, "answers": answers})
            db.session.commit()
            
            await interaction.followup.send(
                f"Added question: \"{question}\"\n"
                f"Acceptable answers: {', '.join(answers)}",
                ephemeral=True
            )
            
        elif action == "remove_question":
            if not index:
                await interaction.followup.send("Please specify the question index to remove.", ephemeral=True)
                return
                
            if not settings.custom_questions or index < 1 or index > len(settings.custom_questions):
                await interaction.followup.send("Invalid question index.", ephemeral=True)
                return
                
            # Remove the question
            removed = settings.custom_questions.pop(index - 1)
            db.session.commit()
            
            await interaction.followup.send(
                f"Removed question: \"{removed['question']}\"",
                ephemeral=True
            )
            
        elif action == "list_questions":
            if not settings.custom_questions:
                await interaction.followup.send("No custom questions configured.", ephemeral=True)
                return
                
            # List all questions
            questions_list = "**Custom Verification Questions:**\n\n"
            for i, q in enumerate(settings.custom_questions, 1):
                questions_list += f"{i}. {q['question']}\n"
                questions_list += f"   Acceptable answers: {', '.join(q['answers'])}\n\n"
                
            await interaction.followup.send(questions_list, ephemeral=True)
            
        elif action == "status":
            # Show current verification settings
            status_message = "**Current Verification Settings:**\n\n"
            
            status_message += f"Captcha verification: {'✅' if settings.require_captcha else '❌'}\n"
            status_message += f"Custom questions: {'✅' if settings.require_questions else '❌'}\n"
            status_message += f"Role acceptance: {'✅' if settings.require_role_accept else '❌'}\n"
            status_message += f"Account age check: {'✅' if settings.require_account_age else '❌'}\n\n"
            
            if settings.require_account_age:
                status_message += f"Minimum account age: {settings.min_account_age_days} days\n"
            
            if settings.verification_channel_id:
                channel = interaction.guild.get_channel(int(settings.verification_channel_id))
                status_message += f"Verification channel: {channel.mention if channel else 'Invalid channel'}\n"
            
            if settings.verified_role_id:
                role = interaction.guild.get_role(int(settings.verified_role_id))
                status_message += f"Verified role: {role.mention if role else 'Invalid role'}\n"
            
            if settings.welcome_channel_id:
                channel = interaction.guild.get_channel(int(settings.welcome_channel_id))
                status_message += f"Welcome channel: {channel.mention if channel else 'Invalid channel'}\n"
            
            if settings.welcome_message:
                status_message += f"Welcome message: {settings.welcome_message}\n"
            
            status_message += f"\nCustom questions: {len(settings.custom_questions) if settings.custom_questions else 0}\n"
            
            # Add statistics
            status_message += f"\n**Statistics:**\n"
            status_message += f"Total verification attempts: {settings.total_attempts}\n"
            status_message += f"Successful verifications: {settings.successful_verifications}\n"
            status_message += f"Failed verifications: {settings.failed_verifications}\n"
            
            await interaction.followup.send(status_message, ephemeral=True)
            
        else:
            await interaction.followup.send(f"Unknown action: {action}", ephemeral=True)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.command(name="manual_verify", description="Manually verify a user")
    async def manual_verify(
        self, 
        interaction: Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        """Manually verify a user"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        
        # Get verification settings
        settings = await self.get_verification_settings(guild_id)
        
        # Skip if no verification required
        if not any([
            settings.require_captcha,
            settings.require_questions,
            settings.require_role_accept,
            settings.require_account_age
        ]):
            await interaction.followup.send(
                f"{user.mention} does not need verification as no verification is required for this server.",
                ephemeral=True
            )
            return
        
        # Assign verified role if configured
        if settings.verified_role_id:
            try:
                role = interaction.guild.get_role(int(settings.verified_role_id))
                if role:
                    await user.add_roles(role, reason=f"Manual verification by {interaction.user}")
            except Exception as e:
                await interaction.followup.send(
                    f"Error assigning verified role: {e}",
                    ephemeral=True
                )
                return
        
        # Create a verification log
        from app import app
        
        with app.app_context():
            # Create verification log
            verification_log = VerificationLog(
                user_id=str(user.id),
                guild_id=guild_id,
                setting_id=settings.id,
                success=True,
                captcha_completed=True,
                questions_completed=True,
                role_accept_completed=True,
                completed_at=datetime.utcnow(),
                failure_reason=None
            )
            db.session.add(verification_log)
            
            # Update settings stats
            settings.successful_verifications += 1
            
            db.session.commit()
        
        await interaction.followup.send(
            f"✅ {user.mention} has been manually verified by {interaction.user.mention}"
            + (f" with reason: {reason}" if reason else ""),
            ephemeral=True
        )
        
        # Send welcome message if configured
        if settings.welcome_channel_id and settings.welcome_message:
            try:
                channel = interaction.guild.get_channel(int(settings.welcome_channel_id))
                if channel:
                    welcome_msg = settings.welcome_message.replace("{user}", user.mention)
                    await channel.send(welcome_msg)
            except Exception as e:
                await interaction.followup.send(
                    f"Error sending welcome message: {e}",
                    ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(Verification(bot))
    print("Verification cog loaded")