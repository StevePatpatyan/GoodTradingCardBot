import discord
from discord.ext import commands
import dotenv
import os

intents = discord.Intents.all()
dotenv.load_dotenv()

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

    # Load the command files
    await bot.load_extension("script")
    await bot.load_extension("personalScript")


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
