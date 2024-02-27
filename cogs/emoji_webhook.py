import discord
import discord.utils
import re
from discord.ext import commands
from discord.ext.commands import command, Context
import os
import pymongo
import asyncio

#pattern = ':\w+:($|\D)'
pattern = ':\w+:((?= )?(?=$)|(?=\D))'
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

    async def find_message(self, reference):
        channel_id = reference.channel_id
        channel = await self.bot.fetch_channel(channel_id)
        message = await channel.fetch_message(reference.message_id)
        return message


    async def send_message(self, member, channel, content, reference=None):
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
        newView = None
        if reference:
            message = await self.find_message(reference)

            new_embed = discord.Embed(type="rich", title=f"{message.clean_content}", color=discord.Color.blue(), url=message.jump_url)
            new_embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            if message.clean_content == "":
                new_embed.title = "*Jump to media*"
            await webhook.send(username=member.display_name, avatar_url=(member.display_avatar.url), embed=new_embed)
            await webhook.send(username=member.display_name, avatar_url=(member.display_avatar.url), content=content)
        else:
            await webhook.send(username=member.display_name, avatar_url=(member.display_avatar.url), content=content)
    
    async def parse_content(self, message_content):
        content = "" + message_content
        original_content = "" + message_content
        emojis_used = []
        error_messages=[]
        while re.search(pattern, content):
            emoji_name = re.search(pattern, content).group(0).split(":")[1]
            emoji = await self.get_emoji(emoji_name)
            if emoji:
                if not emoji in emojis_used:
                    emojis_used.append(emoji)
                content = re.sub(pattern, str(emoji) + " ", content, 1)
            else:
                error_messages.append(f"Emoji {emoji_name} not found")
                content = re.sub(pattern, "", content, 1)
        if len(emojis_used) == 0:
            return original_content, [], error_messages, False     
        return content, emojis_used, error_messages, True
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot == False and message.guild:
            ctx = await self.bot.get_context(message)
            if ctx.command == None:
                if re.search(pattern, message.content):
                    content, emojis_used, error_messages, todo = await self.parse_content(message.content)
                    if len(error_messages) > 0:
                        await message.channel.send(f"{str(message.author.mention)} "+ "\n".join(error_messages), delete_after=5)
                    if not todo:
                        return
                    await message.delete()
                    await self.send_message(message.author, message.channel, content, message.reference)
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