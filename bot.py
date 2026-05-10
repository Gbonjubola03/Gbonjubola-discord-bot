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
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(WARNS_FILE):
    with open(WARNS_FILE, "w") as f:
        json.dump({}, f)

# ==========================================
# LOAD / SAVE
# ==========================================

async def log_action(guild, title, description, color, moderator, target=None, reason=None, action_taken=None):
    pass

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

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# DEFAULT SETTINGS
# ==========================================

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
            "bad_words": [
                "badword1",
                "badword2"
            ]
        }

        save_settings(settings)

    return settings[guild_id]

# ==========================================
# READY
# ==========================================

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# ==========================================
# PERMISSION CHECK
# ==========================================

def can_use_bot(member: discord.Member):

    settings = get_guild_settings(member.guild.id)

    role_ids = [role.id for role in member.roles]

    # blocked roles
    for role_id in settings["blacklisted_roles"]:
        if role_id in role_ids:
            return False

    # if no allowed roles set
    if len(settings["allowed_roles"]) == 0:
        return True

    # allowed roles
    for role_id in settings["allowed_roles"]:
        if role_id in role_ids:
            return True

    return False

# ==========================================
# LOGGING
# ==========================================

async def send_log(guild, message):

    settings = get_guild_settings(guild.id)

    channel_id = settings["log_channel"]

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel:
        await channel.send(message)

# ==========================================
# HELP COMMAND
# ==========================================

@bot.tree.command(name="ghelp", description="View all bot commands")
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="Bot Commands",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Moderation",
        value="""
/warn
/purge
/lock
/unlock
""",
        inline=False
    )

    embed.add_field(
        name="Info",
        value="""
/userinfo
/serverinfo
""",
        inline=False
    )

    embed.add_field(
        name="Settings",
        value="""
/setlog
/addallowedrole
/removeallowedrole
/addblacklistrole
/removeblacklistrole
/toggleautomod
""",
        inline=False
    )

    await interaction.response.send_message(embed=embed)

# ==========================================
# SET LOG CHANNEL
# ==========================================

@bot.tree.command(name="setlog", description="Set log channel")
@app_commands.describe(channel="Select log channel")
async def setlog(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "Administrator only.",
            ephemeral=True
        )

    settings = load_settings()

    guild_id = str(interaction.guild.id)

    if guild_id not in settings:
        get_guild_settings(interaction.guild.id)
        settings = load_settings()

    settings[guild_id]["log_channel"] = channel.id

    save_settings(settings)

    await interaction.response.send_message( 
        f"✅ Log channel set to {channel.mention}"
    )

# ==========================================
# ADD ALLOWED ROLE
# ==========================================

@bot.tree.command(name="addallowedrole", description="Allow role to use bot")
@app_commands.describe(role="Select role")
async def addallowedrole(
    interaction: discord.Interaction,
    role: discord.Role
):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "Administrator only.",
            ephemeral=True
        )

    settings = load_settings()

    guild_id = str(interaction.guild.id)

get_guild_settings(interaction.guild.id)
settings = load_settings()

    if role.id not in settings[guild_id]["allowed_roles"]:
        settings[guild_id]["allowed_roles"].append(role.id)

    save_settings(settings)

    await interaction.response.send_message(
        f"✅ {role.mention} can now use moderation commands."
    )

# ==========================================
# REMOVE ALLOWED ROLE
# ==========================================

@bot.tree.command(name="removeallowedrole", description="Remove allowed role")
@app_commands.describe(role="Select role")
async def removeallowedrole(
    interaction: discord.Interaction,
    role: discord.Role
):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "Administrator only.",
            ephemeral=True
        )

    settings = load_settings()

    guild_id = str(interaction.guild.id)

    if role.id in settings[guild_id]["allowed_roles"]:
        settings[guild_id]["allowed_roles"].remove(role.id)

    save_settings(settings)

    await interaction.response.send_message(
        f"❌ {role.mention} removed from allowed roles."
    )

# ==========================================
# ADD BLACKLIST ROLE
# ==========================================

