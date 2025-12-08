import discord
import logging
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

class CommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Pong!")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")



async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
