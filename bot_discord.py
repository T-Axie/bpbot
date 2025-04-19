import discord
from discord.ext import commands, tasks
import datetime
import json

# Charger la configuration
with open('config.json') as f:
    config = json.load(f)

TOKEN = config['token']
GUILD_ID = int(config['guild_id'])
CATEGORY_TOURNOIS_ID = int(config['category_tournois_id'])
CATEGORY_ARCHIVES_ID = int(config['category_archives_id'])
PLANNING_CHANNEL_ID = int(config['planning_channel_id'])

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    archive_old_tournaments.start()

@bot.command()
async def addtournoi(ctx, *, titre):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    channel_name = titre.lower().replace(" ", "-").replace("/", "-")
    new_channel = await guild.create_text_channel(channel_name, category=category)

    msg = await new_channel.send(f"""\n📋 **Participation au tournoi : {titre}**\n\nRéagis avec :\n✅ = Je participe\n🤔 = À confirmer\n❌ = Je ne viens pas\n\nParticipants :\n- (ajoutez vos réactions ci-dessous)\n""")
    await msg.add_reaction("✅")
    await msg.add_reaction("🤔")
    await msg.add_reaction("❌")
    await msg.pin()
    await ctx.send(f"Salon créé : {new_channel.mention}")

@bot.command()
async def planning(ctx):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    salons = category.text_channels
    salons_sorted = sorted(salons, key=lambda c: c.created_at)

    planning_lines = ["📅 **Planning Tournois en cours :**\n"]
    for chan in salons_sorted:
        planning_lines.append(f"📍 {chan.name.replace('-', ' ').title()} → {chan.mention}")

    planning_channel = guild.get_channel(PLANNING_CHANNEL_ID)
    await planning_channel.send("\n".join(planning_lines))

@bot.command()
async def archivetournois(ctx):
    guild = ctx.guild
    tournois_cat = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
    archives_cat = discord.utils.get(guild.categories, id=CATEGORY_ARCHIVES_ID)

    for chan in tournois_cat.text_channels:
        await chan.edit(category=archives_cat)
    await ctx.send("Tous les salons de tournoi ont été archivés.")

@tasks.loop(hours=24)
async def archive_old_tournaments():
    today = datetime.date.today()
    if today.day == 1:
        guild = bot.get_guild(GUILD_ID)
        tournois_cat = discord.utils.get(guild.categories, id=CATEGORY_TOURNOIS_ID)
        archives_cat = discord.utils.get(guild.categories, id=CATEGORY_ARCHIVES_ID)
        for chan in tournois_cat.text_channels:
            await chan.edit(category=archives_cat)
        log_channel = guild.get_channel(PLANNING_CHANNEL_ID)
        await log_channel.send("✅ Tournois du mois précédent archivés automatiquement.")

bot.run(TOKEN)