@bot.tree.command(name="addblacklistrole", description="Blacklist a role")
@app_commands.describe(role="Select role")
async def addblacklistrole(
    interaction: discord.Interaction,
    role: discord.Role
):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "Administrator only.",
            ephemeral=True
        )

    settings = load_settings()

    guild_id = str(interaction.guild.id)

    if role.id not in settings[guild_id]["blacklisted_roles"]:
        settings[guild_id]["blacklisted_roles"].append(role.id)

    save_settings(settings)

    await interaction.response.send_message(
        f"🚫 {role.mention} blacklisted from bot usage."
    )

# ==========================================
# REMOVE BLACKLIST ROLE
# ==========================================

@bot.tree.command(name="removeblacklistrole", description="Remove blacklist role")
@app_commands.describe(role="Select role")
async def removeblacklistrole(
    interaction: discord.Interaction,
    role: discord.Role
):

    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "Administrator only.",
            ephemeral=True
        )

    settings = load_settings()

    guild_id = str(interaction.guild.id)

    if role.id in settings[guild_id]["blacklisted_roles"]:
        settings[guild_id]["blacklisted_roles"].remove(role.id)

    save_settings(settings)

    await interaction.response.send_message(
        f"✅ {role.mention} removed from blacklist."
    )

# ==========================================
# TOGGLE AUTOMOD
# ==========================================

@bot.tree.command(name="toggleautomod", description="Enable or disable automod")
@app_commands.describe(
    feature="Feature name",
    state="true or false"
)
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
            "Invalid feature name.",
            ephemeral=True
        )

    settings[guild_id][feature] = state

    save_settings(settings)

    await interaction.response.send_message(
        f"✅ {feature} set to {state}"
    )

# =========================
# WARN SYSTEM
# =========================

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str
):

    if is_blocked(interaction.user):
        return await interaction.response.send_message(
            "❌ Your role cannot use this bot.",
            ephemeral=True
        )

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id not in warns:
        warns[guild_id] = {}

    if user_id not in warns[guild_id]:
        warns[guild_id][user_id] = 0

    warns[guild_id][user_id] += 1
    save_warns()

    count = warns[guild_id][user_id]

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned.\nReason: {reason}\nWarns: {count}"
    )

await log_action(
    guild=interaction.guild,
    title="⚠️ Member Warned",
    description="A member has received a warning.",
    color=discord.Color.orange(),
    moderator=interaction.user,
    target=member,
    reason=reason,
    action_taken=f"User now has {count} warning(s)"
)

    # 3 warns = timeout
    if count >= 3 and count < 5:
        await member.timeout(
            timedelta(minutes=10),
            reason="Reached 3 warnings"
        )

        await interaction.followup.send(
            f"⏳ {member.mention} timed out for 10 minutes."
        )

await log_action(
    guild=interaction.guild,
    title="⏳ Member Timed Out",
    description="User reached warning limit.",
    color=discord.Color.yellow(),
    moderator=interaction.user,
    target=member,
    reason="Reached 3 warnings",
    action_taken="Timed out for 10 minutes"
)

    # 5 warns = kick
    elif count >= 5 and count < 7:
        await member.kick(reason="Reached 5 warnings")

        await interaction.followup.send(
            f"👢 {member.mention} has been kicked."
        )

await log_action(
    guild=interaction.guild,
    title="👢 Member Kicked",
    description="User exceeded warning limit.",
    color=discord.Color.red(),
    moderator=interaction.user,
    target=member,
    reason="Reached 5 warnings",
    action_taken="User was kicked"
)

    # 7 warns = ban
    elif count >= 7:
        await member.ban(reason="Reached 7 warnings")

        await interaction.followup.send(
            f"🔨 {member.mention} has been banned."
        )

await log_action(
    guild=interaction.guild,
    title="🔨 Member Banned",
    description="User exceeded warning limit.",
    color=discord.Color.dark_red(),
    moderator=interaction.user,
    target=member,
    reason="Reached 7 warnings",
    action_taken="User was permanently banned"
)

# ==========================================
# PURGE
# ==========================================

