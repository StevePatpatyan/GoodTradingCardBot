import discord
from discord.ext import commands
import dotenv
import os
import sqlite3
from asyncio import TimeoutError

intents = discord.Intents.all()
intents.message_content = True
dotenv.load_dotenv()

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.command()
async def viewMyCards(ctx):
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
        conn.close()
        names = names + [row[0] for row in rows]
        images = images + [row[1] for row in rows]
        totals = totals + [row[2] for row in rows]

    # display list of card names and numbers
    for idx in range(len(names)):
        if not totals[idx]:
            await ctx.channel.send(f"{idx + 1}. {names[idx]} --> {numbers[idx]}")
        else:
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
            and m.author.id == ctx.author.id
            or m.content == "q"
            and m.author.id == ctx.author.id,
            timeout=60,
        )
        if message.content == "q":
            return
        else:
            await ctx.channel.send(file=discord.File(images[int(message.content) - 1]))
    except TimeoutError:
        await ctx.channel.send("Timeout for choice...")
        return


@bot.command()
async def viewAllCards(ctx):
    # view general card name, total, and image based on id in database
    await ctx.channel.send("Select ID of the card.")
    try:
        card_id = await bot.wait_for(
            "message",
            check=lambda m: m.content.isdigit()
            and int(m.content) > 0
            and m.author.id == ctx.author.id,
            timeout=60,
        )
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            f"SELECT name,image,total FROM CardsGeneral WHERE id = {int(card_id.content)}"
        )
        rows = cursor.fetchall()
        conn.close()
        # card does not exist
        if len(rows) == 0:
            await ctx.channel.send("No such card...")
            return
        else:
            info = rows[0]
            await ctx.channel.send(file=discord.File(info[1]))
            if info[2]:
                await ctx.channel.send(
                    f"{info[0]}. There are {info[2]} total of this card out there!"
                )
            else:
                await ctx.channel.send(
                    f"{info[0]}. This card's population can still be increased!"
                )
    except TimeoutError:
        await ctx.channel.send("Timeout for choice...")
        return


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
