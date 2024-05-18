import discord
from discord.ext import commands, tasks
import json
import secrets
import string
import os
import random
import pytz
import time
import asyncio
import typing
from typing import Union
from datetime import datetime
from discord.ui import View, Button

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='+', intents=intents)


@bot.event
async def on_ready():
  print(f'Logged in as {bot.user.name}')
  streaming_status.start()
  update_channel_names.start()
  await bot.tree.sync()


status_index = 0
@tasks.loop(seconds=10)
async def streaming_status():
    global status_index
    now = datetime.now(pytz.timezone('Asia/Bangkok'))
    current_date = now.strftime("%d/%m/%Y") 
    current_time = now.strftime("%H:%M %p")
    if status_index == 0:
        activity = discord.Game(name=f"/help | {len(bot.guilds)} servers")
    else:
        activity = discord.Game(name=f"Day: {current_date}")
        await bot.change_presence(activity=activity)
        await asyncio.sleep(5) 
        activity = discord.Game(name=f"Time: {current_time}", type=1)
    await bot.change_presence(activity=activity)
    status_index = 1 - status_index

class HelpView(View):
    def __init__(self, embeds):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.current_page = 0

        self.next_button = Button(label='Next', style=discord.ButtonStyle.primary)
        self.next_button.callback = self.next_page
        self.prev_button = Button(label='Previous', style=discord.ButtonStyle.primary)
        self.prev_button.callback = self.prev_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.update_buttons()

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        await self.update_embed(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        await self.update_embed(interaction)

    async def update_embed(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1

def create_help_embeds():
    commands_info = [
        ("/purge", "🗑️ Clear messages from the channel"),
        ("/setprefix", "⚙️ Change the bot prefix"),
        ("/avatar", "🖼️ Get a user's avatar"),
        ("/serverinfo", "ℹ️ Get information about the server"),
        ("/slowmode", "🐌 Set the slow mode delay for the current channel"),
        ("/userinfo", "👤 Get information about a user"),
        ("/kick", "👢 Kick a user from the server"),
        ("/ban", "🔨 Ban a user from the server"),
    ]

    embeds = []
    page_size = 5
    for i in range(0, len(commands_info), page_size):
        embed = discord.Embed(
            title="🔹 Help - Commands List 🔹",
            description="Here are the available commands you can use:",
            color=discord.Color.blue()
        )
        for name, description in commands_info[i:i + page_size]:
            embed.add_field(name=name, value=description, inline=False)
        embed.set_footer(text=f"Page {i // page_size + 1}/{(len(commands_info) - 1) // page_size + 1}")
        embed.set_thumbnail(url=bot.user.avatar.url)
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
        embeds.append(embed)
    return embeds

@bot.tree.command(name='help', description='List all commands and their descriptions')
async def help_command(interaction: discord.Interaction):
    embeds = create_help_embeds()
    view = HelpView(embeds)
    await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)


@bot.tree.command(name='kick', description='Kick a user from the server')
@commands.has_permissions(kick_members=True)
async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        embed = discord.Embed(
            title='❌ Error',
            description='You do not have permission to use this command.',
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title='👢 Member Kicked',
            description=f'{member.mention} has been kicked from the server.',
            color=discord.Color.orange()
        )
        embed.add_field(name='Kicked By', value=interaction.user.mention, inline=True)
        embed.add_field(name='Reason', value=reason, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text='Kicked Command Executed', icon_url=interaction.user.avatar)
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title='❌ Error',
            description='I do not have permission to kick this member.',
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='ban', description='Ban a user from the server')
async def ban_command(interaction: discord.Interaction, user: discord.Member, reason: str = 'No reason provided'):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message('You do not have permission to ban members.', ephemeral=True)
        return

    try:
        await user.ban(reason=reason)
        embed = discord.Embed(
            title='🔨 User Banned',
            description=f'{user.mention} has been banned from the server.',
            color=discord.Color.red()
        )
        embed.add_field(name='Banned by', value=interaction.user.mention, inline=False)
        embed.add_field(name='Reason', value=reason, inline=False)
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text='Banned Command Executed', icon_url=interaction.user.avatar)
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message('I do not have permission to ban this user.', ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f'An error occurred: {str(e)}', ephemeral=True)

