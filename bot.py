import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()
TOKEN = os.getenv("TOKEN")

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="g!", intents=intents)

# =========================
# FILES
# =========================
SETTINGS_FILE = "settings.json"
WARNS_FILE = "warns.json"

for file in [SETTINGS_FILE, WARNS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# =========================
# LOAD / SAVE
# =========================
def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load_settings():
    return load_json(SETTINGS_FILE)

def save_settings(data):
    save_json(SETTINGS_FILE, data)

def load_warns():
    return load_json(WARNS_FILE)

def save_warns(data):
    save_json(WARNS_FILE, data)

# =========================
# DEFAULT SETTINGS
# =========================
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
            "anti_token": True
        }
        save_settings(settings)

    return settings[guild_id]

# =========================
# PERMISSION CHECK
# =========================
def can_use_bot(member: discord.Member):
    settings = get_guild_settings(member.guild.id)
    role_ids = [r.id for r in member.roles]

    if any(r in settings["blacklisted_roles"] for r in role_ids):
        return False

    if not settings["allowed_roles"]:
        return True

    return any(r in settings["allowed_roles"] for r in role_ids)

# =========================
# WARN SYSTEM
# =========================
warns = load_warns()

# =========================
# AUTOMOD HELPERS
# =========================
BAD_WORDS = ["fuck", "bitch", "shit", "nigga"]
URL_REGEX = r"(https?:\/\/[^\s]+)"
INVITE_REGEX = r"(discord\.gg\/|discord\.com\/invite\/)"
TOKEN_REGEX = r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}"

async def handle_violation(message, reason):
    user_id = str(message.author.id)

    if user_id not in warns:
        warns[user_id] = 0

    warns[user_id] += 1
    save_warns(warns)

    await message.delete()

    if warns[user_id] >= 2:
        await message.author.timeout(timedelta(minutes=10), reason=reason)
        warns[user_id] = 0
        save_warns(warns)

        await message.channel.send(
            f"{message.author.mention} ⏳ Timed out (10 mins): {reason}",
            delete_after=10
        )
    else:
        await message.channel.send(
            f"{message.author.mention} ⚠️ Warning: {reason}",
            delete_after=10
        )

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# =========================
# HELP
# =========================
@bot.tree.command(name="ghelp")
async def ghelp(interaction: discord.Interaction):
    embed = discord.Embed(title="Bot Commands", color=discord.Color.blue())

    embed.add_field(name="Moderation", value="warn, ban, kick, timeout, purge", inline=False)
    embed.add_field(name="Settings", value="setlog, addallowedrole, removeallowedrole", inline=False)

    await interaction.response.send_message(embed=embed)

# =========================
# WARN COMMAND
# =========================
@bot.tree.command(name="warn")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id not in warns:
        warns[guild_id] = {}

    if user_id not in warns[guild_id]:
        warns[guild_id][user_id] = 0

    warns[guild_id][user_id] += 1
    save_warns(warns)

    count = warns[guild_id][user_id]

    await interaction.response.send_message(
        f"{member.mention} warned. Reason: {reason} (Total: {count})"
    )

    if count == 3:
        await member.timeout(timedelta(minutes=10), reason="3 warns")
    elif count == 5:
        await member.kick(reason="5 warns")
    elif count >= 7:
        await member.ban(reason="7 warns")

# =========================
# PURGE
# =========================
@bot.tree.command(name="purge")
async def purge(interaction: discord.Interaction, amount: int):

    if not can_use_bot(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)

    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

# =========================
# LOCK / UNLOCK
# =========================
@bot.tree.command(name="lock")
async def lock(interaction: discord.Interaction):

    if not can_use_bot(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)

    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False

    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Channel locked.")

@bot.tree.command(name="unlock")
async def unlock(interaction: discord.Interaction):

    if not can_use_bot(interaction.user):
        return await interaction.response.send_message("No permission.", ephemeral=True)

    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = True

    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Channel unlocked.")

# =========================
# USER INFO
# =========================
@bot.tree.command(name="userinfo")
async def userinfo(interaction: discord.Interaction, member: discord.Member):

    embed = discord.Embed(title=member.name, color=discord.Color.green())
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Joined", value=member.joined_at, inline=False)

    await interaction.response.send_message(embed=embed)

# =========================
# SERVER INFO
# =========================
@bot.tree.command(name="serverinfo")
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    embed = discord.Embed(title=guild.name, color=discord.Color.orange())
    embed.add_field(name="Members", value=guild.member_count)

    await interaction.response.send_message(embed=embed)

# =========================
# AUTOMOD EVENT
# =========================
@bot.event
async def on_message(message):

    if not message.guild or message.author.bot:
        return

    settings = get_guild_settings(message.guild.id)

    content = message.content.lower()

    # ANTI LINK
    if settings["anti_link"] and re.search(URL_REGEX, content):
        await handle_violation(message, "Links not allowed")
        return

    # ANTI INVITE
    if settings["anti_invite"] and re.search(INVITE_REGEX, content):
        await handle_violation(message, "Invite links not allowed")
        return

    # ANTI SWEAR
    if settings["anti_swear"]:
        for word in BAD_WORDS:
            if word in content.split():
                await handle_violation(message, "Swearing detected")
                return

    # ANTI TOKEN
    if settings["anti_token"] and re.search(TOKEN_REGEX, content):
        await handle_violation(message, "Token detected")
        return

    await bot.process_commands(message)

# =========================
# RUN BOT
# =========================
if TOKEN is None:
    print("ERROR: TOKEN not found")

bot.run(TOKEN)