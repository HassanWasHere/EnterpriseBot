import discord
import discord.utils
import re
from discord.ext import commands
from discord.ext.commands import command, Context
import os
import pymongo
import asyncio

pattern = ':\w+:($|\D)'

class EmojiWebhook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji_directory = os.environ.get("emoji_dir")
        self.holding_guild = None
        self.uploaded_emojis = dict()

    async def setup_emoji_holding_guild(self):
        guild_id = self.bot.db_con.get_emoji_holding_server()
        if guild_id:
            try:
                self.holding_guild = await self.bot.fetch_guild(guild_id)
            except discord.NotFound:
                self.bot.db_con.remove_webhook(guild_id.id)
            except discord.HTTPException as a:
                print(a)
        if self.holding_guild == None:
            self.holding_guild = await self.bot.create_guild(name="Test")
            self.bot.db_con.add_emoji_holding_server(self.holding_guild.id)
        return self.holding_guild
    
    async def get_holding_guild(self):
        if self.holding_guild:
            return self.holding_guild
        else:
            guild= await self.setup_emoji_holding_guild()
            return guild

    async def upload_emoji(self, guild, given_name):
        emoji_dir = self.get_emoji_file(given_name)
        if emoji_dir:
            with open(emoji_dir, "rb") as img:
                img_byte = img.read()
                emoji = await guild.create_custom_emoji(name = given_name.lower(), image = img_byte)
                return emoji

    def get_emoji_file(self, given_name):
        if os.path.exists(self.emoji_directory):
            for file_name in os.listdir(self.emoji_directory):
                prefix = file_name.split(".")
                if prefix and prefix[0]:
                    if prefix[0].lower() == given_name.lower():
                        return f"{self.emoji_directory}/{file_name}"
        return False
    
    async def get_emoji(self, given_name):
        if given_name in self.uploaded_emojis:
            return self.uploaded_emojis[given_name]
        else:
            holding_guild = await self.get_holding_guild()
            emoji = await self.upload_emoji(holding_guild, given_name)
            self.uploaded_emojis[given_name] = emoji
            return emoji

    async def delete_emoji(self, emojis_used):
        for emoji in emojis_used:
            await emoji.delete()
            clone = self.uploaded_emojis.copy().items()
            for key, value in clone:
                if value == emoji:
                    del self.uploaded_emojis[key]


    async def send_message(self, member, channel, content):
        webhook_data = self.bot.db_con.get_webhook(channel.id)
        webhook = None
        if webhook_data:
            try:
                webhook = await self.bot.fetch_webhook(webhook_data["webhook_id"])
            except discord.NotFound:
                self.bot.db_con.remove_webhook(channel.id)
            except discord.HTTPException as a:
                print(a)
        if webhook == None:
            webhook = await channel.create_webhook(name="Test")
            self.bot.db_con.add_webhook(channel.id, webhook.id)
        await webhook.edit(name=member.display_name, avatar=(await member.display_avatar.read()))   
        await webhook.send(content=content)

    
    async def parse_content(self, message_content):
        content = "" + message_content
        emojis_used = []
        while re.search(pattern, content):
            emoji_name = re.search(pattern, content).group(0).split(":")[1]
            emoji = await self.get_emoji(emoji_name)
            if not emoji in emojis_used:
                emojis_used.append(emoji)
            content = re.sub(pattern, str(emoji) + " ", content, 1)
        return content, emojis_used
        

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot == False and message.guild:
            ctx = await self.bot.get_context(message)
            if ctx.command == None:
                if re.search(pattern, message.content):
                    content, emojis_used = await self.parse_content(message.content)
                    await message.delete()
                    await self.send_message(message.author, message.channel, content)
                    await self.delete_emoji(emojis_used)
        

    @commands.hybrid_command(name="say", description="Type a message using the Enterprise bot")
    async def say(self, ctx, message):
        content, emojis_used = await self.parse_content(message)
        await self.send_message(ctx.author, ctx.channel, content)
        await ctx.reply("Success!", delete_after=True)
        await self.delete_emoji(emojis_used)

    @commands.hybrid_command(name="sync", description="Sync command tree")
    async def sync(self, ctx):
        await self.bot.tree.sync()

    @commands.hybrid_command(name="eval", description="Evaluate python expression")
    async def ev(self, ctx, message):
        if ctx.author.id == 212552746879025154:
            output = eval(message)
            await ctx.reply(output)

    @commands.hybrid_command(name="exec", description="Execute python expression")
    async def ex(self, ctx, message):
        if ctx.author.id == 212552746879025154:
            exec(message)


async def setup(bot):
    await bot.add_cog(EmojiWebhook(bot))