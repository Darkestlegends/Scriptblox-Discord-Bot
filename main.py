import discord
from discord.ext import commands
import requests
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def search(ctx, query=None, mode='free'):
    if query is None:
        initial_embed = discord.Embed(
            title="🔍 Script Search",
            description="Use the `!search` command followed by your query to search for scripts.\n"
                        "You can also specify the search mode (default is 'free').\n"
                        "Modes: 'free', 'paid'\n"
                        "For example: `!search my script paid`\n"
                        "Please provide a query to get started!",
            color=0x3498db
        )
        await ctx.send(embed=initial_embed)
        return

    page = 1
    results_per_page = 5

    while True:
        api_url = f"https://scriptblox.com/api/script/search?q={query}&mode={mode}&page={page}"

        response = requests.get(api_url)
        data = response.json()

        if "result" in data and "scripts" in data["result"]:
            scripts = data["result"]["scripts"]

            if not scripts:
                await ctx.send("No more scripts found!")
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

            embed = discord.Embed(title=f"Search Results (Page {page}/{data['result']['totalPages']})", color=0x27ae60)

            for field_name, field_value in embed_fields:
                embed.add_field(name=field_name, value=field_value, inline=False)

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
            except asyncio.TimeoutError:
                break

        else:
            await ctx.send("No scripts found!")
            break

bot.run(TOKEN)
