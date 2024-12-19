import discord
from discord.ext import commands
import dotenv
import os
import sqlite3

intents = discord.Intents.all()
intents.message_content = True
dotenv.load_dotenv()

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.command()
async def viewCards(ctx):
    # get users card names and numbers out of total cards
    id = ctx.author.id
    conn = sqlite3.connect("cards.db")
    cursor = conn.execute(f"SELECT number,general_id FROM Cards WHERE owner_id = {id}")
    rows = cursor.fetchall()
    general_ids = [row[1] for row in rows]
    numbers = [row[0] for row in rows]

    # get card names, total, and image of card from general database here
    names = []
    images = []
    totals = []
    for general in general_ids:
        cursor = conn.execute(
            f"SELECT name,image,total FROM CardsGeneral WHERE id = {general}"
        )
        rows = cursor.fetchall()
        names = names + [row[0] for row in rows]
        images = images + [row[1] for row in rows]
        totals = totals + [row[2] for row in rows]

    # display list of card names and numbers
    for idx in range(len(names)):
        await ctx.channel.send(
            f"{idx + 1}. {names[idx]} --> {numbers[idx]} out of {totals[idx]}"
        )

    # allow to see one of the cards (image)
    await ctx.channel.send(
        'Select the number of a card you want to see. If you don\'t want to see a card, type "q"'
    )
    try:
        message = await bot.wait_for(
            "message",
            check=lambda m: m.content.isdigit()
            and int(m.content) > 0
            and int(m.content) <= len(names)
            or m.content == "q",
            timeout=60,
        )
        if message.content == "q":
            return
        else:
            await ctx.channel.send(file=discord.File(images[int(message.content) - 1]))
    except:
        await ctx.channel.send("Timeout for choice...")
        return


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
