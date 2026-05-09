import discord
import datetime
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Bot Ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# Welcome Message
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    
    if channel:
        await channel.send(f"Welcome {member.mention} to the server 🎉")

# Auto Reply
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if "hello" in message.content.lower():
        await message.channel.send("Hey 👋")

    await bot.process_commands(message)

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

# CLEAR COMMAND
@bot.tree.command(name="clear", description="Delete messages")
@app_commands.describe(amount="Number of messages")
async def clear(interaction: discord.Interaction, amount: int):

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
