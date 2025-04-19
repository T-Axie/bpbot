import discord
from discord.ext import commands, tasks
import datetime
import os

# === Charger la config depuis les variables d’environnement ===
TOKEN = os.getenv("token")
GUILD_ID = int(os.getenv("guild_id"))
CATEGORY_TOURNOIS_ID = int(os.getenv("category_tournois_id"))
CATEGORY_ARCHIVES_ID = int(os.getenv("category_archives_id"))
PLANNING_CHANNEL_ID = int(os.getenv("planning_channel_id"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_messages = {}
tracked_links = {}

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    archive_old_tournaments.start()


@bot.command()
async def addtournoi(ctx, *, contenu):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)

    # Découper contenu (ex: "27 avril Ravensburg https://link")
    parts = contenu.split()
    lien = parts[-1] if parts[-1].startswith("http") else ""
    titre = " ".join(parts[:-1]) if lien else contenu
    channel_name = titre.lower().replace(" ", "-").replace("/", "-")

    new_channel = await guild.create_text_channel(
        channel_name,
        category=category
    )

    msg = await new_channel.send(
        f"📅 **Participation au tournoi : {titre}**\n"
        f"Réagis avec :\n"
        f"✅ = Je participe\n❓ = À confirmer\n❌ = Je ne viens pas\n🚗 = Je viens en voiture (lift possible)\n\n"
        f"{lien}"
    )

    await msg.add_reaction("✅")
    await msg.add_reaction("❓")
    await msg.add_reaction("❌")
    await msg.add_reaction("🚗")
    await msg.pin()

    await ctx.send(f"Salon créé : {new_channel.mention}")
    tracked_messages[msg.id] = new_channel.id
    tracked_links[msg.id] = lien


@bot.command()
async def planning(ctx):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    salons = category.text_channels

    # Trier les salons par date dans leur nom
    def extract_date_key(channel):
        try:
            mots = channel.name.replace("-", " ").split()
            jour = int(mots[0])
            mois_str = mots[1].lower()
            mois_map = {
                "janvier": 1, "février": 2, "mars": 3, "avril": 4,
                "mai": 5, "juin": 6, "juillet": 7, "août": 8,
                "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
            }
            mois = mois_map.get(mois_str, 0)
            return datetime.date(2025, mois, jour)
        except:
            return datetime.date(2025, 12, 31)

    salons_sorted = sorted(salons, key=extract_date_key)

    planning_lines = ["📅 **Planning Tournois en cours :**\n"]
    for chan in salons_sorted:
        planning_lines.append(f"📍 {chan.name.replace('-', ' ').title()} → {chan.mention}")

    planning_channel = guild.get_channel(PLANNING_CHANNEL_ID)
    await planning_channel.send("\n".join(planning_lines))


@bot.event
async def on_raw_reaction_add(payload):
    await update_participation_message(payload)


@bot.event
async def on_raw_reaction_remove(payload):
    await update_participation_message(payload)


async def update_participation_message(payload):
    if payload.message_id not in tracked_messages:
        print(f"Ignoré : {payload.message_id} n'est pas suivi")
        return

    guild = bot.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    if not message:
        return

    reactions_map = {
        "✅": [],
        "❓": [],
        "❌": [],
        "🚗": [],
    }

    for reaction in message.reactions:
        if str(reaction.emoji) in reactions_map:
            users = [user async for user in reaction.users()]
            reactions_map[str(reaction.emoji)] = [f"• {u.display_name}" for u in users if not u.bot]

    titre = message.channel.name.replace("-", " ").title()
    lien = tracked_links.get(payload.message_id, "")

    new_content = (
        f"📅 **Participation au tournoi : {titre}**\n"
        f"Réagis avec :\n"
        f"✅ = Je participe\n❓ = À confirmer\n❌ = Je ne viens pas\n🚗 = Je viens en voiture (lift possible)\n\n"
        f"**✅ Participants :**\n" + "\n".join(reactions_map["✅"]) + "\n\n"
        f"**❓ À confirmer :**\n" + "\n".join(reactions_map["❓"]) + "\n\n"
        f"**❌ Ne viennent pas :**\n" + "\n".join(reactions_map["❌"]) + "\n\n"
        f"**🚗 Proposent un lift :**\n" + "\n".join(reactions_map["🚗"]) + "\n\n"
        f"{lien}"
    )

    await message.edit(content=new_content)


@tasks.loop(hours=24)
async def archive_old_tournaments():
    now = datetime.datetime.now(datetime.timezone.utc)
    guild = bot.get_guild(GUILD_ID)

    tournoi_category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    archive_category = discord.utils.get(guild.categories, id=CATEGORY_ARCHIVES_ID)

    for channel in tournoi_category.text_channels:
        if channel.created_at < now - datetime.timedelta(days=30):
            await channel.edit(category=archive_category)
            print(f"Archivé : {channel.name}")


bot.run(TOKEN)
