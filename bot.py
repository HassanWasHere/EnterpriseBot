import obj.client
import discord
import os

intents = discord.Intents.all()

client = obj.client.EnterpriseClient(intents)
client.run(os.environ.get("TOKEN"))

client.cleanup()