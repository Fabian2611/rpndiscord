import discord
from discord.ext import commands, tasks
from aiohttp import web
import os
import logging
import asyncio

from dotenv import load_dotenv
from settings import settings

logger = logging.getLogger(__name__)

load_dotenv()

class BridgeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_post('/minecraft-events', self.handle_minecraft_event)
        self.runner = None
        self.site = None
        self.port = settings.get("bridge_port", 3000)
        self.token = os.getenv("BRIDGE_TOKEN")
        self.channel_id = settings.get("bridge_channel_id", 0)
        self.info_channel_id = settings.get("info_channel_id", 0)
        self.server_status = "🟢"
        self.mc_host = settings.get("minecraft_server_host", "127.0.0.1")
        self.mc_port = settings.get("minecraft_server_port", 25565)

    async def cog_load(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        logger.info(f"Bridge web server started on port {self.port}")
        
        if settings.get("status_override") is None:
            ping_interval = settings.get("server_ping_seconds", 60)
            self.server_ping_task.change_interval(seconds=ping_interval)
            self.server_ping_task.start()

    async def cog_unload(self):
        if self.server_ping_task.is_running():
            self.server_ping_task.cancel()
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

    async def handle_minecraft_event(self, request):
        # Verify token
        auth_token = request.headers.get('X-Bridge-Token')
        if not self.token or auth_token != self.token:
            logger.warning("Unauthorized bridge request attempt")
            return web.Response(status=401, text="Unauthorized")

        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        event_type = data.get("type")
        content = data.get("content")
        player = data.get("player")
        player_count = data.get("playerCount")

        if not self.channel_id:
            logger.warning("BRIDGE_CHANNEL_ID not set, ignoring event")
            return web.Response(status=200)

        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            logger.warning(f"Channel with ID {self.channel_id} not found")
            return web.Response(status=200)

        assert self.bot.storage;

        message = None
        if event_type == "chat":
            message = f"**<{player}>** {content}"
        elif event_type == "join":
            message = f"**{player}** joined the game."
            self.bot.storage.set("player_count", player_count)
            self.bot.storage.save()
        elif event_type == "leave":
            message = f"**{player}** left the game."
            self.bot.storage.set("player_count", player_count - 1)
            self.bot.storage.save()
        if message:
            await channel.send(message)

        await self.update_player_count()

        return web.Response(status=200)

    @tasks.loop(seconds=60)
    async def server_ping_task(self):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.mc_host, self.mc_port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            self.server_status = "🟢"
        except Exception:
            self.server_status = "🔴"
        
        await self.update_player_count()

    async def update_player_count(self):
        assert self.bot.storage;
        count = self.bot.storage.get("player_count", 0)
        msgid = self.bot.storage.get("player_count_msgid", None)
        
        status_override = settings.get("status_override")
        status = status_override if status_override is not None else self.server_status
        
        template = settings.get("info_message_template", "[{status}] Aktuelle Spieleranzahl: {count}")
        content = template.format(count=count, status=status)

        if not msgid:
            message = await self.bot.get_channel(self.info_channel_id).send(content)
            self.bot.storage.set("player_count_msgid", message.id)
        else:
            try:
                message = await self.bot.get_channel(self.info_channel_id).fetch_message(msgid)
                await message.edit(content=content)
            except discord.NotFound:
                message = await self.bot.get_channel(self.info_channel_id).send(content)
                self.bot.storage.set("player_count_msgid", message.id)
        self.bot.storage.save()


async def setup(bot: commands.Bot):
    await bot.add_cog(BridgeCog(bot))

