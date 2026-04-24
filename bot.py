import asyncio

import discord
from discord.ext import commands

import config
from handlers.screenshot_handler import handle_screenshot_message
from handlers.json_handler import handle_json_message

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)


@bot.event
async def on_ready():
    from commands import status, link, result, reparse, newseason, newmatch
    for mod in (status, link, result, reparse, newseason, newmatch):
        mod.setup(bot.tree)

    await bot.tree.sync()
    print(f"Ready: {bot.user} | Slash commands synced")

    from services.sheets_service import get_active_season
    season = get_active_season()
    if season:
        print(f"Active season: {season['season_name']} ({season['sheet_id']})")
    else:
        print("No active season. Run /newseason to create one.")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == config.SCREENSHOT_CHANNEL_ID:
        await handle_screenshot_message(message)
    elif message.channel.id == config.JSON_CHANNEL_ID:
        await handle_json_message(message)

    await bot.process_commands(message)


def main():
    if not config.DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")
    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
