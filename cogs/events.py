import os
import logging
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from settings import settings

logger = logging.getLogger(__name__)

load_dotenv()

class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ids = settings.get("auto_role_ids", [])
        for role_id in ids:
            await member.add_roles(discord.utils.get(member.guild.roles, id=int(role_id)))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.global_name == self.bot.user.global_name:
            return
        if message.channel.id != settings.get("bridge_channel_id", -1):
            return

        ip = settings.get("minecraft_endpoint")
        if not ip:
            return

        logger.info(f"Relaying message from Discord to Minecraft: {message.content}")
        async with aiohttp.ClientSession() as session:
            # POST with X-Bridge-Token, action=(literal)broadcast, message=message.content
            headers = {
                "X-Bridge-Token": os.getenv("BRIDGE_TOKEN", "")
            }
            data = {
                "action": "broadcast",
                "message": "sender=" + message.author.name + ";" + message.content
            }
            async with session.post(f"http://{ip}/discord", headers=headers, json=data) as resp:
                if resp.status != 200:
                    logger.info(f"Failed to send message to Minecraft server: {resp.status}")

async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
