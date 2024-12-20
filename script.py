import discord
from discord.ext import commands
import sqlite3
from asyncio import TimeoutError
import helper
import random


class Script(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def viewMyCards(self, ctx):
        # get users card names and numbers out of total cards
        id = ctx.author.id
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT number,general_id FROM Cards WHERE owner_id = ?", (id,)
        )
        rows = cursor.fetchall()
        general_ids = [row[1] for row in rows]
        numbers = [row[0] for row in rows]

        # get card names, total, and image of card from general database here
        names = []
        images = []
        totals = []
        for general in general_ids:
            cursor = conn.execute(
                "SELECT name,image,total FROM CardsGeneral WHERE id = ?", (general,)
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
                    f"{idx + 1}. {names[idx]} --> {numbers[idx]} of {totals[idx]}"
                )

        # allow to see one of the cards (image)
        await ctx.channel.send(
            'Select the number of a card you want to see. If you don\'t want to see a card, type "q"'
        )
        try:
            message = await self.bot.wait_for(
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
                await ctx.channel.send(
                    file=discord.File(images[int(message.content) - 1])
                )
        except TimeoutError:
            await ctx.channel.send("Timeout for choice...")
            return

    @commands.command()
    async def viewCard(self, ctx):
        # view general card name, total, and image based on id in database
        await ctx.channel.send("Select ID of the card.")
        try:
            card_id = await self.bot.wait_for(
                "message",
                check=lambda m: m.content.isdigit()
                and int(m.content) > 0
                and m.author.id == ctx.author.id,
                timeout=60,
            )
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute(
                "SELECT name,image,total FROM CardsGeneral WHERE id = ?",
                (int(card_id.content),),
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

    # this command takes in a name after the command name in Discord, then asks user if they want to buy pack.
    # it uses the ids of cards to assign rewards. The code uses -1 for coins and -2 for vouchers, which I intend to use as a voucher system for claiming event cards
    @commands.command()
    async def openPack(self, ctx, name):
        # get specified pack info, check pack exists and if it's available
        try:
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute("SELECT * FROM Packs WHERE name = ?", (name,))
            rows = cursor.fetchall()
            conn.close()

            if len(rows) == 0:
                await ctx.channel.send("Pack does not exist...")
                return

            is_available = rows[0][8]
            if is_available == 0:
                raise helper.PackNotAvailableError
        except helper.PackNotAvailableError:
            await ctx.channel.send("That pack is currently not available...")

        # confirm buying pack
        name = rows[0][0]
        cost = rows[0][1]

        await ctx.channel.send(
            f"Would you like to buy {name} Pack for {cost} cash? (y/n)"
        )

        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author
                and m.content.lower() == "y"
                or m.content.lower() == "n",
            )
            if response.content == "n":
                return
        except TimeoutError:
            await ctx.channel.send("Timeout for choice...")
            return

        # at this point, user responded with "y"

        # subtract cost from balance (if sufficient cash)
        try:
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute(
                "SELECT cash FROM Users WHERE id = ?", (ctx.author.id,)
            )
            cash = cursor.fetchall()[0][0]
            if cash < cost:
                raise helper.NotEnoughCashError
            conn.execute(
                f"UPDATE Users SET cash = cash - {cost} WHERE id = ?",
                (ctx.author.id,),
            )
            conn.commit()
        except helper.NotEnoughCashError:
            await ctx.channel.send("You do not have enough cash...")
            conn.close()
            return
        common_id = rows[0][2]
        uncommon_id = rows[0][3]
        rare_id = rows[0][4]
        epic_id = rows[0][5]
        legendary_id = rows[0][6]
        mythical_id = rows[0][7]
        rewards = {
            "Common Drop": common_id,
            "Uncommon Drop": uncommon_id,
            "Rare Drop": rare_id,
            "Epic Drop": epic_id,
            "Legendary Drop": legendary_id,
            "MYTHICAL PULL": mythical_id,
        }

        # coin/vouchers multiplier depending on number of rolls / rarity (if reward for that rarity is coins)
        cash_multiplier = 1
        voucher_multiplier = 1

        # base number to multiply by (can be altered of course)
        cash_base = 100
        voucher_base = 1

        # roll 0 or 1 every time. if 1, move on to next rarity. if 0, stop and get rarity it was on
        for drop, reward_id in rewards.items():
            if random.choice([0, 1]) == 0:
                if reward_id == -1:
                    cash_rewarded = cash_base * cash_multiplier
                    conn.execute(
                        f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                        (ctx.author.id,),
                    )
                    await ctx.channel.send(
                        f"<@{ctx.author.id}> you pulled the {drop} and got {cash_rewarded} cash!"
                    )
                elif reward_id == -2:
                    vouchers_rewarded = voucher_base * voucher_multiplier
                    conn.execute(
                        f"UPDATE Users SET vouchers = vouchers + {vouchers_rewarded} WHERE id = ?",
                        (ctx.author.id,),
                    )
                    await ctx.channel.send(
                        f"<@{ctx.author.id}> you pulled the {drop} and got {vouchers_rewarded} vouchers!"
                    )
                else:
                    helper.add_card(ctx.author.id, reward_id)
                    cursor = conn.execute(
                        "SELECT name FROM CardsGeneral WHERE id = ?", (reward_id,)
                    )
                    card_name = cursor.fetchall()[0][0]
                    await ctx.channel.send(
                        f"<@{ctx.author.id}> you pulled the {drop} and got {card_name}!"
                    )
                conn.close()


# setup cog/connection of this file to main.py
async def setup(bot):
    await bot.add_cog(Script(bot))
