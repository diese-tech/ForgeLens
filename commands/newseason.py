import asyncio

import discord
from discord import app_commands

import config
from services import sheets_service
from commands._checks import staff_only


def setup(tree: app_commands.CommandTree) -> None:
    @tree.command(name="newseason", description="Create a new season sheet and set it as active")
    @app_commands.describe(name="Season name (e.g. Season 1, Spring 2025)")
    @staff_only()
    async def newseason(interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)

        season_name = name.strip()
        folder_name = f"{config.LEAGUE_SLUG} — {season_name}"

        await interaction.followup.send(f"Creating Drive folder and sheet for **{season_name}**…")

        try:
            folder_id = await asyncio.to_thread(
                sheets_service.create_drive_folder, folder_name, config.PARENT_DRIVE_FOLDER_ID
            )
            sheet_id  = await asyncio.to_thread(
                sheets_service.create_season_sheet, season_name, folder_id
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create season: {e}")
            return

        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        admin_channel = interaction.guild.get_channel(config.ADMIN_REPORT_CHANNEL_ID)

        summary = (
            f"✅ **{season_name}** is now active.\n"
            f"Sheet: {sheet_url}\n"
            f"To view or edit the sheet yourself, open that link and share it with your personal Google account."
        )

        await interaction.followup.send(summary)
        if admin_channel and admin_channel.id != interaction.channel_id:
            await admin_channel.send(summary)
