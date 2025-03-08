from typing import Optional

from discord.ext import commands
from sqlalchemy.orm import Session

from discord_key_bot.db.models import Member


def is_admin(session: Session, ctx: commands.Context) -> bool:
    if ctx.bot.is_owner(ctx.author):
        return True

    member: Optional[Member] = session.query(Member).filter(Member.id == ctx.author.id).first()

    return member and member.is_admin
