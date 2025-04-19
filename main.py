
import discord
from discord.ext import commands, tasks
import datetime
import os


TOKEN = os.getenv("token")
GUILD_ID = int(os.getenv("guild_id"))
CATEGORY_TOURNOIS_ID = int(os.getenv("category_tournois_id"))
CATEGORY_ARCHIVES_ID = int(os.getenv("category_archives_id"))
PLANNING_CHANNEL_ID = int(os.getenv("planning_channel_id"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_messages = set()
tracked_links = {}

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    archive_old_tournaments.start()

@bot.command()
async def addtournoi(ctx, *, titre_et_lien):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)

    if "http" in titre_et_lien:
        parts = titre_et_lien.split()
        titre = " ".join(part for part in parts if not part.startswith("http"))
        lien = next((part for part in parts if part.startswith("http")), None)
    else:
        titre = titre_et_lien
        lien = None

    channel_name = titre.lower().replace(" ", "-").replace("/", "-")
    new_channel = await guild.create_text_channel(channel_name, category=category)

    desc = f"**Participation au tournoi : {titre}**\n\n"
    desc += "Réagis avec :\n✅ = Je participe\n🤔 = À confirmer\n❌ = Je ne viens pas\n🚗 = Je viens en voiture (lift possible)\n\n"
    if lien:
        desc += f"[Lien vers l'événement]({lien})\n"

    msg = await new_channel.send(desc)
    tracked_messages.add(msg.id)
    if lien:
        tracked_links[msg.id] = lien

    await msg.add_reaction("✅")
    await msg.add_reaction("🤔")
    await msg.add_reaction("❌")
    await msg.add_reaction("🚗")
    await msg.pin()

    await ctx.send(f"Salon créé : {new_channel.mention}")

@bot.command()
async def planning(ctx):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    salons = category.text_channels
    salons_sorted = sorted(salons, key=lambda c: c.name)

    planning_lines = ["📅 **Planning Tournois en cours :**\n"]
    for chan in salons_sorted:
        planning_lines.append(f"📍 {chan.name.replace('-', ' ').title()} → {chan.mention}")

    channel = guild.get_channel(PLANNING_CHANNEL_ID)
    await channel.purge()
    await channel.send("\n".join(planning_lines))

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
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
        "🤔": [],
        "❌": [],
        "🚗": [],
    }

    for reaction in message.reactions:
        if str(reaction.emoji) in reactions_map:
            users = [user async for user in reaction.users()]
            reactions_map[str(reaction.emoji)] = [u.mention for u in users if not u.bot]

    titre = message.channel.name.replace("-", " ").title()
    lien = tracked_links.get(message.id)

        new_content = (
            f"📅 **Participation au tournoi : {titre}**\n"
            f"Réagis avec :\n"
            f"✅ = Je participe\n❓ = À confirmer\n❌ = Je ne viens pas\n🚗 = Je viens en voiture (lift possible)\n\n"
            f"**✅ Participants :**\n" + "\n".join(reactions_map["✅"]) + "\n\n"
            f"**❓ À confirmer :**\n" + "\n".join(reactions_map["❓"]) + "\n\n"
            f"**❌ Ne viennent pas :**\n" + "\n".join(reactions_map["❌"]) + "\n\n"
            f"**🚗 Proposent un lift :**\n" + "\n".join(reactions_map["🚗"]) + "\n\n"
            + lien if lien else ""
        )

    await message.edit(content=new_content)

@tasks.loop(hours=24)
async def archive_old_tournaments():
    now = datetime.datetime.now(datetime.timezone.utc)
    guild = bot.get_guild(GUILD_ID)
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    archive_category = discord.utils.get(guild.categories, id=CATEGORY_ARCHIVES_ID)

    for channel in category.text_channels:
        if channel.created_at < now - datetime.timedelta(days=30):
            await channel.edit(category=archive_category)
            print(f"Archivé : {channel.name}")

bot.run(TOKEN)
