import discord
from discord.ext import commands, tasks
import datetime
import os
import json

# === Charger la config depuis les variables d’environnement ===
TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CATEGORY_TOURNOIS_ID = int(os.getenv("CATEGORY_TOURNOIS_ID"))
CATEGORY_ARCHIVES_ID = int(os.getenv("CATEGORY_ARCHIVES_ID"))
PLANNING_CHANNEL_ID = int(os.getenv("PLANNING_CHANNEL_ID"))

# Charger les messages suivis
if os.path.exists("tracked_messages.json"):
    with open("tracked_messages.json", "r") as f:
        tracked_messages = json.load(f)
        tracked_messages = {int(k): v for k, v in tracked_messages.items()}
else:
    tracked_messages = {}

MOIS_ORDRE = {
    'janvier': 1,
    'février': 2,
    'fevrier': 2,
    'mars': 3,
    'avril': 4,
    'mai': 5,
    'juin': 6,
    'juillet': 7,
    'août': 8,
    'aout': 8,
    'septembre': 9,
    'octobre': 10,
    'novembre': 11,
    'décembre': 12,
    'decembre': 12
}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Pour conserver les liens dans les messages suivis
tracked_links = {}

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    archive_old_tournaments.start()

@tasks.loop(hours=12)
async def archive_old_tournaments():
    guild = bot.get_guild(GUILD_ID)
    tournois_cat = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    archives_cat = discord.utils.get(guild.categories, id=CATEGORY_ARCHIVES_ID)
    now = datetime.datetime.now(datetime.timezone.utc)
    for channel in tournois_cat.text_channels:
        if (now - channel.created_at).days >= 30:
            await channel.edit(category=archives_cat)

@bot.command()
async def addtournoi(ctx, *, args):
    parts = args.strip().split()
    lien = ""

    if parts[-1].startswith("http"):
        lien = parts[-1]
        titre = " ".join(parts[:-1])
    else:
        titre = " ".join(parts)

    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    channel_name = titre.lower().replace(" ", "-").replace("/", "-")
    new_channel = await guild.create_text_channel(channel_name, category=category)

    message_content = (
        f"\n📋 **Participation au tournoi : {titre}**\n"
        f"Réagis avec :\n"
        f"✅ = Je participe\n🤔 = À confirmer\n❌ = Je ne viens pas\n🚗 = Je viens en voiture (lift possible)"
    )

    if lien:
        message_content += f"\n\n🔗 Lien : <{lien}>"

    msg = await new_channel.send(message_content)

    await msg.add_reaction("✅")
    await msg.add_reaction("🤔")
    await msg.add_reaction("❌")
    await msg.add_reaction("🚗")
    await msg.pin()

    tracked_messages[msg.id] = new_channel.id
    tracked_links[msg.id] = lien

    with open("tracked_messages.json", "w") as f:
        json.dump(tracked_messages, f)

    await ctx.send(f"Salon créé : {new_channel.mention}")
    await update_planning(ctx.guild)

@bot.command()
async def planning(ctx):
    await update_planning(ctx.guild)
    await ctx.send("Planning mis à jour !")

def extraire_date_depuis_nom(nom):
    try:
        parts = nom.split("-")
        jour = int(parts[0])
        mois = MOIS_ORDRE.get(parts[1].lower(), 0)
        return (mois, jour)
    except:
        return (99, 99)

async def update_planning(guild):
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    salons = category.text_channels
    salons_sorted = sorted(salons, key=lambda c: extraire_date_depuis_nom(c.name))

    planning_lines = ["📋 **Planning Tournois en cours :**\n"]
    for chan in salons_sorted:
        titre = chan.name.replace('-', ' ').title()
        planning_lines.append(f"📌 {titre} ➔ {chan.mention}")

    channel_planning = guild.get_channel(PLANNING_CHANNEL_ID)
    messages = [msg async for msg in channel_planning.history(limit=10)]

    if messages:
        await messages[0].edit(content="\n".join(planning_lines))
    else:
        await channel_planning.send("\n".join(planning_lines))

@bot.event
async def on_raw_reaction_add(payload):
    await update_participation_message(payload)

@bot.event
async def on_raw_reaction_remove(payload):
    await update_participation_message(payload)

async def update_participation_message(payload):
    if payload.message_id not in tracked_messages:
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

    user_reactions = {}

    for reaction in message.reactions:
        if str(reaction.emoji) in reactions_map:
            users = [user async for user in reaction.users() if not user.bot]
            reactions_map[str(reaction.emoji)] = [u.mention for u in users]
            for u in users:
                if u.id not in user_reactions:
                    user_reactions[u.id] = []
                user_reactions[u.id].append(str(reaction.emoji))

    # Nettoyage : une seule réaction parmi ✅/🤔/❌
    for u_id, emojis in user_reactions.items():
        exclusive = [e for e in emojis if e in ["✅", "🤔", "❌"]]
        if len(exclusive) > 1:
            for e in exclusive:
                if e != emojis[-1]:
                    emoji_obj = discord.utils.get(message.reactions, emoji=e)
                    if emoji_obj:
                        user = guild.get_member(u_id)
                        if user:
                            try:
                                await message.remove_reaction(e, user)
                            except:
                                pass

    titre = message.channel.name.replace("-", " ").title()
    lien = tracked_links.get(message.id, "")

    new_content = (
        f"📋 **Participation au tournoi : {titre}**\n"
        f"Réagis avec :\n"
        f"✅ = Je participe\n🤔 = À confirmer\n❌ = Je ne viens pas\n🚗 = Je viens en voiture (lift possible)\n\n"
        f"✅ **Participent :**\n" + "\n".join(reactions_map["✅"]) + "\n\n"
        f"🤔 **À confirmer :**\n" + "\n".join(reactions_map["🤔"]) + "\n\n"
        f"❌ **Ne viennent pas :**\n" + "\n".join(reactions_map["❌"]) + "\n\n"
        f"🚗 **Proposent un lift :**\n" + "\n".join(reactions_map["🚗"])
    )

    if lien:
        new_content += f"\n\n🔗 Lien : <{lien}>"

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
