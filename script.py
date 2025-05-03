import discord
from discord.ext import commands
import sqlite3
from asyncio import TimeoutError
import helper
import random
from datetime import datetime
import math
import dotenv
import os


class Script(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # format of parameter should be @user or "all" to view all cards in game
    @commands.command()
    async def viewcards(self, ctx, user):
        # check if input is valid
        if user != "all" and not user[2:-1].isdigit():
            await ctx.channel.send("Invalid input...")
            return

        async def callback(interaction, view):
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> this is not your card viewing window..."
                )
                return
            # find the select menu in which a value was clicked on
            select_menu = None
            for menu in select_menus:
                for val in menu.values:
                    if val != None:
                        select_menu = menu
            if select_menu.values[0] == "Cancel":
                await interaction.response.edit_message(
                    content="Cancelled viewing...", view=None
                )
                return
            # get users card image that they choose to display
            conn = sqlite3.connect("cards.db")
            card_name = select_menu.values[0].split("~")[0]
            cursor = conn.execute(
                "SELECT image FROM CardsGeneral WHERE name = ?", (card_name,)
            )
            rows = cursor.fetchall()
            image = rows[0][0]
            conn.close()
            # display card image
            if image.split(".")[1] == "gif":
                await ctx.channel.send(file=discord.File(image), view=view)
                await interaction.response.edit_message(view=None)
            else:
                await interaction.response.edit_message(
                    attachments=[discord.File(image)], view=view
                )
            return

        # get users card names
        conn = sqlite3.connect("cards.db")
        if user == "all":
            cursor = conn.execute(
                "SELECT id FROM CardsGeneral WHERE id != -1 AND id != -2"
            )
        else:
            id = int(user[2:-1])
            cursor = conn.execute(
                "SELECT general_id FROM Cards WHERE owner_id = ?", (id,)
            )
        rows = cursor.fetchall()
        # check if there are cards associated with the id
        if len(rows) == 0:
            await ctx.channel.send(
                "Either this user has no cards or is not in the database..."
            )
            return

        general_ids = set([row[0] for row in rows])

        # get card name and total of card from general database here
        names = []
        totals = []
        for general in general_ids:
            cursor = conn.execute(
                "SELECT name,total FROM CardsGeneral WHERE id = ?", (general,)
            )
            rows = cursor.fetchall()
            names = names + [row[0] for row in rows]
            totals = totals + [row[1] for row in rows]
        conn.close()
        totals = ["N/A" if total == None else total for total in totals]
        # make a select menu of user cards plus an option to cancel

        select_options = [
            discord.SelectOption(
                label=name,
                value=name,
                description=f"Total of this Card: {total}",
            )
            for (
                name,
                total,
            ) in list(zip(names, totals))
        ] + [discord.SelectOption(label="Cancel", value="Cancel")]
        views = []
        select_menus = []
        for idx in range(0, len(select_options), 25):
            if len(select_options) - idx >= 25:
                select_menu = discord.ui.Select(options=select_options[idx : idx + 25])
            else:
                select_menu = discord.ui.Select(
                    options=select_options[idx : len(select_options)]
                )
            view = discord.ui.View(timeout=120)
            views.append(view)
            select_menu.callback = lambda interaction: callback(interaction, view)
            select_menus.append(select_menu)
            view.add_item(select_menu)

        await ctx.channel.send("Select a card to view.")
        for view in views:
            await ctx.channel.send(view=view)
        return

    # this command takes in a name after the command name in Discord, then asks user if they want to buy pack.
    # it uses the ids of cards to assign rewards. The code uses -1 for coins and -2 for vouchers, which I intend to use as a voucher system for claiming event cards
    @commands.command()
    async def openpack(self, ctx):
        # when function runs, user confirmed choice by selecting dropdown menu option
        async def callback(interaction, view):
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
            pack_info = cursor.fetchall()
            conn.close()

            name = select_menu.values[0]
            if name == "Cancel Pack":
                await interaction.response.edit_message(
                    content="Cancelled pack opening...", view=None
                )
                return
            # ask user how many of the chosen pack they want to open at a time (min: 0, max: 10)
            await interaction.response.edit_message(
                content="How many packs would you like to open? (0-10)", view=None
            )
            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.content.isdigit(),
                )
                num_packs = int(response.content)
                if num_packs < 0 or num_packs > 10:
                    await ctx.channel.send("Invalid number to open at a time...")
                    return
                elif num_packs == 0:
                    await ctx.channel.send("Cancelled pack opening...")
                    return
                else:
                    cost = pack_info[0][1] * num_packs
            except TimeoutError:
                return
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
            except helper.NotEnoughCashError:
                await ctx.channel.send(
                    content="You do not have enough cash...", view=view
                )
                conn.close()
                return
            # open a pack/ go through rolls for each pack. add card reward ids and cash/voucher pulls to pulls list to announce pulls after the rolling loop is done
            pulls = []
            # store names of cards that ran out
            all_out = []
            name = pack_info[0][0]
            common_id = pack_info[0][2]
            uncommon_id = pack_info[0][3]
            rare_id = pack_info[0][4]
            epic_id = pack_info[0][5]
            legendary_id = pack_info[0][6]
            mythical_id = pack_info[0][7]
            cash_base = pack_info[0][9]
            voucher_base = float(pack_info[0][10])
            rewards = {
                "Common Drop": common_id,
                "Uncommon Drop": uncommon_id,
                "Rare Drop": rare_id,
                "Epic Drop": epic_id,
                "Legendary Drop": legendary_id,
                "MYTHICAL PULL": mythical_id,
            }

            for idx in range(num_packs):
                # coin/vouchers multiplier depending on number of rolls / rarity (if reward for that rarity is coins/vouchers)
                cash_multiplier = 1
                voucher_multiplier = 1

                # roll 0 or 1 every time. if 1, move on to next rarity. if 0, stop and get rarity it was on
                # decrease odds of next roll every iteration (to balance odds)
                rolls = 11
                for drop, reward_ids in rewards.items():
                    # pick a random reward out of the rarity
                    reward_ids = reward_ids.split(",")
                    reward_id = int(random.choice(reward_ids))
                    # reward current rarity (else, go next rarity and increase multipliers and rolls)
                    if random.choice(range(rolls)) >= 5 or drop == "MYTHICAL PULL":
                        if reward_id == 0:
                            pulls.append(f"- {drop} - Nothing...")
                        elif reward_id == -1:
                            cash_rewarded = cash_base * cash_multiplier
                            conn.execute(
                                f"UPDATE Users SET cash = cash + {cash_rewarded} WHERE id = ?",
                                (ctx.author.id,),
                            )
                            pulls.append(f"- {drop} - {cash_rewarded} Cash")
                        elif reward_id == -2:
                            vouchers_rewarded = round(voucher_base * voucher_multiplier)
                            conn.execute(
                                f"UPDATE Users SET vouchers = vouchers + {vouchers_rewarded} WHERE id = ?",
                                (ctx.author.id,),
                            )
                            pulls.append(f"- {drop} - {vouchers_rewarded} Vouchers")

                        # card reward
                        else:
                            helper.add_card(
                                ctx.author.id,
                                reward_id,
                                handle_connection=False,
                                conn=conn,
                            )
                            cursor = conn.execute(
                                "SELECT name,total,NextNumber,image FROM CardsGeneral WHERE id = ?",
                                (reward_id,),
                            )
                            rows = cursor.fetchall()
                            next_number = rows[0][2]
                            total = rows[0][1]
                            card_name = rows[0][0]
                            pulls.append(f"- {drop} - {card_name}")
                            # send image of card to show off if mythical
                            if drop == "MYTHICAL PULL":
                                image = rows[0][3]
                                await ctx.channel.send(file=discord.File(image))
                                # # Play special video if card is 1 of 1
                                # if total == 1:
                                #     dotenv.load_dotenv()
                                #     pull_vid = os.getenv("PULL_VID")
                                #     await ctx.channel.send(file=discord.File(pull_vid))
                            # change reward to voucher if no more of a card available in rarity
                            if total != None and next_number > total:
                                all_out.append(f"- {drop} - {card_name}")
                                reward_ids = [
                                    id if id != str(reward_id) else "-2"
                                    for id in reward_ids
                                ]
                                drop_name = drop.title().replace(" ", "")
                                reward_ids = ",".join(reward_ids)
                                conn.execute(
                                    f"UPDATE Packs SET {drop_name} = {reward_ids} WHERE name = ?",
                                    (name,),
                                )
                                # update what you can pull additionally like this so that it also updates within the pack opening without needing an extra commit
                                rewards[drop] = reward_ids
                        break
                    else:
                        cash_multiplier *= 2
                        voucher_multiplier += 1
                        rolls = math.ceil(rolls + (rolls - 10) * 1.5)
                    # ensure rewrd ids is string so that next iteration is smooth
                    if isinstance(reward_ids, list):
                        reward_ids = ",".join(reward_ids)

            # announce pulls and if any cards are no longer available
            conn.commit()
            conn.close()
            await ctx.channel.send(
                f"<@{ctx.author.id}> you pulled the following from the {name} pack(s):"
            )
            await ctx.channel.send("\n".join(pulls))
            if len(all_out) > 0:
                allowed_mentions = discord.AllowedMentions(everyone=True)
                await ctx.channel.send(
                    content=f"@everyone These cards are no longer available to pull...",
                    allowed_mentions=allowed_mentions,
                )
                await ctx.channel.send("\n".join(all_out))
            return

        # get specified all pack info
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute("SELECT * FROM Packs WHERE available = 1")
        rows = cursor.fetchall()
        conn.close()

        # make a select menu of available packs plus an option to cancel

        pack_names = [row[0] for row in rows]
        pack_descriptions = [row[11] for row in rows]
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
        view = discord.ui.View(timeout=60)
        view.add_item(select_menu)
        select_menu.callback = lambda interaction: callback(interaction, view)
        await ctx.channel.send("Select a pack to open.", view=view)
        return

    # check either cash or voucher balance
    @commands.command()
    async def balance(self, ctx, check_type):
        if (
            check_type.lower() != "c"
            and check_type.lower() != "v"
            and check_type.lower() != "e"
        ):
            await ctx.channel.send("Invalid balance type...")
            return
        conn = sqlite3.connect("cards.db")
        if check_type.lower() == "c":
            cash = conn.execute(
                "SELECT cash from Users WHERE id = ?", (ctx.author.id,)
            ).fetchall()[0][0]
            await ctx.channel.send(f"You have {cash} cash.")
        elif check_type.lower() == "v":
            vouchers = conn.execute(
                "SELECT vouchers from Users WHERE id = ?", (ctx.author.id,)
            ).fetchall()[0][0]
            await ctx.channel.send(f"You have {vouchers} vouchers.")
        else:
            event_vouchers = conn.execute(
                "SELECT EventVouchers from Users WHERE id = ?", (ctx.author.id,)
            ).fetchall()[0][0]
            await ctx.channel.send(
                f"You have {event_vouchers} vouchers for the current event."
            )
        conn.close()
        return

    # use vouchers to get event rewards
    @commands.command()
    async def usevouchers(self, ctx):
        # at this point, user selected choice
        async def callback(interaction, view):
            # check if person who interacted is the one who invoked voucher claim (so that someone doesn't open a pack for someone else)
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> this is not your voucher claim window..."
                )
                return
            # get specified voucher reward info, check reward exists and if it's available
            conn = sqlite3.connect("cards.db")
            cursor = conn.execute(
                "SELECT * FROM VoucherRewards WHERE name = ?", (select_menu.values[0],)
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
                    content="You do not have enough vouchers...", view=view
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
                    view=view,
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
                    view=view,
                )
                # if card ran out, set as unavailable
                if total != None and next_number > total:
                    conn.execute(
                        "UPDATE VoucherRewards SET available = 0 WHERE name = ?",
                        (name,),
                    )
                    await ctx.channel.send(
                        "There are no more of this card available..."
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
        view = discord.ui.View(timeout=60)
        view.add_item(select_menu)
        select_menu.callback = lambda interaction: callback(interaction, view)
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
        ################## trade function #####################################
        # check if input was @user format
        partner_id = partner[2:-1]
        if not partner_id.isdigit():
            await ctx.channel.send("Invalid input...")
            return
        partner_id = int(partner_id)
        # preventing trading with self
        if int(partner_id) == ctx.author.id:
            await ctx.channel.send("You can't trade with yourself, silly...")
            return

        # get names and numbers of initiator's cards
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT general_id,number FROM Cards WHERE owner_id = ? and tradable = 1",
            (ctx.author.id,),
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
        conn.close()
        cards_info = [
            (
                name,
                general_id,
                number,
            )
            for name, general_id, number in list(zip(names, general_ids, numbers))
        ]

        # initiator chooses cards/cash/vouchers by searching up general_id/number (number optional)
        await ctx.channel.send(
            'Select the cards you are offering by searching up the card ID and EXACT number of card out of total in this format: name:number. For cash or vouchers, use this format: cash/vouchers:amount. If you don\'t care about number, just give name. q to cancel trade. Say "done" when you have put in all your offers.'
        )
        offered_items = []
        while True:
            try:
                response = await self.bot.wait_for(
                    "message", check=lambda m: m.author == ctx.author, timeout=60
                )
                if response.content.lower() == "q":
                    await ctx.channel.send("Canceled trade...")
                    return
                if response.content.lower() == "done":
                    break
                search = response.content.split(":")
                # check if user is offering cash/vouchers
                if search[0] == "cash" or search[0] == "vouchers":
                    if (
                        len(search) == 1
                        or not search[1].isdigit()
                        or int(search[1]) < 0
                    ):
                        await ctx.channel.send("Invalid quantity input... try again.")
                        continue
                    else:
                        amount_offered = int(search[1])
                        conn = sqlite3.connect("cards.db")
                        user_amount = conn.execute(
                            f"SELECT {search[0]} FROM Users WHERE id = ?",
                            (ctx.author.id,),
                        ).fetchall()[0][0]
                        if amount_offered > int(user_amount):
                            await ctx.channel.send(
                                f"You do not have enough {search[0]} to offer that much... try again."
                            )
                            continue
                        else:
                            await ctx.channel.send(f"{search[1]} {search[0]}")
                            await ctx.channel.send("Is this correct? (y/n)")
                            try:
                                confirm = await self.bot.wait_for(
                                    "message",
                                    check=lambda m: m.author == ctx.author
                                    and m.content.lower() == "y"
                                    or m.author == ctx.author
                                    and m.content.lower() == "n",
                                    timeout=60,
                                )
                                if confirm.content.lower() == "y":
                                    offered_items.append(search)
                                    await ctx.channel.send("Item added.")
                                    continue
                                # user said no to the confirmation
                                else:
                                    await ctx.channel.send(
                                        "Okay, try searching again or confirm or cancel the trade."
                                    )
                                    continue
                            except TimeoutError:
                                await ctx.channel.send(
                                    f"<@{ctx.author.id}> your trade window has timed out..."
                                )
                                return
                searched_id = search[0]
                searched_number = None
                ############################### card offer #########################
                # non-digit id?
                if not searched_id.isdigit():
                    await ctx.channel.send(
                        "Invalid id input... try searching again or confirm or cancel."
                    )
                    continue
                if len(search) > 1:
                    searched_number = search[1]
                    # non-digit number?
                    if not searched_number.isdigit():
                        await ctx.channel.send(
                            "Invalid card number input... try searching again or confirm or cancel."
                        )
                        continue
                    searched_number = int(searched_number)

                searched_id = int(searched_id)
                results = [
                    (
                        name,
                        general_id,
                        number,
                    )
                    for name, general_id, number in cards_info
                    if searched_id == general_id
                    and searched_number == number
                    or searched_id == general_id
                    and searched_number == None
                ]

                if len(results) > 0:
                    result = results[0]
                    await ctx.channel.send(f"{result[0]} --> #{result[2]} out of total")
                    await ctx.channel.send(
                        "Is this the card you are looking for? (y/n)"
                    )
                    try:
                        confirm = await self.bot.wait_for(
                            "message",
                            check=lambda m: m.author == ctx.author
                            and m.content.lower() == "y"
                            or m.author == ctx.author
                            and m.content.lower() == "n",
                            timeout=60,
                        )
                        if confirm.content.lower() == "y":
                            offered_items.append(result)
                            await ctx.channel.send("Item added.")
                            continue
                        # user said no to the searched card found
                        else:
                            await ctx.channel.send(
                                "Okay, try searching again or confirm or cancel the trade."
                            )
                            continue
                    except TimeoutError:
                        await ctx.channel.send(
                            f"<@{ctx.author.id} your trade window has timed out..."
                        )
                        return
                # no results
                else:
                    await ctx.channel.send(
                        "No results found... Try searching again or type q to cancel the trade."
                    )
                    continue
            except TimeoutError:
                await ctx.channel.send(
                    f"<@{ctx.author.id} your trade window has timed out..."
                )
                return

        ############################## get names and numbers of partner's cards #################################
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT general_id,number FROM Cards WHERE owner_id = ? and tradable = 1",
            (partner_id,),
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
        conn.close()
        cards_info = [
            (
                name,
                general_id,
                number,
            )
            for name, general_id, number in list(zip(names, general_ids, numbers))
        ]

        # initiator chooses cards/cash/vouchers by searching up general_id/number (number optional)
        await ctx.channel.send(
            'Select the cards you want by searching up the card ID and EXACT number of card out of total in this format: name:number. For cash or vouchers, use this format: cash/vouchers:amount. If you don\'t care about number, just give name. q to cancel trade. Say "done" when you have put in all your offers.'
        )
        desired_items = []
        while True:
            try:
                response = await self.bot.wait_for(
                    "message", check=lambda m: m.author == ctx.author, timeout=60
                )
                if response.content.lower() == "q":
                    await ctx.channel.send("Canceled trade...")
                    return
                if response.content.lower() == "done":
                    break
                search = response.content.split(":")
                # check if user is offering cash/vouchers
                if search[0] == "cash" or search[0] == "vouchers":
                    if (
                        len(search) == 1
                        or not search[1].isdigit()
                        or int(search[1]) < 0
                    ):
                        await ctx.channel.send("Invalid quantity input... try again.")
                        continue
                    else:
                        amount_offered = int(search[1])
                        search[1] = amount_offered
                        conn = sqlite3.connect("cards.db")
                        user_amount = conn.execute(
                            f"SELECT {search[0]} FROM Users WHERE id = ?",
                            (partner_id,),
                        ).fetchall()[0][0]
                        if amount_offered > int(user_amount):
                            await ctx.channel.send(
                                f"This person does not have enough {search[0]} to offer that much... try again."
                            )
                            continue
                        else:
                            await ctx.channel.send(f"{search[1]} {search[0]}")
                            await ctx.channel.send("Is this correct? (y/n)")
                            try:
                                confirm = await self.bot.wait_for(
                                    "message",
                                    check=lambda m: m.author == ctx.author
                                    and m.content.lower() == "y"
                                    or m.author == ctx.author
                                    and m.content.lower() == "n",
                                    timeout=60,
                                )
                                if confirm.content.lower() == "y":
                                    desired_items.append(search)
                                    await ctx.channel.send("Item added.")
                                    continue
                                # user said no to the confirmation
                                else:
                                    await ctx.channel.send(
                                        "Okay, try searching again or confirm or cancel the trade."
                                    )
                                    continue
                            except TimeoutError:
                                await ctx.channel.send(
                                    f"<@{ctx.author.id} your trade window has timed out..."
                                )
                                return
                ################# card desire #############################
                searched_id = search[0]
                searched_number = None
                # non-digit id?
                if not searched_id.isdigit():
                    await ctx.channel.send(
                        "Invalid id input... try searching again or confirm or cancel."
                    )
                    continue
                if len(search) > 1:
                    searched_number = search[1]
                    # non-digit number?
                    if not searched_number.isdigit():
                        await ctx.channel.send(
                            "Invalid card number input... try searching again or confirm or cancel."
                        )
                        continue
                    searched_number = int(searched_number)

                searched_id = int(searched_id)
                results = [
                    (
                        name,
                        general_id,
                        number,
                    )
                    for name, general_id, number in cards_info
                    if searched_id == general_id
                    and searched_number == number
                    or searched_id == general_id
                    and searched_number == None
                ]

                if len(results) > 0:
                    result = results[0]
                    await ctx.channel.send(f"{result[0]} --> #{result[2]} out of total")
                    await ctx.channel.send(
                        "Is this the card you are looking for? (y/n)"
                    )
                    try:
                        confirm = await self.bot.wait_for(
                            "message",
                            check=lambda m: m.author == ctx.author
                            and m.content.lower() == "y"
                            or m.author == ctx.author
                            and m.content.lower() == "n",
                            timeout=60,
                        )
                        if confirm.content.lower() == "y":
                            desired_items.append(result)
                            await ctx.channel.send("Item added.")
                            continue
                        # user said no to the searched card found
                        else:
                            await ctx.channel.send(
                                "Okay, try searching again or confirm or cancel the trade."
                            )
                            continue
                    except TimeoutError:
                        await ctx.channel.send(
                            f"<@{ctx.author.id}> your trade window has timed out..."
                        )
                        return
                # no results
                else:
                    await ctx.channel.send(
                        "No results found... Try searching again or type q to cancel the trade."
                    )
                    continue
            except TimeoutError:
                await ctx.channel.send(
                    f"<@{ctx.author.id}> your trade window has timed out..."
                )
                return
        #################################### COMMENCE TRADE ###########################################
        await ctx.channel.send(
            f"<@{partner_id}> <@{ctx.author.id}> is proposing a trade!"
        )
        await ctx.channel.send("*OFFERING:*")
        for offer in offered_items:
            # offer is card
            if type(offer) == tuple:
                await ctx.channel.send(
                    f"- {offer[0]} --> Card number {offer[2]} out of total"
                )
            # offer is cash/vouchers
            else:
                await ctx.channel.send(f"- {offer[1]} {offer[0]}")
        await ctx.channel.send("*THEY WANT:*")
        for desire in desired_items:
            # offer is card
            if type(desire) == tuple:
                await ctx.channel.send(
                    f"- {desire[0]} --> Card number {desire[2]} out of total"
                )
            # offer is cash/vouchers
            else:
                await ctx.channel.send(f"- {desire[1]} {desire[0]}")

        # accept or decline #
        await ctx.channel.send("**Now... the big question is... Y OR N**")
        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == partner_id
                and m.content.lower() == "y"
                or m.author.id == partner_id
                and m.content.lower() == "n",
                timeout=120,
            )
            # if accepting trade, transfer items
            if response.content.lower() == "y":
                for offer in offered_items:
                    # card transfer
                    if type(offer) == tuple:
                        helper.transfer(
                            "card",
                            ctx.author.id,
                            partner_id,
                            name=offer[0],
                            number=offer[2],
                        )
                    # cash/voucher transfer
                    else:
                        helper.transfer(
                            offer[0], ctx.author.id, partner_id, amount=offer[1]
                        )
                for desire in desired_items:
                    # card transfer
                    if type(desire) == tuple:
                        helper.transfer(
                            "card",
                            partner_id,
                            ctx.author.id,
                            name=desire[0],
                            number=desire[2],
                        )
                    # cash/voucher transfer
                    else:
                        helper.transfer(
                            desire[0], partner_id, ctx.author.id, amount=desire[1]
                        )
                await ctx.channel.send(
                    f"<@{ctx.author.id}> <@{partner_id}> BOOOOM. THIS TRADE WAS ACCEPTED!"
                )
            # trade declined
            else:
                await ctx.channel.send(
                    f"<@{ctx.author.id}> <@{partner_id}> the trade was not accepted..."
                )
        except TimeoutError:
            await ctx.channel.send(
                f"<@{ctx.author.id}> <@{partner_id}> this trade timed out..."
            )
            return
        return

    # how many of a certain card a user has
    @commands.command()
    async def howmany(self, ctx, card_id):
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute(
            "SELECT general_id from Cards WHERE general_id = ? and owner_id = ?",
            (
                card_id,
                ctx.author.id,
            ),
        )
        rows = cursor.fetchall()
        conn.close()
        await ctx.channel.send(f"<@{ctx.author.id}> you have {len(rows)} of this card.")
        return

    @commands.command()
    # if the user has the cards in a set, they can claim the set reward for free! however the cards they use to claim become untradable/unsellable
    async def completeset(self, ctx):
        # callback runs after user chose from dropdown menu
        async def callback(interaction):
            # find the sole non-None value (which is the name of the set reward or Cancel for cancel option) inputted from all dropdown menus
            value = [menu for menu in select_menus if len(menu.values) > 0][0].values[0]
            if value == "Cancel":
                await interaction.response.edit_message(
                    content="Cancelled claim...", view=None
                )
                return

            conn = sqlite3.connect("cards.db")
            # check if user already claimed the set
            cursor = conn.execute("SELECT id FROM SetRewards WHERE name = ?", (value,))
            set_id = cursor.fetchall()[0][0]
            cursor = conn.execute(
                "SELECT SetsClaimed FROM Users WHERE id = ?", (ctx.author.id,)
            )
            sets_claimed = cursor.fetchall()[0][0].split(",")
            sets_claimed = [int(id) for id in sets_claimed if id.isdigit()]
            if set_id in sets_claimed:
                await interaction.response.edit_message(
                    content="You already claimed this reward...", view=None
                )
                conn.close()
                return

            # get the id of the reward and cards needed to claim
            cursor = conn.execute(
                "SELECT reward_id,CardsRequired,quantity FROM SetRewards WHERE name = ?",
                (value,),
            )
            row = cursor.fetchall()[0]
            reward_id = row[0]
            cards_required = row[1].split(",")
            quantity = row[2]

            # ensure user has all cards needed
            cursor = conn.execute(
                "SELECT general_id FROM Cards WHERE owner_id = ?", (ctx.author.id,)
            )
            general_ids = set([row[0] for row in cursor.fetchall()])
            unobtained_cards = []
            conn.close()
            for card in cards_required:
                if card.isdigit() and int(card) not in general_ids:
                    unobtained_cards.append(card)
            if len(unobtained_cards) > 0:
                await interaction.response.edit_message(
                    content="You do not have all the cards required to claim this set reward... Here are the cards you're missing",
                    view=None,
                )
                conn = sqlite3.connect("cards.db")
                for card in unobtained_cards:
                    name = conn.execute(
                        "SELECT name FROM CardsGeneral WHERE id = ?", (card,)
                    ).fetchall()[0][0]
                    await ctx.channel.send(f"- {name}")
                return
            # at this point, user has all cards required, so we can reward
            conn = sqlite3.connect("cards.db")
            if reward_id == -1:
                conn.execute(
                    f"UPDATE Users SET cash = cash + {quantity} WHERE id = ?",
                    (ctx.author.id,),
                )
                conn.commit()
                await interaction.response.edit_message(
                    content=f"Congrats on completing the {value} and receiving {quantity} cash!",
                    view=None,
                )
            elif reward_id == -2:
                conn = sqlite3.connect("cards.db")
                conn.execute(
                    f"UPDATE Users SET vouchers = vouchers + {quantity} WHERE id = ?",
                    (ctx.author.id,),
                )
                conn.commit()
                await interaction.response.edit_message(
                    content=f"Congrats on completing the {value} and receiving {quantity} vouchers!",
                    view=None,
                )
            # card reward
            else:
                helper.add_card(ctx.author.id, reward_id)
                conn = sqlite3.connect("cards.db")
                card_name = conn.execute(
                    "SELECT name FROM CardsGeneral WHERE id = ?", (reward_id,)
                ).fetchall()[0][0]
                await interaction.response.edit_message(
                    content=f"Congrats on completing the {value} and receiving {card_name}!",
                    view=None,
                )

            # finally, change one of the cards they turned in to untradable and mark that they claimed the set
            for card_id in cards_required:
                specific_card_id = conn.execute(
                    "SELECT id FROM Cards WHERE general_id = ? AND owner_id = ?",
                    (
                        int(card_id),
                        ctx.author.id,
                    ),
                ).fetchall()[-1][0]
                conn.execute(
                    "UPDATE Cards SET tradable = 0 WHERE id = ?", (specific_card_id,)
                )
            sets_claimed = ",".join(str(s) for s in sets_claimed)
            sets_claimed += f"{set_id},"
            conn.execute(
                "UPDATE Users SET SetsClaimed = ? WHERE id = ?",
                (
                    sets_claimed,
                    ctx.author.id,
                ),
            )
            conn.commit()
            conn.close()
            return

        # make select menus for set reward choices
        conn = sqlite3.connect("cards.db")
        cursor = conn.execute("SELECT * FROM SetRewards")
        rows = cursor.fetchall()
        conn.close()
        select_options = [
            discord.SelectOption(label=row[1], value=row[1], description=row[4])
            for row in rows
        ] + [discord.SelectOption(label="Cancel", value="Cancel")]
        views = []
        select_menus = []
        for idx in range(0, len(select_options), 25):
            view = discord.ui.View(timeout=60)
            select_menu = None
            if len(select_options) - idx >= 25:
                select_menu = discord.ui.Select(options=select_options[idx : idx + 25])
            else:
                select_menu = discord.ui.Select(
                    options=select_options[idx : len(select_options)]
                )
            select_menu.callback = callback
            select_menus.append(select_menu)
            view.add_item(select_menu)
            views.append(view)
        await ctx.channel.send("Here are all the set rewards...")
        for view in views:
            await ctx.channel.send(view=view)

    # tip someone
    @commands.command()
    async def tip(self, ctx, username, cash):
        # check if user exists in database
        conn = sqlite3.connect("cards.db")
        users = conn.execute(
            "SELECT * FROM Users WHERE username = ?", (username,)
        ).fetchall()
        if len(users) == 0:
            await ctx.channel.send("No such user...")
            return

        # transfer cash
        user_id = conn.execute(
            "SELECT id FROM Users WHERE username = ?", (username,)
        ).fetchall()[0][0]
        conn.close()
        helper.transfer("cash", ctx.author.id, user_id, amount=cash)
        await ctx.channel.send(
            f"<@{ctx.author.id}> just tipped <@{user_id}> {cash} cash!!!"
        )
        return

    @commands.command()
    # redeem an available code by using command them code right after (only one of the same code per user)
    async def code(self, ctx, code):
        conn = sqlite3.connect("cards.db")
        # get info about code
        try:
            code_info = conn.execute(
                "SELECT * FROM Codes WHERE code = ?", (code,)
            ).fetchall()[0]
            # check if already claimed by user
            codes_claimed = (
                conn.execute(
                    "SELECT CodesClaimed From Users WHERE id = ?", (ctx.author.id,)
                )
                .fetchall()[0][0]
                .split(",")
            )
            code_id = code_info[0]
            if str(code_id) in codes_claimed:
                raise helper.AlreadyClaimedError

            # check if code is available
            available = code_info[4]
            if available == 0:
                raise helper.PackNotAvailableError

            # at this point, ready to redeem.
            # store code info in different variables
            name = code_info[1]
            reward_id = code_info[2]
            quantity = None
            # reward cash
            if reward_id == -1:
                quantity = code_info[3]
                conn.execute(
                    f"UPDATE Users SET cash = cash + {quantity} WHERE id = ?",
                    (ctx.author.id,),
                )
            # reward vouchers
            elif reward_id == -2:
                quantity = code_info[3]
                conn.execute(
                    f"UPDATE Users SET vouchers = vouchers + {quantity} WHERE id = ?",
                    (ctx.author.id,),
                )
            # reward card
            else:
                helper.add_card(
                    ctx.author.id, reward_id, handle_connection=False, conn=conn
                )

            # add to user's codes claimed (reusable code = -1 id if you wish. To prevent multiple entries in rapid time, you can remove this manually from database later.)
            # if code_id != -1:
            codes_claimed = ",".join(str(s) for s in codes_claimed)
            codes_claimed += f"{code_id},"
            conn.execute(
                f"UPDATE Users SET CodesClaimed = ? WHERE id = ?",
                (
                    codes_claimed,
                    ctx.author.id,
                ),
            )

            # display message for success
            await ctx.channel.send(
                f"<@{ctx.author.id}> You have successfully claimed {name}!"
            )

        # if code does not exist
        except IndexError:
            await ctx.channel.send(f"<@{ctx.author.id}> The code does not exist...")
        # if user already claimed code
        except helper.AlreadyClaimedError:
            await ctx.channel.send(
                f"<@{ctx.author.id}> You already claimed this code..."
            )
        # if code is not available
        except helper.PackNotAvailableError:
            await ctx.channel.send(f"<@{ctx.author.id}> This code is not available...")
        # resolve
        finally:
            conn.commit()
            conn.close()
            return


# setup cog/connection of this file to main.py
async def setup(bot):
    await bot.add_cog(Script(bot))
