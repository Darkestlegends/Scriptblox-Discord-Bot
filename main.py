import discord
from discord.ext import commands
import requests
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the environment variable
TOKEN = os.getenv("BOT_TOKEN")

# Define intents with message content enabled
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True  # Enable message content intent

# Initialize the bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Define a command to display initial information and search for scripts
@bot.command()
async def search(ctx, query=None, mode='free'):
    if query is None:
        initial_embed = discord.Embed(
            title="🔍 Script Search",
            description="To search for scripts, use the `!search` command followed by your query.\n"
                        "For example: `!search my script`\n"
                        "You can also specify the search mode (default is 'free').\n"
                        "Modes: 'free', 'paid'\n"
                        "For example: `!search my script paid`\n"
                        "Please provide a query to get started!",
            color=0x3498db  # Blue color
        )
        await ctx.send(embed=initial_embed)
        return

    # Initialize page number
    page = 1
    results_per_page = 5  # Maximum number of results per page

    while True:
        # Construct the API URL with the current page
        api_url = f"https://scriptblox.com/api/script/search?q={query}&mode={mode}&page={page}"

        # Send a GET request to the API
        response = requests.get(api_url)
        data = response.json()

        # Extract relevant script information
        if "result" in data and "scripts" in data["result"]:
            scripts = data["result"]["scripts"]

            if not scripts:
                await ctx.send("No more scripts found!")
                break

            # Create a list to accumulate fields for the embed
            embed_fields = []

            start_index = (page - 1) * results_per_page
            end_index = start_index + results_per_page
            current_page_scripts = scripts[start_index:end_index]

            for script in current_page_scripts:
                game_name = script["game"]["name"]
                title = script["title"]
                script_type = script["scriptType"]
                script_content = script["script"]
                views = script["views"]  # Get the views count
                verified = script["verified"]  # Get the verification status
                has_key = script.get("key", False)  # Get the key status, default to False if not present
                created_at = script["createdAt"]  # Timestamp when the script was created
                updated_at = script["updatedAt"]  # Timestamp when the script was last updated

                # Determine if it's free or paid
                if script_type == "free":
                    paid_or_free = "Free 💰"
                else:
                    paid_or_free = "Paid 💲"

                # Define emojis to make the field_value "alive"
                views_emoji = "👀"  # Eyes emoji
                verified_emoji = "✅" if verified else "❌"  # Checkmark or X emoji
                key_emoji = "🔑" if has_key else "🚫"  # Key or No Entry emoji

                # Truncate the script content to fit within the embed size limit
                max_content_length = 1000  # Maximum length for a single field value (reduced)

                if len(script_content) > max_content_length:
                    truncated_script_content = script_content[:max_content_length - 3] + "..."  # Truncate and add ellipsis
                else:
                    truncated_script_content = script_content

                # Create an additional field with emojis to display views, verification status, and key status
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

            # Create an embed with multiple fields for the current page
            embed = discord.Embed(title=f"Search Results (Page {page}/{data['result']['totalPages']})", color=0x27ae60)  # Green color

            for field_name, field_value in embed_fields:
                embed.add_field(name=field_name, value=field_value, inline=False)

            # Send the embed with arrow emojis for pagination
            message = await ctx.send(embed=embed)

            if page > 1:
                await message.add_reaction("⬅️")  # Left arrow emoji for the previous page

            if page < data["result"]["totalPages"]:
                await message.add_reaction("➡️")  # Right arrow emoji for the next page

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

            try:
                reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=30.0)

                if str(reaction.emoji) == "⬅️" and page > 1:
                    page -= 1
                elif str(reaction.emoji) == "➡️" and page < data["result"]["totalPages"]:
                    page += 1

                await message.clear_reactions()  # Clear reactions before moving to the next page
            except asyncio.TimeoutError:
                break

        else:
            await ctx.send("No scripts found!")
            break

# Run the bot using the TOKEN variable
bot.run(TOKEN)
