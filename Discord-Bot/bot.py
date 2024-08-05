import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord import Member
import asyncio
from discord.ext.commands import has_permissions, MissingPermissions
from discord import FFmpegAudio
import random
import json
import youtube_dl
import os
from discord.utils import get
from youtube_dl import YoutubeDL
import yt_dlp as youtube_dl
from datetime import timedelta


intents = discord.Intents.all()

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

queue = []

def play_next(ctx):
    if len(queue) > 0:
        song = queue.pop(0)
        asyncio.run_coroutine_threadsafe(play_song(ctx, song), bot.loop)

async def play_song(ctx, song):
    async with ctx.typing():
        player = await YTDLSource.from_url(song, loop=bot.loop)
        ctx.voice_client.play(player, after=lambda e: play_next(ctx))
        await ctx.send(f'Now playing: {player.title}')

@bot.event # bot is ready
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command(name='join') # command bot joins voice channel
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()

@bot.command(name='leave') # command bot leaves voice channel
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()

@bot.command(name='play') # command to play music
async def play(ctx, *, url):
    queue.append(url)
    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        await play_song(ctx, url)

@bot.command(name='pause') # command to pause music
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused")
    else:
        await ctx.send("Not playing any music right now.")

@bot.command(name='resume') # command to resume music
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed")
    else:
        await ctx.send("The music is not paused.")

@bot.command(name='stop') # command to stop music and clear queue
async def stop(ctx):
    ctx.voice_client.stop()
    queue.clear()
    await ctx.send("Stopped and cleared the queue.")

@bot.command(name='queue') # command to display queue
async def queue_(ctx):
    if len(queue) == 0:
        await ctx.send("The queue is empty.")
    else:
        await ctx.send('\n'.join([f'{i+1}. {url}' for i, url in enumerate(queue)]))

@bot.command(name='clear') # command to clear queue
async def clear(ctx):
    queue.clear()
    await ctx.send("Cleared the queue.")

@bot.command(name='skip') # command to skip current song
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped")
        play_next(ctx)
    else:
        await ctx.send("Not playing any music right now.")


# when the bot reads a certain message it responds appropriately
@bot.listen('on_message')
async def listen(message):
    if message.author == bot.user:
        return

    if message.content == 'hello':
        await message.channel.send('Hello!')

    deletable_words = ['deletable', 'words', 'here']

    for word in deletable_words:
        if word in message.content:
            await message.delete()
            await message.channel.send('Please do not use that word here!')


    bad_words = ['bad', 'words', 'here']

    for word in bad_words:
        if word in message.content:
            await message.channel.send('Please treat others kindly!')

    congratulatory_words = ['congratulatory', 'words', 'here']

    for word in congratulatory_words:
        if word in message.content:
            await message.channel.send('Congratulations!')




# When a member joins the server bot welcomes them
@bot.event
async def on_member_join(member):
    await member.send(f'Welcome to the server {member.name}! I hope you enjoy your time here!')

# command to kick a member from the server
@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'{member.mention} has been treated like a soccer ball!')

# error handling for kick command
@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to kick members.")


# inactive timeout feature
@bot.event
async def on_voice_state_update(member, before, after):
    if not member.id == bot.user.id:
        return
    
    elif before.channel is None:
        voice = after.channel.guild.voice_client
        time = 0
        while True:
            await asyncio.sleep(1)
            time += 1
            if voice.is_playing() and not voice.is_paused():
                time = 0
            if time == 300:
                await voice.disconnect()
            if not voice.is_connected():
                break


# command to mute a member
@bot.command(name='mute', pass_context=True)
@has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    await member.edit(mute=True)
    await ctx.send(f'{member.mention} has been muted.')

# error handling for mute command
@mute.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to mute members.")

# command to unmute a member
@bot.command(name='unmute', pass_context=True)
@has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(mute=False)
    await ctx.send(f'{member.mention} has been unmuted.')


# error handling for unmute command
@unmute.error
async def unmute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to unmute members.")

# command to ban a member     
@bot.command(name='ban') 
@has_permissions(manage_roles=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member.mention} has been banned.')

# error handling for ban command
@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to ban members.")


# command to delete messages
@bot.command(name='clear')
@has_permissions(manage_messages=True)
async def clear(ctx, num_messages: int):
    if num_messages <= 0:
        await ctx.send('Please enter a valid number of messages to delete.')
        return
    try:
        deleted = await ctx.channel.purge(limit=num_messages+1)
        await ctx.send(f'Deleted {len(deleted)-1} messages.')
    except discord.errors.Forbidden:
        await ctx.send(f'An error occurred: {e}')

# command to mute every member in the voice channel
@bot.command(name='muteall', pass_context=True)
@has_permissions(manage_roles=True)
async def muteall(ctx):
    vc = ctx.author.voice.channel
    for member in vc.members:
        await member.edit(mute=True)

# error handling for muteall command
@muteall.error
async def muteall_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to mute members.")


# command to unmute every member in the voice channel
@bot.command(name='unmuteall', pass_context=True)
@has_permissions(manage_roles=True)
async def unmuteall(ctx):
    vc = ctx.author.voice.channel
    for member in vc.members:
        await member.edit(mute=False)

# error handling for unmuteall command
@unmuteall.error
async def unmuteall_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to unmute members.")





# replace token value here
bot.run('Put your token here')














 