@bot.tree.command(name='purge', description='Clear messages from the channel')
async def purge_command(interaction: discord.Interaction, amount: int = 5):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title='❌ Permission Denied',
            description='You do not have permission to use this command.',
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not (1 <= amount <= 100):
        embed = discord.Embed(
            title='❌ Error',
            description='Please provide a number between 1 and 100 for the amount to clear.',
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    deleted_messages = await interaction.channel.purge(limit=amount + 1)

    embed = discord.Embed(
        title='🧹 Messages Cleared',
        description='messages have been cleared.',
        color=discord.Color.green()
    )
    embed.set_thumbnail(url='https://cdn-icons-png.flaticon.com/512/619/619034.png')
    embed.add_field(name='🧹 Purged By', value=interaction.user.mention, inline=True)
    embed.add_field(name='🗑️ Number of Messages', value=len(deleted_messages) - 1, inline=True)
    embed.set_footer(text='Purge Command Executed', icon_url=interaction.user.avatar)
    embed.timestamp = datetime.now()

    await interaction.followup.send(embed=embed, ephemeral=True)

    
  # Slash command for /setprefix
@bot.tree.command(name='setprefix', description='Change the bot prefix')
async def setprefix_command(interaction: discord.Interaction, new_prefix: str):
    if interaction.user.id == 837294095335817226:  # Replace with your user ID
        bot.command_prefix = new_prefix
        embed = discord.Embed(
            title="Set Prefix",
            description=f"Prefix has been changed to {new_prefix}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="Error",
            description="You don't have permission to change the prefix.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Slash command for /avatar
@bot.tree.command(name='avatar', description='Get a user\'s avatar')
async def avatar_command(interaction: discord.Interaction, user: Union[discord.User, None] = None):
    if user is None:
        user = interaction.user

    embed = discord.Embed(
        title=f"🖼️ Avatar of {user.name}",
        description="",
        color=discord.Color.blue()
    )
    embed.set_image(url=user.display_avatar.url)
    embed.timestamp = datetime.now()

    await interaction.response.send_message(embed=embed)

# Slash command for /serverinfo
@bot.tree.command(name='serverinfo', description='Get information about the server')
async def serverinfo_command(interaction: discord.Interaction):
    guild = interaction.guild
    server_name = guild.name
    server_owner = guild.owner.name
    member_count = guild.member_count
    created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
    guild_icon_url = guild.icon
    embed = discord.Embed(
        title=f"Server Info - {server_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Owner", value=server_owner, inline=False)
    embed.add_field(name="Members", value=member_count, inline=False)
    embed.add_field(name="Created At", value=created_at, inline=False)
    embed.set_thumbnail(url=guild_icon_url)
    await interaction.response.send_message(embed=embed)

# Slash command for /slowmode
@bot.tree.command(name='slowmode', description='Set the slow mode delay for the current channel')
async def slowmode_command(interaction: discord.Interaction, seconds: int):
    embed = discord.Embed(
        title='🐌 Slow Mode Set',
        color=discord.Color.blue()
    )

    if not interaction.user.guild_permissions.manage_channels:
        embed.title = '❌ Error'
        embed.description = 'You do not have permission to set slow mode in this channel.'
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await interaction.channel.edit(slowmode_delay=seconds)
        embed.description = f'Slow mode has been set to {seconds} seconds.'
        embed.add_field(name='Set By', value=interaction.user.mention, inline=True)
        embed.add_field(name='Channel', value=interaction.channel.mention, inline=True)
        embed.set_thumbnail(url='https://cdn3.emoji.gg/emojis/8597-discord-channel-from-vega.png')
        embed.set_footer(text='Slowmode Command Executed', icon_url=interaction.user.avatar)
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed.title = '❌ Error'
        embed.description = 'I do not have permission to set slow mode in this channel.'
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Slash command for /userinfo
@bot.tree.command(name='userinfo', description='Get information about a user')
async def userinfo_command(interaction: discord.Interaction, member: Union[discord.Member, None] = None):
    member = member or interaction.user

    embed = discord.Embed(
        title=f"👤 User Info - {member.name}",
        description=f"Here is the information about {member.mention}",
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_author(name=member.name, icon_url=member.display_avatar.url)
    embed.add_field(name='Username', value=member.name, inline=True)
    embed.add_field(name='User ID', value=member.id, inline=True)
    embed.add_field(name='Joined Server', value=member.joined_at.strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.add_field(name='Joined Discord', value=member.created_at.strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.add_field(name='Top Role', value=member.top_role.mention, inline=True)
    embed.set_footer(text='UserInfo Command Executed', icon_url=interaction.user.avatar)
    embed.timestamp = datetime.now()

    await interaction.response.send_message(embed=embed)

bot.run('BOT-TOKEN-HERE')