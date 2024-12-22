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
    async def viewcard(self, ctx, card_id):
        # view general card name, total, and image based on id in database
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT name,image,total FROM CardsGeneral WHERE id = ?",
            (int(card_id),),
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
            cursor = conn.execute(
                "SELECT * FROM Packs WHERE name = ?", (select_menu.values[0],)
            )
            rows = cursor.fetchall()
            conn.close()

            name = select_menu.values[0]
            if name == "Cancel Pack":
                await interaction.response.edit_message(
                    content="Cancelled pack opening...", view=None
                )
                return
            cost = rows[0][1]
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
                        # reward cash or vouchers if there are no more cards to give
                        if next_number > total:
                            mythical_cash_multiplier = 12
                            mythical_voucher_multiplier = multiplier
                            cash_andor_vouchers = "v"
                            if "c" in cash_andor_vouchers:
                                cash_rewarded = cash_base * mythical_cash_multiplier
                                conn.execute(
                                    f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                                    (ctx.author.id,),
                                )
                                await interaction.response.edit_message(
                                    content=f"<@{ctx.author.id}> you pulled the {drop}! There are no more {card_name} cards available so you got {cash_rewarded} cash instead.",
                                    view=None,
                                )
                            if "v" in cash_andor_vouchers:
                                vouchers_rewarded = (
                                    voucher_base * mythical_voucher_multiplier
                                )
                                conn.execute(
                                    f"UPDATE Users SET vouchers = vouchers + {vouchers_rewarded} WHERE id = ?",
                                    (ctx.author.id,),
                                )
                                await interaction.response.edit_message(
                                    content=f"<@{ctx.author.id}> you pulled the {drop}! There are no more {card_name} cards available so you got {vouchers_rewarded} vouchers instead.",
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
                                await ctx.channel.send(file=discord.File(image))
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
        pack_costs = [row[1] for row in rows]
        select_options = [
            discord.SelectOption(
                label=f"{name} - {cost} cash", value=name, description=description
            )
            for (
                name,
                description,
                cost,
            ) in list(zip(pack_names, pack_descriptions, pack_costs))
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
            cursor = conn.execute(
                "SELECT * FROM VoucherRewards WHERE name = ?", (select_menu.values,)
            )
            rows = cursor.fetchall()
            conn.close()

            name = select_menu.values[0]
            if name == "Cancel Voucher":
                await interaction.response.edit_message(
                    content="Cancelled voucher claim...", view=None
                )
                return
            name = select_menu.values[0]
            cost = rows[0][0]
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
        voucher_costs = [row[0] for row in rows]
        select_options = [
            discord.SelectOption(
                label=f"{name} - {cost} vouchers", value=name, description=description
            )
            for (name, description, cost) in list(
                zip(voucher_names, voucher_descriptions, voucher_costs)
            )
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
                    f"<@{interaction.user.id}> this is not your login window..."
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

    # trade with others! basic way this works is switching ids of card owner in database/giving and subtracting coins and vouchers
    # input is @user
    @commands.command()
    async def trade(self, ctx, partner):
        async def init_callback(interaction, partner):
            # the final callback function, which asks initiator of trade to choose what they want from the partner, and complete the trade/timeout
            async def partner_callback(interaction, init_values, offers):
                # make sure interactor is command invoker
                if interaction.user != ctx.author:
                    await interaction.response.send_message(
                        f"<@{interaction.user.id} this is not your trade window..."
                    )
                    return
                if "Cancel" in partner_select_menu.values:
                    await interaction.response.edit_message(
                        content="Trade cancelled...", view=None
                    )
                    return
                partner_id = int(partner[2:-1])

                # check if the user wants cash, vouchers, card, or canceled the trade
                proposals = []
                conn = sqlite3.connect("cards.db")
                for value in partner_select_menu.values:
                    if value == "cash" or value == "vouchers":
                        amount = conn.execute(
                            f"SELECT {value} FROM Users WHERE id = ?",
                            (partner_id,),
                        ).fetchall()[0][0]
                        try:
                            # make sure it is first interaction message, since it can only respond once (first time will be when cash or vouchers amount is asked for)
                            if (
                                "cash"
                                in partner_select_menu.values[
                                    : partner_select_menu.values.index(value)
                                ]
                                or "vouchers"
                                in partner_select_menu.values[
                                    : partner_select_menu.values.index(value)
                                ]
                            ):
                                await ctx.channel.send(
                                    content=f"How much {value.lower()} do you propose?",
                                    view=None,
                                )
                            else:
                                await interaction.response.edit_message(
                                    content=f"How much {value.lower()} do you propose?",
                                    view=None,
                                )
                            proposal = await self.bot.wait_for(
                                "message",
                                check=lambda m: m.author == ctx.author
                                and m.content.isdigit()
                                and int(m.content) >= 0,
                                timeout=60,
                            )
                            if int(proposal.content) > amount:
                                raise helper.NotEnoughCashError
                        except helper.NotEnoughCashError:
                            await interaction.response.edit_message(
                                content=f"This person does not have enough {init_select_menu.values[0].lower()} to offer that much... closing trade...",
                                view=None,
                            )
                            conn.close()
                            return
                        except TimeoutError:
                            await interaction.response.edit_message(
                                content="Timeout for choice...", view=None
                            )
                            conn.close()
                            return
                        proposals.append(f"{proposal.content} {value}")
                    # user offered card, decrypt the value into a structured part for the trade message
                    else:
                        proposal = " --> ".join(value.split("~"))
                        proposals.append(proposal)
                conn.close()
                # construct the trade message
                # make sure it is first interaction message, since it can only respond once (first time will be when cash or vouchers amount is asked for)
                if (
                    "cash" in partner_select_menu.values
                    or "vouchers" in partner_select_menu.values
                ):
                    await ctx.channel.send(
                        f"<@{partner_id}> <@{ctx.author.id}> is offering the following:"
                    )
                else:
                    await interaction.response.edit_message(
                        content=f"<@{partner_id}> <@{ctx.author.id}> is offering the following:",
                        view=None,
                    )
                for offer in offers:
                    await ctx.channel.send(offer)
                await ctx.channel.send("...and is asking of you the following:")
                for proposal in proposals:
                    await ctx.channel.send(proposal)
                try:
                    await ctx.channel.send("Do you accept or decline? (y/n)")
                    response = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.author.id == partner_id
                        and m.content.lower() == "y"
                        or m.author.id == partner_id
                        and m.content.lower() == "n",
                        timeout=120,
                    )
                    # exchange contents
                    if response.content.lower() == "y":
                        await ctx.channel.send("Please wait...")
                        for value, offer in list(zip(init_values, offers)):
                            if value == "cash" or value == "vouchers":
                                amount = int(offer.split(" ")[0])
                                helper.transfer(
                                    value, value, ctx.author.id, partner_id, amount
                                )
                            else:
                                helper.transfer(
                                    "card", value, ctx.author.id, partner_id
                                )

                        for value, proposals in list(
                            zip(partner_select_menu.values, proposals)
                        ):
                            if value == "cash" or value == "vouchers":
                                amount = proposal.split(" ")[0]
                                helper.transfer(
                                    value, value, partner_id, ctx.author.id, amount
                                )
                            else:
                                helper.transfer(
                                    "card", value, partner_id, ctx.author.id
                                )
                        await ctx.channel.send(
                            f"<@{partner_id}> accepted <@{ctx.author.id}>'s trade!"
                        )
                    else:
                        await ctx.channel.send(
                            f"<@{partner_id}> respectfully declined <@{ctx.author.id}>'s trade..."
                        )
                        return
                except TimeoutError:
                    await ctx.channel.send("Timeout for choice...")
                    return

            ######################## initial callback ##############################
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    f"<@{interaction.user.id} this is not your trade window..."
                )
                return
            if "Cancel" in init_select_menu.values:
                await interaction.response.edit_message(
                    content="Trade cancelled...", view=None
                )
                return
            # make select menu for partner's cards
            partner_id = partner[2:-1]
            partner_id = int(partner_id)
            conn = sqlite3.connect("cards.db")
            # check if user is in database
            if (
                len(
                    conn.execute(
                        "SELECT id FROM Users WHERE id = ?", (partner_id,)
                    ).fetchall()
                )
                == 0
            ):
                await ctx.channel.send("This user is not in the database...")
                conn.close()
                return
            cursor = conn.execute(
                "SELECT general_id,number FROM Cards WHERE owner_id = ?", (partner_id,)
            )
            rows = cursor.fetchall()
            general_ids = [row[0] for row in rows]
            numbers = [row[1] for row in rows]
            names = [
                conn.execute(
                    "SELECT name FROM CardsGeneral WHERE id = ?", (general_id,)
                ).fetchall()[0][0]
                for general_id in general_ids
            ]
            partner_select_options = [
                discord.SelectOption(
                    label=name,
                    description=f"Card number: {number} out of total",
                    value=f"{name}~#{number} out of total",
                )
                for (name, number) in list(zip(names, numbers))
            ] + [
                discord.SelectOption(label="Cash", value="cash"),
                discord.SelectOption(label="Vouchers", value="vouchers"),
                discord.SelectOption(label="Cancel Trade", value="Cancel"),
            ]
            partner_select_menu = discord.ui.Select(
                options=partner_select_options,
                custom_id="partnertrade",
                max_values=len(partner_select_options),
            )
            partner_view = discord.ui.View(timeout=60)
            partner_view.add_item(partner_select_menu)
            # check if the user offered cash, vouchers, card, or canceled the trade
            offers = []
            conn = sqlite3.connect("cards.db")
            for value in init_select_menu.values:
                if value == "cash" or value == "vouchers":
                    amount = conn.execute(
                        f"SELECT {value} FROM Users WHERE id = ?",
                        (ctx.author.id,),
                    ).fetchall()[0][0]
                    try:
                        # make sure it is first interaction message, since it can only respond once (first time will be when cash or vouchers amount is asked for)
                        if (
                            "cash"
                            in init_select_menu.values[
                                : init_select_menu.values.index(value)
                            ]
                            or "vouchers"
                            in init_select_menu.values[
                                : init_select_menu.values.index(value)
                            ]
                        ):
                            await ctx.channel.send(
                                content=f"How much {value.lower()} are you offering?",
                                view=None,
                            )
                        else:
                            await interaction.response.edit_message(
                                content=f"How much {value.lower()} are you offering?",
                                view=None,
                            )
                        offer = await self.bot.wait_for(
                            "message",
                            check=lambda m: m.author == ctx.author
                            and m.content.isdigit()
                            and int(m.content) >= 0,
                            timeout=60,
                        )
                        if int(offer.content) > amount:
                            raise helper.NotEnoughCashError
                    except helper.NotEnoughCashError:
                        await interaction.response.edit_message(
                            content=f"You do not have enough {value.lower()} to offer that much... closing trade...",
                            view=None,
                        )
                        conn.close()
                        return
                    except TimeoutError:
                        await interaction.response.edit_message(
                            content="Timeout for choice...", view=None
                        )
                        conn.close()
                        return
                    offers.append(f"{offer.content} {value}")
                # user offered a card, decrypt so that it makes sense in the trade message
                else:
                    offer = " --> ".join(value.split("~"))
                    offers.append(offer)
            conn.close()
            partner_select_menu.callback = lambda interaction: partner_callback(
                interaction, init_select_menu.values, offers
            )
            # make sure it is first interaction message, since it can only respond once (first time will be when cash or vouchers amount is asked for)
            if (
                "cash" in init_select_menu.values
                or "vouchers" in init_select_menu.values
            ):
                await ctx.channel.send(
                    "What would you like from the other person?", view=partner_view
                )
            else:
                await interaction.response.edit_message(
                    content="What would you like from the other person?",
                    view=partner_view,
                )

        ################## trade function #####################################
        # check if input was @user format
        partner_id = partner[2:-1]
        if not partner_id.isdigit():
            await ctx.channel.send("Invalid input...")
            return

        # preventing trading with self
        if int(partner_id) == ctx.author.id:
            await ctx.channel.send("You can't trade with yourself, silly...")
            return

        # create select menus for invoker/initiator's cards
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT general_id,number FROM Cards WHERE owner_id = ?", (ctx.author.id,)
        )

        rows = cursor.fetchall()
        general_ids = [row[0] for row in rows]
        numbers = [row[1] for row in rows]
        names = [
            conn.execute(
                "SELECT name FROM CardsGeneral WHERE id = ?", (general_id,)
            ).fetchall()[0][0]
            for general_id in general_ids
        ]
        init_select_options = [
            discord.SelectOption(
                label=name,
                description=f"Card number: {number} out of total",
                value=f"{name}~#{number} out of total",
            )
            for (name, number) in list(zip(names, numbers))
        ] + [
            discord.SelectOption(label="Cash", value="cash"),
            discord.SelectOption(label="Vouchers", value="vouchers"),
            discord.SelectOption(label="Cancel Trade", value="Cancel"),
        ]
        init_select_menu = discord.ui.Select(
            options=init_select_options,
            custom_id="inittrade",
            max_values=len(init_select_options),
        )

        init_view = discord.ui.View(timeout=60)
        init_view.add_item(init_select_menu)

        init_select_menu.callback = lambda interaction: init_callback(
            interaction, partner
        )

        await ctx.channel.send(
            "What are you offering?",
            view=init_view,
        )


# setup cog/connection of this file to main.py
async def setup(bot):
    await bot.add_cog(Script(bot))
