import discord
import asyncio
import cogs
import os
from discord.ext.commands import Bot, errors
from database import handler

class EnterpriseClient(Bot):
    def __init__(self, intents):
        self.db_con = handler.DatabaseConnection()
        super().__init__(command_prefix=self.get_prefix, intents=intents)
        asyncio.run(self.load_cogs())
        

    def cleanup(self):
        self.db_con.close()
    def get_database(self):
        return self.db_con
    
    async def get_prefix(self, *args):
        return ["!"]

    async def load_cogs(self):
        print("Loading cogs...")
        for file_name in os.listdir("cogs"):
            if file_name.endswith(".py"):
                print(f"Loading {file_name} cog...")
                await self.load_extension("cogs." + file_name[:-3])
    
    
