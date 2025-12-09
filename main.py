import discord
import os
import logging
from dotenv import load_dotenv
from discord.ext import commands

from settings import settings
from util.storage import Storage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.storage = Storage()
logger = logging.getLogger(__name__)


@bot.event
async def on_ready():
    await bot.load_extension("cogs.events")
    await bot.load_extension("cogs.commands")
    await bot.load_extension("cogs.bridge")
    await bot.load_extension("cogs.tickets")

    guild = discord.Object(id=settings.get("guild_id"))
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    
    if settings.get("global_sync"):
        await bot.tree.sync()
    
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info(f'Loaded {len(bot.cogs)} cogs')

    bot.storage.load()
    logger.info("Storage loaded")

bot.run(os.environ["BOT_TOKEN"], log_handler=None)
