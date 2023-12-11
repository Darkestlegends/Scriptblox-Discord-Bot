import discord
from discord.ext import commands
import requests
import os
from flask import Flask
from threading import Thread
import asyncio
from dotenv import load_dotenv
import shutil
from zipfile import ZipFile
from io import BytesIO

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

app = Flask(__name__)

# Variable to track whether the Flask app is already running
flask_running = False

@app.route('/')
def hello_world():
    return 'Pin this tab in your browser to keep the bot alive - from sleepyvibes'

def run_flask():
    global flask_running
    if not flask_running:
        app.run(host='0.0.0.0', port=8080)
        flask_running = True

flask_thread = Thread(target=run_flask)
flask_thread.start()

# Function to handle the download action
async def handle_download(ctx, game_name, scripts):
    if not scripts:
        await ctx.send("No scripts found!")
        return

    is_replit = "REPLIT_DB_URL" in os.environ
    temp_dir = f"/tmp/game_scripts_for_{game_name.replace(' ', '_')}" if is_replit else f"game_scripts_for_{game_name.replace(' ', '_')}"
    os.makedirs(temp_dir, exist_ok=True)

    # Write scripts to individual files
    for script in scripts:
        title = script["title"]
        script_content = script["script"]
        sanitized_title = title.replace(' ', '_')
        filename = os.path.join(temp_dir, f"{sanitized_title}.lua")

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(script_content)

    # Create a BytesIO object to store the zip file content in memory
    zip_content = BytesIO()

    # Write files to the ZIP archive
    with ZipFile(zip_content, 'w') as zip_file:
        for script in scripts:
            title = script["title"]
            filename = os.path.join(temp_dir, f"{title.replace(' ', '_')}.lua")
            zip_file.write(filename, os.path.basename(filename))

    zip_content.seek(0)

    loading_message = await ctx.send(embed=discord.Embed(description=":hourglass_flowing_sand: Loading..."))
    await asyncio.sleep(4)

    await ctx.author.send(file=discord.File(zip_content, filename=f"{game_name}_scripts.zip"))

    await loading_message.edit(embed=discord.Embed(description=":white_check_mark: Download complete! Check your DMs."))
    await ctx.send(f"**{game_name} scripts have been sent to your DMs!**")

    if not is_replit:
        shutil.rmtree(temp_dir)

@bot.command()
async def search(ctx, query=None, mode='free'):
    if query is None:
        initial_embed = discord.Embed(
            title="🔍 Script Search",
            description="Use the `.search` command followed by your query to search for scripts.\n"
                        "You can also specify the search mode (default is 'free').\n"
                        "Modes: 'free', 'paid'\n"
                        "For example: `.search my script paid`\n"
                        "Please provide a query to get started!",
            color=0x3498db
        )
        message = await ctx.send(embed=initial_embed)
        await message.add_reaction("⬇️")  # Add the download emoji reaction
        return

    # ... (rest of the search command)

# Function to handle the search result download action
async def handle_search_download(ctx, game_name, scripts):
    await handle_download(ctx, game_name, scripts)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:  # Ignore reactions from the bot itself
        return

    message = reaction.message

    if message.author == bot.user:  # Check if the message is sent by the bot
        if str(reaction.emoji) == "⬇️":  # Check for the download emoji reaction
            query = message.embeds[0].title.split()[-1]  # Extract the query from the embed title
            await message.delete()  # Remove the original search message
            await search_and_download(message.channel, query)

# Function to perform search and initiate download
async def search_and_download(channel, query):
    api_url = f"https://scriptblox.com/api/script/search?q={query}"
    response = requests.get(api_url)
    data = response.json()

    if "result" in data and "scripts" in data["result"]:
        scripts = data["result"]["scripts"]
        await handle_search_download(channel, query, scripts)
    else:
        await channel.send(f"No scripts found for the query: {query}")

@bot.command()
async def download(ctx, game_name=None):
    if game_name is None:
        await ctx.send("Please provide the name of the game to download scripts.")
        return

    api_url = f"https://scriptblox.com/api/script/search?q={game_name}"
    response = requests.get(api_url)
    data = response.json()

    if "result" in data and "scripts" in data["result"]:
        scripts = data["result"]["scripts"]
        await handle_download(ctx, game_name, scripts)
    else:
        await ctx.send(f"No scripts found for the game: {game_name}")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="LightningBot strike someone down"))

bot.run(TOKEN)
