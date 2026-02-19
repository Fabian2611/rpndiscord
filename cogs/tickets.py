import discord
from discord.ext import commands
from discord import ui
import logging
from settings import settings

logger = logging.getLogger(__name__)

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

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        self._ensure_permissions(overwrites, interaction, ticket_type)

        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )
            
            await channel.send(
                f"Willkommen {interaction.user.mention}! Bitte beschreibe dein Problem bezüglich {ticket_type}.",
                view=TicketManagementView(self.bot)
            )
            
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

    @ui.button(label="Close", style=discord.ButtonStyle.secondary, custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket zu schließen.", ephemeral=True)
            return

        # Disable sending messages for the user
        overwrites = interaction.channel.overwrites
        
        # Find the user overwrite (not bot, not default role)
        target_user = None
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                target_user = target
                break
        
        # Check if already closed
        if target_user:
            if overwrites[target_user].send_messages is False:
                await interaction.response.send_message("Ticket ist bereits geschlossen.", ephemeral=True)
                return
        elif interaction.channel.overwrites.get(interaction.guild.default_role, discord.PermissionOverwrite()).send_messages is False:
            await interaction.response.send_message("Ticket ist bereits geschlossen.", ephemeral=True)
            return

        if target_user:
            overwrites[target_user].send_messages = False
            await interaction.channel.set_permissions(target_user, overwrite=overwrites[target_user])
            msg = "Ticket geschlossen. Der Benutzer kann keine Nachrichten mehr senden."
        else:
            # Fallback if we can't find specific user, just lock for everyone except bot
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
            msg = "Ticket geschlossen."

        new_view = TicketManagementView(self.bot, is_closed=True)
        await interaction.response.edit_message(view=new_view)
        await interaction.followup.send(msg)

    @ui.button(label="Reopen", style=discord.ButtonStyle.success, custom_id="ticket_reopen")
    async def reopen_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket wiederzueröffnen.", ephemeral=True)
            return

        # Re-enable sending messages
        overwrites = interaction.channel.overwrites
        
        target_user = None
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                target_user = target
                break
        
        # Check if already open
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
            await interaction.response.send_message("Konnte den Ticket-Ersteller nicht finden, um das Ticket wiederzueröffnen.")

    @ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket zu löschen.", ephemeral=True)
            return

        # Check if closed (user cannot send messages)
        is_closed = False
        for target, overwrite in interaction.channel.overwrites.items():
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                if overwrite.send_messages is False:
                    is_closed = True
                    break
        
        if not is_closed and interaction.channel.overwrites.get(interaction.guild.default_role, discord.PermissionOverwrite()).send_messages is False:
            is_closed = True
        
        if is_closed:
            await interaction.response.send_message("Ticket wird in 5 Sekunden gelöscht...")
            await interaction.channel.delete(reason="Ticket auf Benutzeranfrage gelöscht")
        else:
            await interaction.response.send_message("Du musst das Ticket schließen, bevor du es löschen kannst.", ephemeral=True)

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

        # Check if message already exists to avoid spamming
        if self.bot.storage.get("ticket_panel_sent"):
            return

        await channel.send(
            "Erstelle ein Ticket:",
            view=TicketCreationView(self.bot)
        )
        self.bot.storage.set("ticket_panel_sent", True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