@bot.tree.command(name="purge", description="Delete messages")
@app_commands.describe(amount="Number of messages")
async def purge(
    interaction: discord.Interaction,
    amount: int
):

    if not can_use_bot(interaction.user):
        return await interaction.response.send_message(
            "No permission.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=amount)

    await interaction.followup.send(
        f"Deleted {len(deleted)} messages.",
        ephemeral=True
    )

# ==========================================
# LOCK
# ==========================================

@bot.tree.command(name="lock", description="Lock current channel")
async def lock(interaction: discord.Interaction):

    if not can_use_bot(interaction.user):
        return await interaction.response.send_message(
            "No permission.",
            ephemeral=True
        )

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = False

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message("🔒 Channel locked.")

await log_action(
    guild=interaction.guild,
    title="🔒 Channel Locked",
    description=f"{interaction.channel.mention} was locked.",
    color=discord.Color.blurple(),
    moderator=interaction.user,
    action_taken="Members can no longer send messages"
)

# ==========================================
# UNLOCK
# ==========================================

@bot.tree.command(name="unlock", description="Unlock current channel")
async def unlock(interaction: discord.Interaction):

    if not can_use_bot(interaction.user):
        return await interaction.response.send_message(
            "No permission.",
            ephemeral=True
        )

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = True

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message("🔓 Channel unlocked.")

await log_action(
    guild=interaction.guild,
    title="🔓 Channel Unlocked",
    description=f"{interaction.channel.mention} was unlocked.",
    color=discord.Color.green(),
    moderator=interaction.user,
    action_taken="Members can now send messages"
)

# ==========================================
# USER INFO
# ==========================================

@bot.tree.command(name="userinfo", description="View user info")
@app_commands.describe(member="Select member")
async def userinfo(
    interaction: discord.Interaction,
    member: discord.Member
):

    embed = discord.Embed(
        title=f"{member.name}'s Info",
        color=discord.Color.green()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"))

    await interaction.response.send_message(embed=embed)

# ==========================================
# SERVER INFO
# ==========================================

@bot.tree.command(name="serverinfo", description="View server info")
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.orange()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="Owner", value=guild.owner)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))

    await interaction.response.send_message(embed=embed)

# =========================
# AUTO MOD SYSTEM
# =========================

user_violations = {}

BAD_WORDS = [
    "fuck",
    "bitch",
    "nigga",
    "shit"
]

URL_REGEX = r"(https?:\/\/[^\s]+)"
INVITE_REGEX = r"(discord\.gg\/|discord\.com\/invite\/)"
TOKEN_REGEX = r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}"

async def handle_violation(message, reason):

    user_id = str(message.author.id)

    if user_id not in user_violations:
        user_violations[user_id] = 0

    user_violations[user_id] += 1

    # DELETE MESSAGE
    await message.delete()

    # FIRST OFFENSE
    if user_violations[user_id] == 1:

        await message.channel.send(
            f"{message.author.mention} ⚠️ Warning: {reason}",
            delete_after=10
        )

    # SECOND OFFENSE
    else:

        await message.author.timeout(
            timedelta(minutes=10),
            reason=reason
        )

        await message.channel.send(
            f"{message.author.mention} ⏳ Timed out for 10 minutes.\nReason: {reason}",
            delete_after=10
        )

        user_violations[user_id] = 0

# =========================
# MESSAGE EVENT
# =========================

@bot.event
async def on_message(message):

if not message.guild:
    return

    if message.author.bot:
        return

    # auto reply
    if "hello" in message.content.lower():
        await message.channel.send("Hey 👋")

    guild_data = get_guild_settings(message.guild.id)

    # automod stuff...

    await bot.process_commands(message)

    # =====================
    # ANTI LINK
    # =====================

    if guild_data["anti_link"]:

        if re.search(URL_REGEX, message.content):

            allowed = False

            # ALLOW SERVER INVITES
            if "discord.gg/" in message.content:

                guild_invites = await message.guild.invites()

                for invite in guild_invites:

                    if invite.code in message.content:
                        allowed = True

            if not allowed:

                await message.delete()

                await message.author.timeout(
                    timedelta(minutes=10),
                    reason="Unauthorized link"
                )

                return await message.channel.send(
                    f"{message.author.mention} ⏳ You've been timed out for 10 minutes for sending a link not associated with this server.",
                    delete_after=10
                )

