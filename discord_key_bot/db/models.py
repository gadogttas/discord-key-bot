from typing import List

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, mapped_column, Mapped, Session, declarative_base
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy

from discord_key_bot.common.util import get_search_name


Base = declarative_base()


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name = Column(String)
    pretty_name = Column(String)
    keys: Mapped[List["Key"]] = relationship(back_populates="game")

    @staticmethod
    def get(session: Session, pretty_name: str):
        name = get_search_name(pretty_name)
        game = session.query(Game).filter(Game.name == name).first()

        if not game:
            game = Game(name=name, pretty_name=pretty_name)
            session.add(game)

        return game


class Key(Base):
    __tablename__ = "keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    game: Mapped["Game"] = relationship(back_populates="keys")

    key = Column(String)
    platform = Column(String)

    creator_id = Column(Integer, ForeignKey("members.id"))
    creator = relationship("Member", backref="keys")


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
