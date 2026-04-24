import discord
from discord import app_commands

import config


def staff_only():
    """App command check: interaction user must have at least one staff role."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        user_role_ids = {r.id for r in interaction.user.roles}
        if user_role_ids & set(config.STAFF_ROLE_IDS):
            return True
        await interaction.response.send_message(
            "You need a staff role to use this command.", ephemeral=True
        )
        return False

    return app_commands.check(predicate)
