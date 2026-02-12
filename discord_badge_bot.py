import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
from typing import Optional

# Configuration
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

class BadgeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)
        self.data_file = "service_data.json"
        self.load_data()
    
    def load_data(self):
        """Charge les données de service depuis le fichier JSON"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.service_data = json.load(f)
        else:
            self.service_data = {}
    
    def save_data(self):
        """Sauvegarde les données de service dans le fichier JSON"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.service_data, f, indent=4, ensure_ascii=False)
    
    async def setup_hook(self):
        """Synchronise les commandes slash au démarrage"""
        await self.tree.sync()
        print("Commandes slash synchronisées!")

# Initialisation du bot
bot = BadgeBot()

@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user}')
    print(f'ID du bot: {bot.user.id}')
    print('------')

@bot.tree.command(name="debut_service", description="Démarrer votre service")
async def debut_service(interaction: discord.Interaction):
    """Commande pour badger en début de service"""
    user_id = str(interaction.user.id)
    username = interaction.user.name
    
    # Vérifier si l'utilisateur est déjà en service
    if user_id in bot.service_data and bot.service_data[user_id].get('en_service'):
        await interaction.response.send_message(
            "❌ Vous êtes déjà en service!", 
            ephemeral=True
        )
        return
    
    # Enregistrer le début de service
    now = datetime.now().isoformat()
    
    if user_id not in bot.service_data:
        bot.service_data[user_id] = {
            'username': username,
            'sessions': [],
            'temps_total': 0,
            'en_service': False
        }
    
    bot.service_data[user_id]['en_service'] = True
    bot.service_data[user_id]['debut_actuel'] = now
    bot.service_data[user_id]['username'] = username
    
    bot.save_data()
    
    embed = discord.Embed(
        title="✅ Début de Service",
        description=f"{interaction.user.mention} a commencé son service",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Heure de début", value=f"<t:{int(datetime.now().timestamp())}:F>")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="fin_service", description="Terminer votre service")
async def fin_service(interaction: discord.Interaction):
    """Commande pour badger en fin de service"""
    user_id = str(interaction.user.id)
    username = interaction.user.name
    
    # Vérifier si l'utilisateur est en service
    if user_id not in bot.service_data or not bot.service_data[user_id].get('en_service'):
        await interaction.response.send_message(
            "❌ Vous n'êtes pas en service actuellement!", 
            ephemeral=True
        )
        return
    
    # Calculer la durée du service
    debut = datetime.fromisoformat(bot.service_data[user_id]['debut_actuel'])
    fin = datetime.now()
    duree = (fin - debut).total_seconds()
    
    # Enregistrer la session
    session = {
        'debut': debut.isoformat(),
        'fin': fin.isoformat(),
        'duree': duree
    }
    
    bot.service_data[user_id]['sessions'].append(session)
    bot.service_data[user_id]['temps_total'] += duree
    bot.service_data[user_id]['en_service'] = False
    del bot.service_data[user_id]['debut_actuel']
    
    bot.save_data()
    
    # Formater la durée
    heures = int(duree // 3600)
    minutes = int((duree % 3600) // 60)
    secondes = int(duree % 60)
    
    embed = discord.Embed(
        title="🔴 Fin de Service",
        description=f"{interaction.user.mention} a terminé son service",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Heure de fin", value=f"<t:{int(fin.timestamp())}:F>", inline=False)
    embed.add_field(name="Durée de service", value=f"{heures}h {minutes}m {secondes}s", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mon_temps", description="Voir votre temps de service total")
async def mon_temps(interaction: discord.Interaction):
    """Affiche les statistiques de temps de service de l'utilisateur"""
    user_id = str(interaction.user.id)
    
    if user_id not in bot.service_data:
        await interaction.response.send_message(
            "❌ Vous n'avez aucun enregistrement de service.", 
            ephemeral=True
        )
        return
    
    data = bot.service_data[user_id]
    temps_total = data['temps_total']
    
    # Si en service actuellement, ajouter le temps en cours
    if data.get('en_service'):
        debut = datetime.fromisoformat(data['debut_actuel'])
        temps_actuel = (datetime.now() - debut).total_seconds()
        temps_total += temps_actuel
    
    # Formater le temps total
    heures = int(temps_total // 3600)
    minutes = int((temps_total % 3600) // 60)
    
    embed = discord.Embed(
        title="📊 Vos Statistiques de Service",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Temps total de service", value=f"{heures}h {minutes}m", inline=False)
    embed.add_field(name="Nombre de sessions", value=str(len(data['sessions'])), inline=True)
    embed.add_field(name="Statut actuel", value="🟢 En service" if data.get('en_service') else "🔴 Hors service", inline=True)
    
    if data.get('en_service'):
        debut = datetime.fromisoformat(data['debut_actuel'])
        embed.add_field(
            name="Service en cours depuis", 
            value=f"<t:{int(debut.timestamp())}:R>", 
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="liste_service", description="Voir qui est actuellement en service")
@app_commands.checks.has_permissions(manage_messages=True)
async def liste_service(interaction: discord.Interaction):
    """Affiche la liste des personnes actuellement en service (admin)"""
    en_service = []
    
    for user_id, data in bot.service_data.items():
        if data.get('en_service'):
            debut = datetime.fromisoformat(data['debut_actuel'])
            temps_ecoule = (datetime.now() - debut).total_seconds()
            heures = int(temps_ecoule // 3600)
            minutes = int((temps_ecoule % 3600) // 60)
            
            en_service.append({
                'username': data['username'],
                'debut': debut,
                'duree': f"{heures}h {minutes}m"
            })
    
    embed = discord.Embed(
        title="👥 Personnel en Service",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    if en_service:
        for person in en_service:
            embed.add_field(
                name=f"👤 {person['username']}", 
                value=f"Début: <t:{int(person['debut'].timestamp())}:R>\nDurée: {person['duree']}", 
                inline=False
            )
    else:
        embed.description = "Aucune personne en service actuellement."
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rapport_temps", description="Voir le rapport de temps d'un utilisateur")
@app_commands.checks.has_permissions(manage_messages=True)
async def rapport_temps(interaction: discord.Interaction, membre: discord.Member):
    """Affiche les statistiques détaillées d'un membre (admin)"""
    user_id = str(membre.id)
    
    if user_id not in bot.service_data:
        await interaction.response.send_message(
            f"❌ {membre.name} n'a aucun enregistrement de service.", 
            ephemeral=True
        )
        return
    
    data = bot.service_data[user_id]
    temps_total = data['temps_total']
    
    # Si en service actuellement, ajouter le temps en cours
    if data.get('en_service'):
        debut = datetime.fromisoformat(data['debut_actuel'])
        temps_actuel = (datetime.now() - debut).total_seconds()
        temps_total += temps_actuel
    
    # Formater le temps total
    heures = int(temps_total // 3600)
    minutes = int((temps_total % 3600) // 60)
    
    embed = discord.Embed(
        title=f"📊 Rapport de Service - {membre.name}",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=membre.display_avatar.url)
    embed.add_field(name="Temps total de service", value=f"{heures}h {minutes}m", inline=False)
    embed.add_field(name="Nombre de sessions", value=str(len(data['sessions'])), inline=True)
    embed.add_field(name="Statut actuel", value="🟢 En service" if data.get('en_service') else "🔴 Hors service", inline=True)
    
    # Afficher les 5 dernières sessions
    if data['sessions']:
        sessions_recentes = data['sessions'][-5:]
        sessions_text = ""
        for session in reversed(sessions_recentes):
            debut = datetime.fromisoformat(session['debut'])
            duree = session['duree']
            h = int(duree // 3600)
            m = int((duree % 3600) // 60)
            sessions_text += f"<t:{int(debut.timestamp())}:d> - {h}h {m}m\n"
        
        embed.add_field(name="Dernières sessions", value=sessions_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="aide_badge", description="Afficher l'aide du système de badge")
async def aide_badge(interaction: discord.Interaction):
    """Affiche les commandes disponibles"""
    embed = discord.Embed(
        title="📋 Système de Badge de Service",
        description="Voici les commandes disponibles:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="/debut_service", 
        value="Démarrer votre service", 
        inline=False
    )
    embed.add_field(
        name="/fin_service", 
        value="Terminer votre service", 
        inline=False
    )
    embed.add_field(
        name="/mon_temps", 
        value="Voir vos statistiques de service", 
        inline=False
    )
    embed.add_field(
        name="/liste_service", 
        value="Voir qui est en service (Admin)", 
        inline=False
    )
    embed.add_field(
        name="/rapport_temps @membre", 
        value="Voir le rapport d'un membre (Admin)", 
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Point d'entrée
if __name__ == "__main__":
    print("Démarrage du bot...")
    print("N'oubliez pas de remplacer 'MTQ3MTE0MjA2NDc0NDk1NTkzNg.GJLtRp.m1sLR-H7yify-NyeOUD8aXku_Y3JD-_zqVYzJY' par votre vrai token!")
    
    # IMPORTANT: Remplacez ceci par votre token de bot Discord
    TOKEN = os.getenv("DISCORD_TOKEN")

     bot.run(TOKEN)
