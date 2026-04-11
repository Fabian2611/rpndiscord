import asyncio
import io
import logging

import discord
from discord import ui
from discord.ext import commands

from settings import settings

logger = logging.getLogger(__name__)


async def generate_transcript(channel: discord.TextChannel) -> discord.File:
    """Helper function to generate a text transcript of a channel."""
    transcript = f"Transcript for {channel.name}\n"
    transcript += "=" * 40 + "\n\n"

    async for msg in channel.history(limit=None, oldest_first=True):
        time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        transcript += f"[{time_str}] {msg.author}: {msg.clean_content}\n"
        for att in msg.attachments:
            transcript += f"[{time_str}] {msg.author}: [Attachment] {att.url}\n"

    buffer = io.BytesIO(transcript.encode('utf-8'))
    return discord.File(fp=buffer, filename=f"transcript-{channel.name}.txt")


class TicketCreationView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    def _ensure_permissions(self, overwrites, interaction, ticket_type):
        # Add overwrites for all roles with administrator permissions
        for roleId in settings.get("admin_role_ids", []):
            role = interaction.guild.get_role(roleId)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        if not (ticket_type == "Admin"):
            # Add overwrites for all moderator roles
            for roleId in settings.get("moderator_role_ids", []):
                role = interaction.guild.get_role(roleId)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        category_id = settings.get("ticket_category_id")
        if not category_id:
            await interaction.response.send_message("Ticket-Kategorie nicht konfiguriert.", ephemeral=True)
            return

        category = self.bot.get_channel(category_id)
        if not category:
            await interaction.response.send_message("Ticket-Kategorie nicht gefunden.", ephemeral=True)
            return

        # Get next ticket number
        ticket_count = self.bot.storage.get("ticket_count", 0) + 1
        self.bot.storage.set("ticket_count", ticket_count)

        channel_name = f"ticket-{ticket_count}-{ticket_type.lower().replace(' ', '-')}"

        overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}

        self._ensure_permissions(overwrites, interaction, ticket_type)

        try:
            channel = await interaction.guild.create_text_channel(name=channel_name, category=category,
                overwrites=overwrites)

            await channel.send(
                f"Willkommen {interaction.user.mention}! Bitte beschreibe dein Problem bezüglich {ticket_type}.",
                view=TicketManagementView(self.bot))

            await interaction.response.send_message(f"Ticket erstellt: {channel.mention}", ephemeral=True)

        except Exception as e:
            logger.error(f"Failed to create ticket channel: {e}")
            await interaction.response.send_message("Fehler beim Erstellen des Ticket-Kanals.", ephemeral=True)

    @ui.button(label="Frage an Support", style=discord.ButtonStyle.primary, custom_id="ticket_support")
    async def support_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.create_ticket(interaction, "Support")

    @ui.button(label="Reports", style=discord.ButtonStyle.danger, custom_id="ticket_report")
    async def report_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.create_ticket(interaction, "Report")

    @ui.button(label="Teambewerbung", style=discord.ButtonStyle.success, custom_id="ticket_application")
    async def application_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.create_ticket(interaction, "Application")

    @ui.button(label="Adminticket", style=discord.ButtonStyle.secondary, custom_id="ticket_admin")
    async def admin_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.create_ticket(interaction, "Admin")


