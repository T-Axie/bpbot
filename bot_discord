import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from keep_alive import keep_alive  # pour Render

# Charger la config via les variables d’environnement
TOKEN = os.environ['TOKEN']
GUILD_ID = int(os.environ['GUILD_ID'])
CATEGORY_TOURNOIS_ID = int(os.environ['CATEGORY_TOURNOIS_ID'])
CATEGORY_ARCHIVES_ID = int(os.environ['CATEGORY_ARCHIVES_ID'])
PLANNING_CHANNEL_ID = int(os.environ['PLANNING_CHANNEL_ID'])

# Charger les messages suivis depuis le fichier local (créé automatiquement)
if os.path.exists("tracked_messages.json"):
    with open("tracked_messages.json", "r") as f:
        tracked_messages = json.load(f)
else:
    tracked_messages = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🔄 Archivage automatique des anciens salons (existant dans ta version précédente)
@tasks.loop(hours=24)
async def archive_old_tournaments():
    guild = bot.get_guild(GUILD_ID)
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    archives = discord.utils.get(guild.categories, id=CATEGORY_ARCHIVES_ID)

    now = datetime.datetime.utcnow()
    for channel in category.text_channels:
        # Comparer les dates de création (avec gestion des fuseaux horaires)
        if channel.created_at.replace(tzinfo=None) < now - datetime.timedelta(days=30):
            await channel.edit(category=archives)

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

    for emoji in ["✅", "🤔", "❌", "🚗"]:
        await msg.add_reaction(emoji)
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

    for u_id, emojis in user_reactions.items():
        exclusive = [e for e in emojis if e in ["✅", "🤔", "❌"]]
        if len(exclusive) > 1:
            for e in exclusive:
                if e != emojis[-1]:
                    emoji_obj = discord.utils.get(message.reactions, emoji=e)
                    user = guild.get_member(u_id)
                    if emoji_obj and user:
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

# Garde Render actif
keep_alive()
bot.run(TOKEN)
