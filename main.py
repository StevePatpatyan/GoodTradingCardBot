import discord
from discord.ext import commands
import dotenv
import os
import aiosqlite
import helper
import random
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import asyncio

intents = discord.Intents.all()
dotenv.load_dotenv(override=True)
TIMEZONE = ZoneInfo("US/Pacific")

# choose the group of pokecards that will randomly appear
all_pokecards = [["Bulbatig", "Varmander", "Squirtstudio", "Davorita", "Cyndascott", "Davodile", "Mieko", "Alchic", "Vantkip"]]
all_ids = [[167, 168, 169, 174, 175, 176, 181, 182, 183]]
all_shiny_ids = [[171, 172, 173, 178, 179, 180, 185, 186, 187]]
all_legendaries = ["Styoptwo", "Raysako"]
all_legendary_ids = [188, 192]
all_legendary_shiny_ids = [189, 193]
GENERATION_WORDS = ["first, second, and third"]
# NUM_GROUPS = 3
CHOSEN_POKECARD_GROUP = random.randrange(len(all_pokecards))

SHINY_CHANCE = 20

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
    # clear opening pack flags that may have been leftover from bot preemptively shutting down
    conn = await aiosqlite.connect("cards.db")
    await conn.execute("UPDATE Users SET opening_pack = 0")
    await conn.commit()
    await conn.close()
    print(f"Logged in as {bot.user.name}")

    # channel = bot.get_channel(int(os.getenv("STARTUP_CHANNEL_ID")))
    # allowed_mentions = discord.AllowedMentions(everyone=True)
    # await channel.send(content="@everyone", allowed_mentions=allowed_mentions)
    # news = os.getenv("NEWS").split("|")
    # news = "\n".join([f"- {new}" for new in news])
    # await channel.send(news)
    # Load the command files
    await bot.load_extension("script")
    await bot.load_extension("adventureScript")
    # await bot.load_extension("personalScript")
    if not hasattr(bot, "pokespawn_task"):
        bot.pokespawn_task = bot.loop.create_task(daily_pokespawn_loop(bot))

# 3 random pokemon appear once each in a day at a random time. the user can then catch it by saying catch
async def daily_pokespawn_loop(bot: commands.Bot):
    await bot.wait_until_ready()


    channel_id = int(os.getenv("STARTUP_CHANNEL_ID"))
    channel = bot.get_channel(channel_id)

    # If channel isn't cached yet, fetch it (recommended)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)

    # send message hinting about which group of pokecards will appear
    await channel.send(f"You feel a strong aura from the {GENERATION_WORDS[CHOSEN_POKECARD_GROUP]} generation.")
    while not bot.is_closed():
        now = datetime.now(TIMEZONE)

        # Next local midnight
        # next_midnight = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=TIMEZONE)
        next_midnight = datetime.combine(now.date(), time(22,0))
        seconds_left = int((next_midnight - now).total_seconds())

        # If we somehow hit midnight exactly, just roll
        if seconds_left <= 0:
            await asyncio.sleep(1)
            continue

        
        pokecards = all_pokecards[CHOSEN_POKECARD_GROUP]
        ids = all_ids[CHOSEN_POKECARD_GROUP]
        shiny_ids = all_shiny_ids[CHOSEN_POKECARD_GROUP]

        # roll to see if a legendary will appear today
        legendary_integer = random.randint(1, 5)
        legendary_index = None
        if legendary_integer == 5:
            legendary_index = random.randrange(len(all_legendaries))
            pokecards.append(all_legendaries[legendary_index])
            ids.append(all_legendary_ids[legendary_index])
            shiny_ids.append(all_legendary_shiny_ids[legendary_index])
            await channel.send("**You sense the presence of something legendary...**")

        spawn_count = len(pokecards)

        # Pick unique spawn times between now and midnight (in seconds from now)
        spawn_offsets = sorted(random.sample(range(1, seconds_left), spawn_count))

        start = datetime.now()
        for offset in spawn_offsets:
            # Sleep until the next offset from the start of this "day window"
            sleep_for = offset - (datetime.now() - start).total_seconds()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

            # Pick one of the remaining pokemon
            i = random.randrange(len(pokecards))
            name = pokecards.pop(i)
            card_id = ids.pop(i)
            shiny_card_id = shiny_ids.pop(i)

            shiny_integer = random.randint(1, SHINY_CHANCE)
            if shiny_integer == SHINY_CHANCE:
                await channel.send(content="@here", file=discord.File(f"Images/✨✨{name}✨✨.png"))
            else:
                await channel.send(content="@here", file=discord.File(f"Images/{name}.png"))

            try:
                msg = await bot.wait_for(
                    "message",
                    timeout=300,  # 5 minutes to catch
                    check=lambda m: (
                        m.channel.id == channel.id and
                        m.content.lower().strip() == "catch"
                    )
                )
                catcher_id = msg.author.id

                # punish catcher with id
               # if catcher_id == <id here>:
                 #   await channel.send(f"<@{catcher_id}> you don't have any pokeballs.")
                #else:
                if shiny_integer == 20:
                    await helper.add_card(catcher_id, shiny_card_id, True)
                    await channel.send(f"<@{catcher_id}> caught ✨✨{name}✨✨!")
                else:
                    # if catcher has shiny charm, roll again
                    if helper.has_shiny_charm(catcher_id):
                        if random.randint(1, SHINY_CHANCE) == SHINY_CHANCE: 
                            await helper.add_card(catcher_id, shiny_card_id, True)
                            await channel.send(f"<@{catcher_id}>'s shiny charm activated!!!")
                            await channel.send(f"<@{catcher_id}> caught {name}!")
                            continue

                    await helper.add_card(catcher_id, card_id, True)
                    await channel.send(f"<@{catcher_id}> caught {name}!")
            except asyncio.TimeoutError:
                await channel.send(f"{name} ran away!")

        # After last spawn, wait until midnight, then loop and reschedule
        remaining = (next_midnight - datetime.now()).total_seconds()
        if remaining > 0:
            await asyncio.sleep(remaining + 1)

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