class TicketManagementView(ui.View):
    def __init__(self, bot, is_closed=False):
        super().__init__(timeout=None)
        self.bot = bot
        self.update_buttons(is_closed)

    def update_buttons(self, is_closed):
        for child in self.children:
            if isinstance(child, ui.Button):
                if child.custom_id == "ticket_close":
                    child.disabled = is_closed
                elif child.custom_id == "ticket_reopen":
                    child.disabled = not is_closed
                elif child.custom_id == "ticket_delete":
                    child.disabled = not is_closed
                elif child.custom_id == "ticket_transcript":
                    child.disabled = not is_closed

    @ui.button(label="Close", style=discord.ButtonStyle.secondary, custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket zu schließen.",
                                                    ephemeral=True)
            return

        overwrites = interaction.channel.overwrites

        target_user = None
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                target_user = target
                break

        if target_user:
            if overwrites[target_user].send_messages is False:
                await interaction.response.send_message("Ticket ist bereits geschlossen.", ephemeral=True)
                return
        elif interaction.channel.overwrites.get(interaction.guild.default_role,
                                                discord.PermissionOverwrite()).send_messages is False:
            await interaction.response.send_message("Ticket ist bereits geschlossen.", ephemeral=True)
            return

        if target_user:
            overwrites[target_user].send_messages = False
            await interaction.channel.set_permissions(target_user, overwrite=overwrites[target_user])
            msg = "Ticket geschlossen. Der Benutzer kann keine Nachrichten mehr senden."
        else:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
            msg = "Ticket geschlossen."

        new_view = TicketManagementView(self.bot, is_closed=True)
        await interaction.response.edit_message(view=new_view)
        await interaction.followup.send(msg)

    @ui.button(label="Reopen", style=discord.ButtonStyle.success, custom_id="ticket_reopen")
    async def reopen_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket wiederzueröffnen.",
                                                    ephemeral=True)
            return

        overwrites = interaction.channel.overwrites

        target_user = None
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                target_user = target
                break

        if target_user:
            if overwrites[target_user].send_messages is True:
                await interaction.response.send_message("Ticket ist bereits offen.", ephemeral=True)
                return

        if target_user:
            overwrites[target_user].send_messages = True
            await interaction.channel.set_permissions(target_user, overwrite=overwrites[target_user])
            msg = "Ticket wiedereröffnet."

            new_view = TicketManagementView(self.bot, is_closed=False)
            await interaction.response.edit_message(view=new_view)
            await interaction.followup.send(msg)
        else:
            await interaction.response.send_message(
                "Konnte den Ticket-Ersteller nicht finden, um das Ticket wiederzueröffnen.", ephemeral=True)

    @ui.button(label="Transkript", style=discord.ButtonStyle.primary, custom_id="ticket_transcript")
    async def transcript_button(self, interaction: discord.Interaction, button: ui.Button):
        # We process the transcript generation and send it to the user who clicked it.
        await interaction.response.defer(ephemeral=True)
        transcript_file = await generate_transcript(interaction.channel)
        await interaction.followup.send("Hier ist das Transkript für dieses Ticket:", file=transcript_file,
                                        ephemeral=True)

    @ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket zu löschen.",
                                                    ephemeral=True)
            return

        is_closed = False
        target_user = None
        for target, overwrite in interaction.channel.overwrites.items():
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                target_user = target
                if overwrite.send_messages is False:
                    is_closed = True

        if not is_closed and interaction.channel.overwrites.get(interaction.guild.default_role,
                                                                discord.PermissionOverwrite()).send_messages is False:
            is_closed = True

        if is_closed:
            await interaction.response.send_message("Ticket wird in 5 Sekunden gelöscht...")

            # Send the transcript to the ticket creator via DM before channel is deleted
            if target_user:
                try:
                    transcript_file = await generate_transcript(interaction.channel)
                    await target_user.send(
                        f"Dein Ticket **{interaction.channel.name}** auf {interaction.guild.name} wurde gelöscht. Hier ist das Transkript:",
                        file=transcript_file)
                except discord.Forbidden:
                    logger.warning(f"Could not send transcript DM to {target_user} (DMs probably closed).")

            await asyncio.sleep(5)
            await interaction.channel.delete(reason="Ticket auf Benutzeranfrage gelöscht")
        else:
            await interaction.response.send_message("Du musst das Ticket schließen, bevor du es löschen kannst.",
                                                    ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketCreationView(self.bot))
        self.bot.add_view(TicketManagementView(self.bot))
        await self.check_ticket_panel()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.check_ticket_panel()

    async def check_ticket_panel(self):
        logger.info("Setting up ticket creation panel...")
        channel_id = settings.get("ticket_creation_channel_id")
        if not channel_id:
            logger.warning("Ticket creation channel ID not configured.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.warning(f"Ticket creation channel {channel_id} not found.")
            return

        if self.bot.storage.get("ticket_panel_sent"):
            return

        await channel.send("Erstelle ein Ticket:", view=TicketCreationView(self.bot))
        self.bot.storage.set("ticket_panel_sent", True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
