import os
import shutil
import asyncio
from zipfile import ZipFile  
from io import BytesIO

import discord
from discord.ext import commands

import requests
from flask import Flask
from threading import Thread
from dotenv import load_dotenv


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
        await ctx.send(embed=initial_embed)
        return

    page = 1
    results_per_page = 3
    message = None

    while True:
        api_url = f"https://scriptblox.com/api/script/search?q={query}&mode={mode}&page={page}"
        response = requests.get(api_url)
        data = response.json()

        if "result" in data and "scripts" in data["result"]:
            scripts = data["result"]["scripts"]

            if not scripts:
                await ctx.send("No scripts found!")
                break

            embed_fields = []
            start_index = (page - 1) * results_per_page
            end_index = start_index + results_per_page
            current_page_scripts = scripts[start_index:end_index]

            for script in current_page_scripts:
                game_name = script["game"]["name"]
                title = script["title"]
                script_type = script["scriptType"]
                script_content = script["script"]
                views = script["views"]
                verified = script["verified"]
                has_key = script.get("key", False)
                created_at = script["createdAt"]
                updated_at = script["updatedAt"]

                if script_type == "free":
                    paid_or_free = "Free 💰"
                else:
                    paid_or_free = "Paid 💲"

                views_emoji = "👀"
                verified_emoji = "✅" if verified else "❌"
                key_emoji = "🔑" if has_key else "🚫"

                max_content_length = 1000

                if len(script_content) > max_content_length:
                    truncated_script_content = script_content[:max_content_length - 3] + "..."
                else:
                    truncated_script_content = script_content

                field_value = (
                    f"Game: {game_name} {views_emoji}\n"
                    f"Script Type: {paid_or_free} {verified_emoji}\n"
                    f"Views: {views}\n"
                    f"Verified: {verified_emoji}\n"
                    f"Key Required: {key_emoji}\n"
                    f"Created At: {created_at}\n"
                    f"Updated At: {updated_at}\n"
                    f"```lua\n{truncated_script_content}\n```"
                )

                embed_fields.append((title, field_value))

            embed = discord.Embed(title=f"Search Results (Page {page}/{data['result']['totalPages']}", color=0x27ae60)

            for field_name, field_value in embed_fields:
                embed.add_field(name=field_name, value=field_value, inline=False)

            if message:
                await message.edit(embed=embed)
            else:
                message = await ctx.send(embed=embed)

            if page > 1:
                await message.add_reaction("⬅️")

            if page < data["result"]["totalPages"]:
                await message.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

            try:
                reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=30.0)

                if str(reaction.emoji) == "⬅️" and page > 1:
                    page -= 1
                elif str(reaction.emoji) == "➡️" and page < data["result"]["totalPages"]:
                    page += 1

                await message.clear_reactions()

                embed.title = f"Search Results - Page {page}/{data['result']['totalPages']})"
                await message.edit(embed=embed)

            except asyncio.TimeoutError:
                break

        else:
            await ctx.send("No scripts found!")
            break

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

        if not scripts:
            await ctx.send(f"No scripts found for the game: {game_name}")
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

        progress_message = await ctx.send(file=discord.File(zip_content, filename=f"{game_name}_scripts.zip"))

        await loading_message.edit(embed=discord.Embed(description=":white_check_mark: Download complete!"))
        await ctx.send(f"**{game_name} scripts have been sent!**")

        if not is_replit:
            shutil.rmtree(temp_dir)
    else:
        await ctx.send(f"No scripts found for the game: {game_name}")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="LightningBot strike someone down"))

bot.run(TOKEN)
