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

    @app_commands.command(name="add", description="Add user to ticket")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel:
            await interaction.response.send_message("This command can only be used in a channel.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
            return

        if not user:
            await interaction.response.send_message("You must specify a user to add.", ephemeral=True)
            return

        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"Added {user.mention} to the ticket.")

    @app_commands.command(name="remove", description="Remove user from ticket")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel:
            await interaction.response.send_message("This command can only be used in a channel.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
            return

        if not user:
            await interaction.response.send_message("You must specify a user to remove.", ephemeral=True)
            return

        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"Removed {user.mention} from the ticket.")

async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
