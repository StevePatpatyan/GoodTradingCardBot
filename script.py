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
    async def viewmycards(self, ctx):
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
            names = names + [row[0] for row in rows]
            images = images + [row[1] for row in rows]
            totals = totals + [row[2] for row in rows]
        conn.close()
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
    async def viewcard(self, ctx):
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
    async def openpack(self, ctx):
        # when function runs, user confirmed choice by selecting dropdown menu option
        async def callback(interaction):
            # check if person who interacted is the one who invoked open pack (so that someone doesn't open a pack for someone else)
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> this is not your pack opening..."
                )
                return
            # get specified all available pack info
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute("SELECT * FROM Packs WHERE available = 1")
            rows = cursor.fetchall()
            conn.close()

            name = select_menu.values[0]
            if name == "Cancel Pack":
                await interaction.response.edit_message(
                    content="Cancelled pack opening...", view=None
                )
                return
            cost = [row[1] for row in rows if row[0] == name][0]
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
                await interaction.response.edit_message(
                    content="You do not have enough cash...", view=None
                )
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
                        await interaction.response.edit_message(
                            content=f"<@{ctx.author.id}> you pulled the {drop} and got {cash_rewarded} cash!",
                            view=None,
                        )
                    elif reward_id == -2:
                        vouchers_rewarded = voucher_base * multiplier
                        conn.execute(
                            f"UPDATE Users SET vouchers = vouchers + {vouchers_rewarded} WHERE id = ?",
                            (ctx.author.id,),
                        )
                        await interaction.response.edit_message(
                            content=f"<@{ctx.author.id}> you pulled the {drop} and got {vouchers_rewarded} vouchers!",
                            view=None,
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
                            await interaction.response.edit_message(
                                content=f"<@{ctx.author.id}> you pulled the {drop}! There are no more {card_name} cards available so you got {cash_rewarded} cash instead.",
                                view=None,
                            )
                        else:
                            await interaction.response.edit_message(
                                content=f"<@{ctx.author.id}> you pulled the {drop} and got {card_name}!",
                                view=None,
                            )
                            # send image of card to show off if mythical
                            if drop == "MYTHICAL PULL":
                                image = rows[0][3]
                                await interaction.response.edit_message(
                                    file=discord.File(image)
                                )
                            helper.add_card(ctx.author.id, reward_id)
                    break
                else:
                    multiplier += 1
            conn.commit()
            conn.close()

        # get specified all pack info
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute("SELECT * FROM Packs WHERE available = 1")
        rows = cursor.fetchall()
        conn.close()

        # make a select menu of available packs plus an option to cancel

        pack_names = [row[0] for row in rows]
        pack_descriptions = [row[10] for row in rows]
        select_options = [
            discord.SelectOption(label=name, value=name, description=description)
            for (
                name,
                description,
            ) in list(zip(pack_names, pack_descriptions))
        ] + [discord.SelectOption(label="Cancel", value="Cancel Pack")]

        select_menu = discord.ui.Select(options=select_options, custom_id="packs")
        select_menu.callback = callback
        view = discord.ui.View(timeout=60)
        view.add_item(select_menu)
        await ctx.channel.send("Select a pack to open.", view=view)
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
    async def usevouchers(self, ctx):
        # at this point, user selected choice
        async def callback(interaction):
            # check if person who interacted is the one who invoked voucher claim (so that someone doesn't open a pack for someone else)
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> this is not your voucher claim window..."
                )
                return
            # get specified voucher reward info, check reward exists and if it's available
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute("SELECT * FROM VoucherRewards WHERE available = 1")
            rows = cursor.fetchall()
            conn.close()

            name = select_menu.values[0]
            if name == "Cancel Voucher":
                await interaction.response.edit_message(
                    content="Cancelled voucher claim...", view=None
                )
                return
            name = select_menu.values[0]
            cost = [row[0] for row in rows if row[3] == name][0]
            # subtract cost from balance (if sufficient vouchers)
            try:
                conn = sqlite3.connect("cards.db")
                cursor = conn.execute(
                    "SELECT vouchers FROM Users WHERE id = ?", (ctx.author.id,)
                )
                vouchers = cursor.fetchall()[0][0]
                if vouchers < cost:
                    raise helper.NotEnoughCashError
                conn.execute(
                    f"UPDATE Users SET vouchers = vouchers - {cost} WHERE id = ?",
                    (ctx.author.id,),
                )
                conn.commit()
            except helper.NotEnoughCashError:
                await interaction.response.edit_message(
                    content="You do not have enough vouchers...", view=None
                )
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
                await interaction.response.edit_message(
                    content=f"<@{ctx.author.id}> you claimed the {name} voucher and got {cash_rewarded} cash!",
                    view=None,
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
                await interaction.response.edit_message(
                    content=f"<@{ctx.author.id}> you claimed the {name} voucher and got {card_name}!",
                    view=None,
                )
                # if card ran out, set as unavailable
                if next_number > total:
                    conn.execute(
                        "UPDATE VoucherRewards SET available = 0 WHERE name = ?",
                        (name,),
                    )
                    await interaction.response.edit_message(
                        content="There are no more of this card available...", view=None
                    )
            conn.commit()
            conn.close()

        # get specified voucher reward info, check reward exists and if it's available
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute("SELECT * FROM VoucherRewards WHERE available = 1")
        rows = cursor.fetchall()
        conn.close()

        # make a select menu of available packs
        voucher_names = [row[3] for row in rows]
        voucher_descriptions = [row[5] for row in rows]
        select_options = [
            discord.SelectOption(label=name, value=name, description=description)
            for (
                name,
                description,
            ) in list(zip(voucher_names, voucher_descriptions))
        ] + [discord.SelectOption(label="Cancel", value="Cancel Voucher")]
        select_menu = discord.ui.Select(
            options=select_options, custom_id="voucherrewards"
        )
        select_menu.callback = callback
        view = discord.ui.View(timeout=60)
        view.add_item(select_menu)
        await ctx.channel.send("Select a voucher reward to open.", view=view)
        return

    # this asks the user a random multiple-choice question out of many questions stored in the database.
    # Every time the user gets it wrong, the bonus goes down by 100 cash until they receive 100 cash as consolation
    @commands.command()
    async def login(self, ctx):
        # function when user selects and answer
        async def callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> this is not your voucher claim window..."
                )
                return
            cash_rewarded = 250
            # check if answer is correct
            if select_menu.values[0] == "correct":
                cash_rewarded = cash_rewarded * 2
                await interaction.response.edit_message(
                    content=f"DING DING DING You just got {cash_rewarded} cash!!! Login again tomorrow for another shot.",
                    view=None,
                )
            else:
                await interaction.response.edit_message(
                    content=f"I'm afraid that is incorrect... you still get {cash_rewarded} cash! Login again tomorrow for another shot.",
                    view=None,
                )
            # give cash and update last login
            conn = sqlite3.connect("cards.db")
            conn.execute(
                f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                (ctx.author.id,),
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
            return

        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT LastLogin FROM Users WHERE id = ?", (ctx.author.id,)
        )
        last_login = cursor.fetchall()[0][0]
        last_login = datetime.strptime(last_login, "%m/%d/%Y").date()
        today = datetime.today().date()
        # check if already logged in
        if last_login >= today:
            await ctx.channel.send("I'm afraid you've already logged in today...")
            conn.close()
            return
        # get question to answer
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute("SELECT * FROM Questions")
        questions = cursor.fetchall()
        conn.close()
        selected = random.choice(questions)
        question = selected[0]
        answers = [selected[1], selected[2], selected[3], selected[4]]
        correct = selected[5]
        # create select menu for login question for user to answer, marking correct answer for interaction function to recognize which option is correct
        select_options = [
            (
                discord.SelectOption(label=answer, value="correct")
                if answer == correct
                else discord.SelectOption(label=answer, value=answer)
            )
            for answer in answers
        ]
        select_menu = discord.ui.Select(options=select_options, custom_id="login")
        select_menu.callback = callback
        view = discord.ui.View(timeout=60)
        view.add_item(select_menu)
        cash_rewarded = 250
        await ctx.channel.send(
            f"I can give you {cash_rewarded} cash today... OR YOU CAN DOUBLE IT IF YOU ANSWER THE FOLLOWING QUESTION CORRECTLY!!!"
        )
        await ctx.channel.send(f"**{question}**", view=view)


# setup cog/connection of this file to main.py
async def setup(bot):
    await bot.add_cog(Script(bot))
