import discord
from discord.ext import commands
import sqlite3
from asyncio import TimeoutError
import helper
import random
from datetime import datetime


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
                or m.author == ctx.author
                and m.content.lower() == "n",
                timeout=60,
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
        cash_base = rows[0][9]
        rewards = {
            "Common Drop": common_id,
            "Uncommon Drop": uncommon_id,
            "Rare Drop": rare_id,
            "Epic Drop": epic_id,
            "Legendary Drop": legendary_id,
            "MYTHICAL PULL": mythical_id,
        }

        # coin/vouchers multiplier depending on number of rolls / rarity (if reward for that rarity is coins)
        multiplier = 1

        # base number to multiply by (cash_base pulled from pack-specific data above)
        voucher_base = 1

        # roll 0 or 1 every time. if 1, move on to next rarity. if 0, stop and get rarity it was on
        for drop, reward_id in rewards.items():
            if random.choice(range(11)) > 5 or drop == "MYTHICAL PULL":
                if reward_id == -1:
                    cash_rewarded = cash_base * multiplier
                    conn.execute(
                        f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                        (ctx.author.id,),
                    )
                    await ctx.channel.send(
                        f"<@{ctx.author.id}> you pulled the {drop} and got {cash_rewarded} cash!"
                    )
                elif reward_id == -2:
                    vouchers_rewarded = voucher_base * multiplier
                    conn.execute(
                        f"UPDATE Users SET vouchers = vouchers + {vouchers_rewarded} WHERE id = ?",
                        (ctx.author.id,),
                    )
                    await ctx.channel.send(
                        f"<@{ctx.author.id}> you pulled the {drop} and got {vouchers_rewarded} vouchers!"
                    )
                else:
                    cursor = conn.execute(
                        "SELECT name,total,NextNumber,image FROM CardsGeneral WHERE id = ?",
                        (reward_id,),
                    )
                    rows = cursor.fetchall()
                    next_number = rows[0][2]
                    total = rows[0][1]
                    card_name = rows[0][0]
                    # reward cash if there are no more cards to give
                    if next_number > total:
                        cash_rewarded = cash_base * multiplier
                        conn.execute(
                            f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                            (ctx.author.id,),
                        )
                        await ctx.channel.send(
                            f"<@{ctx.author.id}> you pulled the {drop}! There are no more {card_name} cards available so you got {cash_rewarded} cash instead."
                        )
                    else:
                        await ctx.channel.send(
                            f"<@{ctx.author.id}> you pulled the {drop} and got {card_name}!"
                        )
                        # send image of card to show off if mythical
                        if drop == "MYTHICAL PULL":
                            image = rows[0][3]
                            await ctx.channel.send(file=discord.File(image))
                        helper.add_card(ctx.author.id, reward_id)
                break
            else:
                multiplier += 1
        conn.commit()
        conn.close()
        return

    # check either cash or voucher balance
    @commands.command()
    async def balance(self, ctx, check_type):
        if check_type.lower() != "c" and check_type.lower() != "v":
            await ctx.channel.send("Invalid balance type...")
            return
        conn = sqlite3.connect("cards.db")
        if check_type.lower() == "c":
            cash = conn.execute(
                "SELECT cash from Users WHERE id = ?", (ctx.author.id,)
            ).fetchall()[0][0]
            await ctx.channel.send(f"You have {cash} cash.")
        else:
            vouchers = conn.execute(
                "SELECT vouchers from Users WHERE id = ?", (ctx.author.id,)
            ).fetchall()[0][0]
            await ctx.channel.send(f"You have {vouchers} vouchers.")
        conn.close()
        return

    # use vouchers to get event rewards
    @commands.command()
    async def useVouchers(self, ctx, name):
        # get specified voucher reward info, check reward exists and if it's available
        try:
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute(
                "SELECT * FROM VoucherRewards WHERE name = ?", (name,)
            )
            rows = cursor.fetchall()
            conn.close()

            if len(rows) == 0:
                await ctx.channel.send("Voucher does not exist...")
                return

            is_available = rows[0][2]
            if is_available == 0:
                raise helper.PackNotAvailableError
        except helper.PackNotAvailableError:
            await ctx.channel.send("That reward is currently not available to claim...")

        # confirm buying pack
        name = rows[0][3]
        cost = rows[0][0]

        await ctx.channel.send(
            f"Would you like to buy {name} Pack for {cost} vouchers? (y/n)"
        )

        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author
                and m.content.lower() == "y"
                or m.author == ctx.author
                and m.content.lower() == "n",
                timeout=60,
            )
            if response.content == "n":
                return
        except TimeoutError:
            await ctx.channel.send("Timeout for choice...")
            return

        # at this point, user responded with "y"

        # subtract cost from balance (if sufficient vouchers)
        try:
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute(
                "SELECT vouchers FROM Users WHERE id = ?", (ctx.author.id,)
            )
            cash = cursor.fetchall()[0][0]
            if cash < cost:
                raise helper.NotEnoughCashError
            conn.execute(
                f"UPDATE Users SET vouchers = vouchers - {cost} WHERE id = ?",
                (ctx.author.id,),
            )
            conn.commit()
        except helper.NotEnoughCashError:
            await ctx.channel.send("You do not have enough vouchers...")
            conn.close()
            return

        # give reward to user
        reward_id = rows[0][1]
        cash_rewarded = rows[0][4]
        if reward_id == -1:
            conn.execute(
                f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                (ctx.author.id,),
            )
            await ctx.channel.send(
                f"<@{ctx.author.id}> you claimed the {name} voucher and got {cash_rewarded} cash!"
            )
        else:
            helper.add_card(ctx.author.id, reward_id)
            cursor = conn.execute(
                "SELECT name,total,NextNumber FROM CardsGeneral WHERE id = ?",
                (reward_id,),
            )
            rows = cursor.fetchall()
            card_name = rows[0][0]
            next_number = rows[0][2]
            total = rows[0][1]
            await ctx.channel.send(
                f"<@{ctx.author.id}> you claimed the {name} voucher and got {card_name}!"
            )
            # if card ran out, set as unavailable
            if next_number > total:
                conn.execute(
                    "UPDATE VoucherRewards SET available = 0 WHERE name = ?", (name,)
                )
                await ctx.channel.send("There are no more of this card available...")
        conn.commit()
        conn.close()
        return

    # this asks the user a random multiple-choice question out of many questions stored in the database.
    # Every time the user gets it wrong, the bonus goes down by 100 cash until they receive 100 cash as consolation
    @commands.command()
    async def login(self, ctx):
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT LastLogin FROM Users WHERE id = ?", (ctx.author.id,)
        )
        last_login = cursor.fetchall()[0][0]
        last_login = datetime.strptime(last_login, "%m/%d/%Y").date()
        today = datetime.today().date()
        # check if already logged in
        if last_login >= today:
            await ctx.channel.send("Im afraid you've already logged in today...")
            conn.close()
            return

        cursor = conn.execute("SELECT * FROM Questions")
        questions = cursor.fetchall()
        questions_only = [row[0] for row in questions]
        conn.close()
        # range goes down by 100 each iteration until it rewards 100 cash at last iteration
        for cash in range(500, 99, -100):
            if cash == 100:
                await ctx.channel.send("Nice try today. Here is 100 cash!")
            else:
                await ctx.channel.send(f"Okay, here is your question for {cash} cash:")
                conn.close()
                selected = random.choice(questions)
                question = selected[0]
                answers = [selected[1], selected[2], selected[3], selected[4]]
                # depending on random placement of answer choices, this will be the number the user will have to input to select the right answer
                correct_choice = 0
                correct_answer = selected[5]
                await ctx.channel.send(f"**{question}**")
                for idx in range(len(answers)):
                    answer_choice = random.choice(answers)
                    if answer_choice == correct_answer:
                        correct_choice = idx + 1
                    await ctx.channel.send(f"{idx+1}: {answer_choice}")
                    answers.remove(answer_choice)
                try:
                    response = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.author == ctx.author
                        and m.content.isdigit()
                        and int(m.content) in list(range(1, 5)),
                        timeout=60,
                    )
                except TimeoutError:
                    await ctx.channel.send("Timeout for choice...")
                if int(response.content) == correct_choice:
                    await ctx.channel.send(
                        f"DING DING DING You just got {cash} cash!!! Login again tomorrow for another shot."
                    )
                    break
                else:
                    await ctx.channel.send("I'm afraid that is incorrect...")
                    questions_only.remove(question)
        # give cash and update last login
        conn = sqlite3.connect("cards.db")
        conn.execute(
            f"UPDATE Users SET cash = cash + {cash} WHERE id = ?", (ctx.author.id,)
        )
        new_login_date = today.strftime("%m/%d/%Y")
        conn.execute(
            "UPDATE Users SET LastLogin = ? WHERE id = ?",
            (
                new_login_date,
                ctx.author.id,
            ),
        )
        conn.commit()
        conn.close()


# setup cog/connection of this file to main.py
async def setup(bot):
    await bot.add_cog(Script(bot))