await log_action(
    guild=message.guild,
    title="🔗 Unauthorized Link Detected",
    description="A user sent a link not associated with this server.",
    color=discord.Color.red(),
    moderator=bot.user,
    target=message.author,
    reason="Unauthorized external link",
    action_taken="Message deleted + 10 minute timeout"
)

    # =====================
    # ANTI INVITE
    # =====================

    if guild_data["anti_invite"]:
        if re.search(INVITE_REGEX, message.content):
            await handle_violation(message, "Sending Discord invite links")
            return

    # =====================
    # ANTI SWEAR
    # =====================

    if guild_data["anti_swear"]:
        for word in BAD_WORDS:

words = message.content.lower().split()

if word in words:

                await handle_violation(message, "Swearing")
                return

await log_action(
    guild=message.guild,
    title="🤬 Swear Detection",
    description="Auto moderation detected profanity.",
    color=discord.Color.orange(),
    moderator=bot.user,
    target=message.author,
    reason="Swearing detected",
    action_taken="Warning issued"
)

    # =====================
    # ANTI CAPS
    # =====================

    if guild_data["anti_caps"]:

        if len(message.content) > 10:

            upper = sum(1 for c in message.content if c.isupper())

            if upper >= len(message.content) * 0.7:
                await handle_violation(message, "Excessive caps")
                return

    # =====================
    # ANTI MASS MENTION
    # =====================

    if guild_data["anti_mass_mention"]:

        if len(message.mentions) >= 5:
            await handle_violation(message, "Mass mentioning")
            return

    # =====================
    # ANTI EMOJI SPAM
    # =====================

    if guild_data["anti_emoji"]:

        emojis = re.findall(r"<a?:\w+:\d+>", message.content)

        if len(emojis) >= 6:
            await handle_violation(message, "Emoji spam")
            return

    # =====================
    # ANTI TOKEN
    # =====================

    if guild_data["anti_token"]:

        if re.search(TOKEN_REGEX, message.content):
            await handle_violation(message, "Possible token/logger detected")
            return

# Welcome Channel Set
@bot.tree.command(name="setwelcome")
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.welcome_channel_id = channel.id
    await interaction.response.send_message(f"Welcome channel set to {channel.mention}")

# Welcome Message
@bot.event
async def on_member_join(member):
    channel_id = getattr(bot, "welcome_channel_id", None)
    if channel_id is None:
        return

    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"Welcome to the server, {member.mention} 🎉")


# PING COMMAND
@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")
    
# BAN COMMAND
@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban")
async def ban(interaction: discord.Interaction, member: discord.Member):

    if interaction.user.guild_permissions.ban_members:
        await member.ban(reason="Banned by admin")
        await interaction.response.send_message(f"{member} has been banned.")
    else:
        await interaction.response.send_message("You don't have permission.")

# KICK COMMAND
@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick")
async def kick(interaction: discord.Interaction, member: discord.Member):

    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason="Kicked by admin")
        await interaction.response.send_message(f"{member} has been kicked.")
    else:
        await interaction.response.send_message("You don't have permission.")

# TIMEOUT COMMAND
@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.describe(
    member="Member to timeout",
    minutes="How long the timeout should last"
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: int
):

    if interaction.user.guild_permissions.moderate_members:

        duration = datetime.timedelta(minutes=minutes)

        await member.timeout(
            duration,
            reason=f"Timed out by {interaction.user}"
        )

        await interaction.response.send_message(
            f"{member.mention} has been timed out for {minutes} minute(s)."
        )

    else:
        await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )


    if interaction.user.guild_permissions.manage_messages:
        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(
            f"Deleted {amount} messages.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )

# FAIL NOTIFICATION 

if TOKEN is None:
    print("ERROR: TOKEN not found in environment variables!")

# RUN BOT
bot.run(TOKEN)
