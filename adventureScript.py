import discord
from discord.ext import commands
from asyncio import TimeoutError
import math
import os

# https://github.com/StevePatpatyan/GoodTradingAdventures


class AdventureScript(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.dm_only()
    # allow a screenshot to be posted for verification to receive an award from an adventure
    # from the Good Trading Adventure Game https://github.com/StevePatpatyan/GoodTradingAdventures
    async def adventure_proof(self, ctx):
            await ctx.author.send("Got proof of completing an adventure? Send the screenshot here and it will be reviewed for a reward!")
            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel) and m.attachments and m.attachments[0].content_type.startswith('image')
                )
                owner_id = os.getenv("OWNER_ID")
                owner = await self.bot.fetch_user(owner_id)
                await owner.send(response.attachments[0])
                await ctx.author.send("Sent successfully. Keep and eye out...")
            except TimeoutError:
                return
            
    @commands.command()
    @commands.dm_only()
    # part of revealing something from the DetectivePK Super Bowl Scandal Adventure
    # the user will discover this command and a clue will be given
    # from the Good Trading Adventure Game https://github.com/StevePatpatyan/GoodTradingAdventures
    async def search_bot(self, ctx):
            username = ctx.author.name
            num_h = 0
            for c in username:
                num_h += ord(c)
            num_h = math.ceil(num_h / 1000) + 167
            await ctx.author.send("You found a letter... made up of literally one letter....:\n" + "h"*num_h)
            await ctx.author.send("Report back to Detective PK.")

async def setup(bot):
    await bot.add_cog(AdventureScript(bot))