import discord
import os

intents = discord.Intents.all()
client = discord.Client(intents=intents)

client.run(os.environ["BOT_TOKEN"])
