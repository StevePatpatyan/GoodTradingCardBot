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
    allowed_mentions = discord.AllowedMentions(everyone=True)
    await channel.send(content="@everyone", allowed_mentions=allowed_mentions)
    news = os.getenv("NEWS").split(",")
    news = "\n".join([f"- {new}" for new in news])
    await channel.send(news)
    # Load the command files
    await bot.load_extension("script")
    await bot.load_extension("personalScript")


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
