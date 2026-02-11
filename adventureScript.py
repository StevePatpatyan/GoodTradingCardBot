import discord
from discord.ext import commands
from asyncio import TimeoutError
import math
import os
from datetime import datetime, timezone

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
            # get a unique num h to report less redundancy when others play
            num_h = 0
            for c in username:
                num_h += ord(c)
            num_h = math.ceil(num_h / 1000) + 167
            await ctx.author.send("Yo... you look like a detective. Here's the letter... made up of literally one letter....:\n" + "```\n" + "h"*num_h + "\n```")
            await ctx.author.send("Report back to Detective PK. Make sure you tell him you found exactly this:\n**a letter with one letter**")
    @commands.command()
    # part of completing something from the DetectivePK Super Bowl Scandal Adventure
    # the user will discover this command and a code to proceed will be given
    # from the Good Trading Adventure Game https://github.com/StevePatpatyan/GoodTradingAdventures
    async def find_witness(self, ctx):
            allowed_mentions = discord.AllowedMentions(everyone=True)
            await ctx.channel.send(content=f"@everyone <@{ctx.author.id}> is searching for a witness. Type VOUCH to vouch for them.", allowed_mentions=allowed_mentions)
            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author != ctx.author and m.content == "VOUCH"
                )

                await ctx.channel.send(f"<@{ctx.author.id}> <@{response.author.id}> successfully became a witness for you! Check DMS.")
                witness_code = 67
                char_count = 3 if min(len(ctx.author.name), len(response.author.name)) >= 3 else min(len(ctx.author.name), len(response.author.name))
                for c1, c2 in zip(ctx.author.name[:char_count], response.author.name[:char_count]):
                     witness_code += ord(c1) + ord(c2)  
                await ctx.author.send(f"Your witness case ID is {witness_code}. Please report this to Detective PK promptly.")
            except TimeoutError:
                await ctx.channel.send(f"<@{ctx.author.id} you couldn't find a witness. Try again later.")

    @commands.command()
    @commands.is_owner()
    # Test the find witness command by yourself by getting the bot to say VOUCH to complete it
    async def test_vouch(self, ctx):
        await ctx.channel.send("VOUCH")

    
    @commands.command()
    @commands.is_owner()
    # Calculate the certification ID command to verify the certificate of the adventure is legit
    async def verify_cert_id(self, ctx, username: str, last_word_adventure_name: str, month: int, day: int, year: int, hour: int, minute: int, second: int):
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        unix_seconds = int(dt.timestamp())
        await ctx.author.send(unix_seconds + ord(username[0]) + ord(last_word_adventure_name[-1]))


async def setup(bot):
    await bot.add_cog(AdventureScript(bot))