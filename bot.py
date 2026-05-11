import discord
import datetime
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="g!", intents=intents)

# ==========================================
# DATABASE
# ==========================================

SETTINGS_FILE = "settings.json"
CONFIG_FILE = "config.json"
WARNS_FILE = "warns.json"

# create files if not exists
for file in [SETTINGS_FILE, CONFIG_FILE, WARNS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# ==========================================
# LOAD / SAVE
# ==========================================

async def log_action(guild, title, description, color, moderator, target=None, reason=None, action_taken=None):
    settings = get_guild_settings(guild.id)
    channel_id = settings.get("log_channel")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        embed.add_field(name="Moderator", value=moderator.mention)
        if target: embed.add_field(name="Target", value=target.mention)
        if reason: embed.add_field(name="Reason", value=reason)
        if action_taken: embed.add_field(name="Action", value=action_taken)
        await channel.send(embed=embed)

def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_warns():
    with open(WARNS_FILE, "r") as f:
        return json.load(f)

def save_warns(data):
    with open(WARNS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_guild_settings(guild_id):
    settings = load_settings()
    guild_id = str(guild_id)
    if guild_id not in settings:
        settings[guild_id] = {
            "log_channel": None,
            "allowed_roles": [],
            "blacklisted_roles": [],
            "anti_link": True,
            "anti_invite": True,
            "anti_swear": True,
            "anti_caps": True,
            "anti_emoji": True,
            "anti_mass_mention": True,
            "anti_token": True,
            "bad_words": ["badword1", "badword2"]
        }
        save_settings(settings)
    return settings[guild_id]

# ==========================================
# READY & PERMS
# ==========================================

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

def can_use_bot(member: discord.Member):
    if member.guild_permissions.administrator: return True
    settings = get_guild_settings(member.guild.id)
    role_ids = [role.id for role in member.roles]
    for role_id in settings["blacklisted_roles"]:
        if role_id in role_ids: return False
    if not settings["allowed_roles"]: return True
    for role_id in settings["allowed_roles"]:
        if role_id in role_ids: return True
    return False

# ==========================================
# COMMANDS
# ==========================================

@bot.tree.command(name="ghelp", description="View all bot commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Bot Commands", color=discord.Color.blue())
    embed.add_field(name="Moderation", value="/warn, /purge, /lock, /unlock, /ban, /kick, /timeout", inline=False)
    embed.add_field(name="Settings", value="/setlog, /addallowedrole, /removeallowedrole, /addblacklistrole, /toggleautomod", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setlog", description="Set log channel")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Admin only.", ephemeral=True)
    settings = load_settings()
    guild_id = str(interaction.guild.id)
    if guild_id not in settings: get_guild_settings(interaction.guild.id)
    settings = load_settings()
    settings[guild_id]["log_channel"] = channel.id
    save_settings(settings)
    await interaction.response.send_message(f"✅ Log channel set to {channel.mention}")

@bot.tree.command(name="addallowedrole", description="Allow role to use bot")
async def addallowedrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Admin only.", ephemeral=True)
    settings = load_settings()
    guild_id = str(interaction.guild.id)
    if guild_id not in settings: settings[guild_id] = {"allowed_roles": [], "blacklisted_roles": []}
    if role.id not in settings[guild_id]["allowed_roles"]:
        settings[guild_id]["allowed_roles"].append(role.id)
        save_settings(settings)
    await interaction.response.send_message(f"✅ {role.mention} added to allowed roles.")
    
@bot.tree.command(name="removeallowedrole", description="Remove allowed role")
async def removeallowedrole(interaction: discord.Interaction, role: discord.Role):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Admin only.", ephemeral=True)

    settings = load_settings()
    guild_id = str(interaction.guild.id)

    # ensure guild exists
    if guild_id not in settings:
        settings[guild_id] = {
            "allowed_roles": [],
            "blacklisted_roles": []
        }

    # ensure key exists
    if "allowed_roles" not in settings[guild_id]:
        settings[guild_id]["allowed_roles"] = []

    # remove role safely
    if role.id in settings[guild_id]["allowed_roles"]:
        settings[guild_id]["allowed_roles"].remove(role.id)
        save_settings(settings)

        await interaction.response.send_message(
            f"❌ {role.mention} removed from allowed roles."
        )
    else:
        await interaction.response.send_message(
            f"⚠️ {role.mention} is not in allowed roles.",
            ephemeral=True
        )
        
@bot.tree.command(name="toggleautomod", description="Enable or disable automod")
async def toggleautomod(
    interaction: discord.Interaction,
    feature: str,
    state: bool
):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "Administrator only.",
            ephemeral=True
        )

    settings = load_settings()
    guild_id = str(interaction.guild.id)

    # ensure guild exists
    if guild_id not in settings:
        settings[guild_id] = {
            "allowed_roles": [],
            "blacklisted_roles": [],
            "anti_link": True,
            "anti_invite": True,
            "anti_swear": True,
            "anti_caps": True,
            "anti_emoji": True,
            "anti_mass_mention": True,
            "anti_token": True
        }

    valid_features = [
        "anti_link",
        "anti_invite",
        "anti_swear",
        "anti_caps",
        "anti_emoji",
        "anti_mass_mention",
        "anti_token"
    ]

    if feature not in valid_features:
        return await interaction.response.send_message(
            "❌ Invalid feature name.",
            ephemeral=True
        )

    old_value = settings[guild_id].get(feature, False)

    settings[guild_id][feature] = state
    save_settings(settings)

    await interaction.response.send_message(
        f"✅ {feature} changed from `{old_value}` → `{state}`"
    )
    
@bot.tree.command(name="userinfo", description="View user info")
@app_commands.describe(member="Select member")
async def userinfo(interaction: discord.Interaction, member: discord.Member):

    embed = discord.Embed(
        title=f"{member.name}'s Info",
        color=discord.Color.green()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    joined = member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown"

    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(name="Joined Server", value=joined, inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="serverinfo", description="View server info")
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.orange()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    owner = guild.owner.mention if guild.owner else "Unknown"

    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def log_action(
    guild: discord.Guild,
    title: str,
    description: str,
    moderator: discord.Member,
    target: discord.Member | None = None,
    reason: str | None = None,
    action_taken: str | None = None
):
    settings = get_guild_settings(guild.id)
    channel_id = settings.get("log_channel")
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if target:
        embed.add_field(name="Target", value=target.mention, inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if action_taken:
        embed.add_field(name="Action", value=action_taken, inline=False)

    await channel.send(embed=embed)
        
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not can_use_bot(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    
    warns_data = load_warns()
    guild_id, user_id = str(interaction.guild.id), str(member.id)
    if guild_id not in warns_data: warns_data[guild_id] = {}
    warns_data[guild_id][user_id] = warns_data[guild_id].get(user_id, 0) + 1
    save_warns(warns_data)
    count = warns_data[guild_id][user_id]

    await interaction.response.send_message(f"⚠️ {member.mention} warned. Reason: {reason} (Warns: {count})")
    await log_action(guild = interaction.guild, title = "⚠️ Member Warned", description = "A member has received a warning.", color = discord.Color.orange(), moderator = interaction.user, target = member, reason = reason, action_taken = f"User now has {count} warning(s)")
    
    await log_action(interaction.guild, "⚠️ Member Warned", f"User warned for {reason}", discord.Color.orange(), interaction.user, member, reason, f"Total warns: {count}")
    await log_action(guild = interaction.guild, title = "⚠️ Member Warned", description = "A member has received a warning.", color = discord.Color.orange(), moderator = interaction.user, target = member, reason = reason, action_taken = f"User now has {count} warning(s)")

    if count == 3:
        await member.timeout(timedelta(minutes=10), reason="3 Warnings")
        await interaction.followup.send(f"⏳ {member.mention} timed out (3 warns).")
        await log_action(guild = interaction.guild, title = "⏳ Member Timed Out", description = "User reached warning limit.", color = discord.Color.yellow(), moderator = interaction.user, target = member, reason = "Reached 3 warnings", action_taken = "Timed out for 10 minutes"
)
    elif count == 5:
        await member.kick(reason="5 Warnings")
        await interaction.followup.send(f"👢 {member.mention} kicked (5 warns).")
        await log_action(guild = interaction.guild, title = "👢 Member Kicked", description = "User exceeded warning limit.", color = discord.Color.red(), moderator = interaction.user, target = member, reason = "Reached 5 warnings", action_taken = "User was kicked")
    elif count >= 7:
        await member.ban(reason="7 Warnings")
        await interaction.followup.send(f"🔨 {member.mention} banned (7+ warns).")
        await log_action(guild = interaction.guild, title = "🔨 Member Banned", description = "User exceeded warning limit.", color = discord.Color.dark_red(), moderator = interaction.user, target = member, reason = "Reached 7 warnings", action_taken = "User was permanently banned")

# =========================
# AUTOMOD LOGIC
# =========================

URL_REGEX = r"(https?:\/\/[^\s]+)"
INVITE_REGEX = r"(discord\.gg\/|discord\.com\/invite\/)"
TOKEN_REGEX = r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}"
BAD_WORDS = ["fuck", "bitch", "nigga", "shit"]
user_violations = {}

async def log_action(
    guild: discord.Guild,
    title: str,
    description: str,
    moderator: discord.Member,
    target: discord.Member | None = None,
    reason: str | None = None,
    action_taken: str | None = None
):
    settings = get_guild_settings(guild.id)
    channel_id = settings.get("log_channel")
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if target:
        embed.add_field(name="Target", value=target.mention, inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if action_taken:
        embed.add_field(name="Action", value=action_taken, inline=False)

    await channel.send(embed=embed)
    
async def handle_violation(message, reason):
    user_id = str(message.author.id)
    user_violations[user_id] = user_violations.get(user_id, 0) + 1
    await message.delete()
    if user_violations[user_id] == 1:
        await message.channel.send(f"{message.author.mention} ⚠️ Warning: {reason}", delete_after=10)
    else:
        try:
            await message.author.timeout(timedelta(minutes=10), reason=reason)
            await message.channel.send(f"{message.author.mention} ⏳ Timed out: {reason}", delete_after=10)
        except: pass
        user_violations[user_id] = 0

@bot.event
async def on_message(message):
    if not message.guild or message.author.bot: return
    
    # Auto reply example

msg = message.content.lower()

if msg in ["hello", "hi", "hey", "yo", "sup", "hola"]:
    await message.channel.send(
        f"Hey {message.author.mention} 👋 How are you doing?"
    )

elif msg in ["how are you", "how are you doing", "wyd"]:
    await message.channel.send(
        f"I'm doing great {message.author.mention} 😄 What about you?"
    )

elif msg in ["good morning", "morning"]:
    await message.channel.send(
        f"Good morning {message.author.mention} ☀️ Hope your day goes well!"
    )

elif msg in ["good afternoon", "afternoon"]:
    await message.channel.send(
        f"Good afternoon {message.author.mention} 😎"
    )

elif msg in ["good evening", "evening"]:
    await message.channel.send(
        f"Good evening {message.author.mention} 🌙"
    )

elif msg in ["good night", "night"]:
    await message.channel.send(
        f"Good night {message.author.mention} 😴 Sleep well!"
    )

elif msg in ["bye", "goodbye", "see ya", "cya"]:
    await message.channel.send(
        f"See you later {message.author.mention} 👋"
    )

elif msg in ["thanks", "thank you", "ty"]:
    await message.channel.send(
        f"You're welcome {message.author.mention} ❤️"
    )

elif msg in ["lol", "lmao", "haha", "wahala", "xd"]:
    await message.channel.send(
        f"{message.author.mention} 😂"
    )

elif msg in ["who made you", "who created you"]:
    await message.channel.send(
        f"I was created by my awesome developer GbonjuBola😎"
    )

elif msg in ["what can you do", "help"]:
    await message.channel.send(
        f"{message.author.mention} I can moderate servers, respond to messages, log actions, and more 🚀"
    )

elif msg in ["i love you", "love you"]:
    await message.channel.send(
        f"Aww ❤️ I love you too {message.author.mention}"
    )

elif msg in ["ping"]:
    await message.channel.send(
        f"Pong 🏓 {round(bot.latency * 1000)}ms"
    )

elif msg in ["bruh"]:
    await message.channel.send(
        f"{message.author.mention} 💀"
    )

elif msg in ["damn"]:
    await message.channel.send(
        f"Calm down there {message.author.mention} 😂"
    )

elif msg in ["bot"]:
    await message.channel.send(
        f"Yes {message.author.mention}? 🤖"
    )

elif msg in ["server dead"]:
    await message.channel.send(
        f"{message.author.mention} revive it then 😭"
    )

elif msg in ["gm"]:
    await message.channel.send(
        f"Good morning {message.author.mention} ☀️"
    )

elif msg in ["gn"]:
    await message.channel.send(
        f"Good night {message.author.mention} 🌙"
    )

elif msg in ["fr"]:
    await message.channel.send(
        f"Real 💯"
    )

elif msg in ["real"]:
    await message.channel.send(
        f"So real {message.author.mention} 💯"
    )

elif msg in ["w bot"]:
    await message.channel.send(
        f"Thanks {message.author.mention} ❤️"
    )

elif msg in ["l bot"]:
    await message.channel.send(
        f"That hurts {message.author.mention} 😔"
    )

elif msg in ["owner"]:
    await message.channel.send(
        f"My owner is amazing 😎"
    )

elif msg in ["can you code"]:
    await message.channel.send(
        f"Of course {message.author.mention} 💻"
    )

elif msg in ["discord"]:
    await message.channel.send(
        f"Best platform ever 😎"
    )

elif msg in ["welcome"]:
    await message.channel.send(
        f"Glad to be here {message.author.mention} ❤️"
    )

elif msg in ["hmm"]:
    await message.channel.send(
        f"What are you thinking about {message.author.mention}? 🤔"
    )

elif msg in ["sad"]:
    await message.channel.send(
        f"Cheer up {message.author.mention} ❤️"
    )

elif msg in ["happy"]:
    await message.channel.send(
        f"Love that energy {message.author.mention} 😄"
    )

elif msg in ["bored"]:
    await message.channel.send(
        f"Go chat with someone or play a game {message.author.mention} 🎮"
    )

elif msg in ["sleepy"]:
    await message.channel.send(
        f"Go get some rest {message.author.mention} 😴"
    )

elif msg in ["food"]:
    await message.channel.send(
        f"Now I'm hungry 🍔"
    )

elif msg in ["music"]:
    await message.channel.send(
        f"Music makes everything better 🎵"
    )

elif msg in ["anime"]:
    await message.channel.send(
        f"Anime fans rise up 🔥"
    )

elif msg in ["python"]:
    await message.channel.send(
        f"Python is awesome for Discord bots 🐍"
    )

elif msg in ["javascript", "js"]:
    await message.channel.send(
        f"JavaScript is powerful too ⚡"
    )

elif msg in ["what's up", "wassup"]:
    await message.channel.send(
        f"Nothing much {message.author.mention} 😎"
    )

elif msg in ["test"]:
    await message.channel.send(
        f"Testing successful ✅"
    )

elif msg in ["rip"]:
    await message.channel.send(
        f"Rest in peace 🕊️"
    )

elif msg in ["gg"]:
    await message.channel.send(
        f"GG {message.author.mention} 🎮"
    )

elif msg in ["skill issue"]:
    await message.channel.send(
        f"😭😭😭"
    )

guild_data = get_guild_settings(message.guild.id)

    # Anti-Link
    if guild_data["anti_link"] and re.search(URL_REGEX, message.content):
        if not any(inv.code in message.content for inv in await message.guild.invites()):
            await handle_violation(message, "External links not allowed")
            await log_action(guild = message.guild, title = "🔗 Unauthorized Link Detected", description = "A user sent a link not associated with this server.", color = discord.Color.red(), moderator = bot.user, target = message.author, reason = "Unauthorized external link", action_taken = "Message deleted + 10 minute timeout")
            return

    # Anti-Swear
    if guild_data["anti_swear"]:
        if any(word in message.content.lower().split() for word in BAD_WORDS):
            await handle_violation(message, "Swearing")
            await log_action(guild = message.guild, title = "🤬 Swear Detection", description = "Auto moderation detected profanity.", color = discord.Color.orange(), moderator = bot.user, target = message.author, reason = "Swearing detected", action_taken = "Warning issued")
            return

    # Anti-Caps
    if guild_data["anti_caps"] and len(message.content) > 10:
        if sum(1 for c in message.content if c.isupper()) >= len(message.content) * 0.7:
            await handle_violation(message, "Excessive Caps")
            return
            
    # Anti-Token
    if guild_data["anti_token"]:

        if re.search(TOKEN_REGEX, message.content):
            await handle_violation(message, "Possible token/logger detected")
            return
            
    await bot.process_commands(message)

# =========================
# UTILITY COMMANDS
# =========================

@bot.tree.command(name="purge")
async def purge(interaction: discord.Interaction, amount: int):
    if not can_use_bot(interaction.user): return await interaction.response.send_message("No perms.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.")

@bot.tree.command(name="lock")
async def lock(interaction: discord.Interaction):
    if not can_use_bot(interaction.user): return
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Channel locked.")

@bot.tree.command(name="unlock")
async def unlock(interaction: discord.Interaction):
    if not can_use_bot(interaction.user): return
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Channel unlocked.")
    
@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")


# BAN COMMAND
@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban")
async def log_action(
    guild: discord.Guild,
    title: str,
    description: str,
    moderator: discord.Member,
    target: discord.Member | None = None,
    reason: str | None = None,
    action_taken: str | None = None
):
    settings = get_guild_settings(guild.id)
    channel_id = settings.get("log_channel")
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if target:
        embed.add_field(name="Target", value=target.mention, inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if action_taken:
        embed.add_field(name="Action", value=action_taken, inline=False)

    await channel.send(embed=embed)
async def ban(interaction: discord.Interaction, member: discord.Member):

    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )

    # Prevent banning yourself
    if member == interaction.user:
        return await interaction.response.send_message(
            "You cannot ban yourself.",
            ephemeral=True
        )

    # Prevent banning the bot
    if member == interaction.guild.me:
        return await interaction.response.send_message(
            "You cannot ban the bot.",
            ephemeral=True
        )

    # Role hierarchy protection
    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message(
            "You cannot ban someone with an equal or higher role than you.",
            ephemeral=True
        )

    await member.ban(reason=f"Banned by {interaction.user}")

    await interaction.response.send_message(
        f"{member.mention} has been banned."
    )
    await log_action(guild = interaction.guild, title = "🔨 Member Banned", description = "User banned by admin", color = discord.Color.dark_red(), moderator = interaction.user, target = member, reason = "No Reason given", action_taken = "User was permanently banned")


# KICK COMMAND
@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick")
async def log_action(
    guild: discord.Guild,
    title: str,
    description: str,
    moderator: discord.Member,
    target: discord.Member | None = None,
    reason: str | None = None,
    action_taken: str | None = None
):
    settings = get_guild_settings(guild.id)
    channel_id = settings.get("log_channel")
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if target:
        embed.add_field(name="Target", value=target.mention, inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if action_taken:
        embed.add_field(name="Action", value=action_taken, inline=False)

    await channel.send(embed=embed)
async def kick(interaction: discord.Interaction, member: discord.Member):

    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )

    # Prevent kicking yourself
    if member == interaction.user:
        return await interaction.response.send_message(
            "You cannot kick yourself.",
            ephemeral=True
        )

    # Prevent kicking the bot
    if member == interaction.guild.me:
        return await interaction.response.send_message(
            "You cannot kick the bot.",
            ephemeral=True
        )

    # Role hierarchy protection
    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message(
            "You cannot kick someone with an equal or higher role than you.",
            ephemeral=True
        )

    await member.kick(reason=f"Kicked by {interaction.user}")

    await interaction.response.send_message(
        f"{member.mention} has been kicked."
    )


# TIMEOUT COMMAND
@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.describe(
    member="Member to timeout",
    minutes="How long the timeout should last"
)
async def log_action(
    guild: discord.Guild,
    title: str,
    description: str,
    moderator: discord.Member,
    target: discord.Member | None = None,
    reason: str | None = None,
    action_taken: str | None = None
):
    settings = get_guild_settings(guild.id)
    channel_id = settings.get("log_channel")
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if target:
        embed.add_field(name="Target", value=target.mention, inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if action_taken:
        embed.add_field(name="Action", value=action_taken, inline=False)

    await channel.send(embed=embed)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: int
):

    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )

    # Prevent timing out yourself
    if member == interaction.user:
        return await interaction.response.send_message(
            "You cannot timeout yourself.",
            ephemeral=True
        )

    # Prevent timing out the bot
    if member == interaction.guild.me:
        return await interaction.response.send_message(
            "You cannot timeout the bot.",
            ephemeral=True
        )

    # Role hierarchy protection
    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message(
            "You cannot timeout someone with an equal or higher role than you.",
            ephemeral=True
        )

    duration = datetime.timedelta(minutes=minutes)

    await member.timeout(
        duration,
        reason=f"Timed out by {interaction.user}"
    )

    await interaction.response.send_message(
        f"{member.mention} has been timed out for {minutes} minute(s)."
    )
    await log_action(guild = interaction.guild, title = "⏳ Member Timed Out", description = "User was timed out by admin", color = discord.Color.yellow(), moderator = interaction.user, target = member, reason = "No reason given", action_taken = f"{member.mention} has been timed out for {minutes} minute(s)."


# CLEAR COMMAND
@bot.tree.command(name="clear", description="Delete messages")
@app_commands.describe(amount="Number of messages to delete")
async def clear(interaction: discord.Interaction, amount: int):

    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )

    await interaction.channel.purge(limit=amount)

    await interaction.response.send_message(
        f"Deleted {amount} messages.",
        ephemeral=True
    )
    
if TOKEN:
    bot.run(TOKEN)
else:
    print("No TOKEN found!")
