import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, mapped_column, Mapped, Session, declarative_base, sessionmaker
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy

from discord_key_bot.common.util import get_search_name
from discord_key_bot.db import sqlalchemy_helpers, db_schema
from .db_schema import Base
from ..platform import Platform


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name = Column(String)
    pretty_name = Column(String)
    keys: Mapped[List["Key"]] = relationship(back_populates="game")

    @staticmethod
    def get(session: Session, pretty_name: str) -> "Game":
        name = get_search_name(pretty_name)
        game = session.query(Game).filter(Game.name == name).first()

        if not game:
            game = Game(name=name, pretty_name=pretty_name)
            session.add(game)

        return game

    def find_key_by_platform(self, platform: Platform) -> "Key":
        # claim the latest expiring keys first
        sorted_keys: List[Optional["Key"]] = sorted(
            self.keys, key=lambda k: datetime.datetime.max if not k.expiration else k.expiration)
        try:
            return next(key for key in sorted_keys if key.platform == platform.search_name)
        except StopIteration:
            raise ValueError


class Key(Base):
    __tablename__ = "keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    game: Mapped["Game"] = relationship(back_populates="keys")

    key = Column(String)
    platform = Column(String)

    creator_id = Column(Integer, ForeignKey("members.id"))
    creator = relationship("Member", backref="keys")
    expiration = Column(DateTime)


def _upgrade_keys(session: Session) -> None:
    def upgrade_func(ver: int) -> int:
        if ver < 1:
            sqlalchemy_helpers.table_add_column("keys", "expiration", DateTime, session)
            ver = 1

        return ver

    db_schema.upgrade(entity='keys', upgrade_func=upgrade_func, session=session)


class Guild(Base):
    __tablename__ = "guilds"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer)
    member_id = Column(Integer, ForeignKey("members.id"))


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    last_claim = Column(DateTime)

    _guilds: Mapped[List[Guild]] = relationship("Guild", cascade="all, delete-orphan")
    guilds: AssociationProxy[Guild] = association_proxy(
        "_guilds",
        "guild_id",
        creator=lambda id: Guild(guild_id=id),
        cascade_scalar_deletes=True,
    )

    @staticmethod
    def get(session: Session, member_id: int, name):
        member = session.query(Member).filter(Member.id == member_id).first()

        if not member:
            member = Member(id=member_id, name=name)
            session.add(member)

        return member


def upgrade_tables(db_session_maker: sessionmaker) -> None:
    session: Session = db_session_maker()
    _upgrade_keys(session=session)
