import discord
from discord.ext import commands
import dotenv
import os

intents = discord.Intents.all()
dotenv.load_dotenv(override=True)

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    channel = bot.get_channel(int(os.getenv("STARTUP_CHANNEL_ID")))
    await channel.send("I am up! Here is the recent news for the bot:")
    await channel.send(os.getenv("NEWS"))
    # Load the command files
    await bot.load_extension("script")
    await bot.load_extension("personalScript")


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
