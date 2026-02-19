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

logger = logging.getLogger(__name__)

class MyBot(commands.Bot):
    storage: Storage

    async def setup_hook(self):
        self.storage = Storage()
        await self.load_extension("cogs.events")
        await self.load_extension("cogs.commands")
        await self.load_extension("cogs.bridge")
        await self.load_extension("cogs.tickets")
        logger.info("Extensions loaded")

    async def on_ready(self):
        guild = discord.Object(id=settings.get("guild_id"))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        if settings.get("global_sync"):
            await self.tree.sync()

        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Loaded {len(self.cogs)} cogs')

intents = discord.Intents.all()
bot = MyBot(command_prefix="!", intents=intents)
bot.run(os.environ["BOT_TOKEN"], log_handler=None)
