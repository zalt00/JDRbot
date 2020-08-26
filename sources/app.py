# -*- coding:Utf-8 -*-


from .config import config
import json
import os
import random
import re
import sys
import threading
import socket as skt
import io

import discord
from discord.ext import commands


bot = commands.Bot(config['bot']['prefix'])

@bot.event
async def on_ready():
    pass

embed = None
embed_message = None

@bot.command(name='test', help='test func (MJ only)')
@commands.has_role('MJ')
async def test(ctx, *args):
    global embed, embed_message
    embed=discord.Embed()
    embed.add_field(name="undefined", value="undefined\n\n\n\ntest", inline=False)
    embed_message = await ctx.send(embed=embed)

@bot.command(name='test2', help='test func (MJ only)')
@commands.has_role('MJ')
async def test2(ctx, *args):
    embed.title = 'BOOOOOOOOOUUUUUUUH'
    await embed_message.edit(embed=embed)

@bot.command(name='clear', help='clears the channel (MJ only)')
@commands.has_role('MJ')
async def clear(ctx, limit: int):
    await ctx.channel.purge(limit=limit)

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(error)
    

def advanced_configuration_pannel(army_management_category, battle_category):
    stop = False
    connection_with_server = None    
    recv_buffer = ''
    send_buffer = ()
    
    def check_connection():
        nonlocal recv_buffer, connection_with_server
        
        if connection_with_server is not None:
            try:                    
                connection_with_server.setblocking(False)
                try:
                    recv_buffer += connection_with_server.recv(4096).decode()
                except BlockingIOError:
                    pass
                connection_with_server.setblocking(True)
                
                if '#close#' in recv_buffer:
                    connection_with_server.close()
                    raise ConnectionResetError
                    
                connection_with_server.send(b'')
                
            except ConnectionResetError:
                recv_buffer = ''
                connection_with_server = None
                return 0
            else:
                return 1
        else:
            return -1
            
    
    print('Panneau de configuration avancée')
    print('Commandes disponibles:')
    print()
    print(' - Commandes de base:')
    print('eval <expr>: évalue une expression')
    print('quit: quitter le panneau de configuration')    
    print()
    print(' - Gestion des batailles:')
    print('edit <mode> <camp> <id>: édite un escouade, le mode peut être "a", "w" ou "rm"')
    print("get <camp> <id>: affiche la composition d'une escouade")
    print("load <filename>: charge une configuration d'armée depuis un fichier json")
    print("save <filename>: sauvegarde la configuration de l'armée dans un fichier json")
    print()
    print(' - Connexion réseau:')
    print('connect: permet de se connecter sur le port par défaut')
    print('check_connection: teste la connection')
    print('recv: reçoit et traite les données du serveur, puis les met dans le buffer')
    print('send <filename=doc_name>: envoie les données du buffer au bot discord')
    print()

    while not stop:
        action = input('> ')
        
        command, *args = action.split(' ')
        
        if command == 'quit':
            stop = True
            
        elif command == 'edit':
            if battle_category.has_battle_started:
                try:
                    mode, camp, squad_id = args
                except ValueError:
                    print('error: wrong argument number', file=sys.stderr)
                else:
                    army = battle_category.current_battle.army1_squads if camp == '1' else battle_category.current_battle.army2_squads
                    squad_id = int(squad_id)
                    if mode in ('a', 'w'):
                        if mode == 'a':
                            print(battle_category.format_squad_data(squad_id, army[squad_id], marker=''))             
                            new_squad = list(army[squad_id])
                            
                        else:
                            new_squad = []
                        
                        input_value = ''
                        while input_value not in ('save', 'cancel'):
                            if input_value:
                                groups = re.findall('([0-9]+) ([a-zA-Z -éèêà]+), ([0-9]+)/([0-9]+)', input_value)
                                if groups and len(groups[0]) == 4:
                                    values = groups[0]
                                    number, type_, atk, pv = values
                                    for i in range(int(number)):
                                        new_squad.append({'atk': int(atk), 'pv': int(pv), 'type': type_})
                                else:
                                    print('error: wrong syntaxe', file=sys.stderr)
                            input_value = input('- ')
                        
                        if input_value == 'save':
                            army[squad_id] = new_squad
                            
                    
                    elif mode == 'rm':
                        print(battle_category.format_squad_data(squad_id, army[squad_id], marker=''))
                        to_remove = set()
                        input_value = ''
                        
                        while input_value not in ('save', 'cancel'):
                            input_value = input('id: ')
                            if input_value.isnumeric():
                                id_ = int(input_value)
                                if id_ < len(army[squad_id]):
                                    to_remove.add(id_)
                                else:
                                    print('error: index out of range')
                                    
                        if input_value == 'save':
                            new_squad = [v for (i, v) in enumerate(army[squad_id]) if i not in to_remove]
                            army[squad_id] = new_squad                            
                                    
                    
            else:
                print('error: battle has not started yet', file=sys.stderr)    
            

        elif command == 'eval':
            expr = ' '.join(args)
            try:
                out_value = eval(expr)
            except Exception as error:
                print(f'{error.__class__.__name__}: {error.args[0]}', file=sys.stderr)
            else:
                if out_value is not None:
                    print('out:', out_value)
        
        elif command == 'get':
            if battle_category.has_battle_started:
                try:
                    camp, squad_id = args
                except ValueError:
                    print('error: wrong argument number', file=sys.stderr)
                else:
                    army = battle_category.current_battle.army1_squads if camp == '1' else battle_category.current_battle.army2_squads
                    squad_id = int(squad_id)       
                    print(battle_category.format_squad_data(squad_id, army[squad_id], marker=''))    
            else:
                print('error: battle has not started yet', file=sys.stderr)        
                
        elif command in ('save', 'load'):
            if len(args) == 1:
                if battle_category.has_battle_started:
                    filename = args[0]
                    if not filename.endswith('.json'):
                        filename += '.json'      
                    if command == 'save':
                        with open(filename, 'w') as datafile:
                            json.dump([battle_category.current_battle.army1_squads, battle_category.current_battle.army2_squads], datafile)       
                    else:
                        battle_category.current_battle.load_armies(filename)
                    
                else:
                    print('error: battle has not started yet', file=sys.stderr)      
            else:        
                print('error: wrong argument number', file=sys.stderr)   
                
        elif command == 'connect':
            recv_buffer = ''
            
            if connection_with_server is not None:
                connection_with_server.close()
            
            connection_with_server = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
            
            response = 'y'
            while response == 'y':
                try:
                    connection_with_server.connect(('localhost', 50000))
                except ConnectionRefusedError:
                    print('error: connection failed, retry ? [Y]es / [N]o', file=sys.stderr)
                    response = input().lower()
                else:
                    response = 'n'
                    print('info: succesfuly connected')
        
        elif command == 'check_connection':
            connection_state = check_connection()
            if connection_state == 0:
                print('info: connexion intérompue')
            elif connection_state == 1:
                print('info: connexion opérationnelle')
            else:
                print('info: connexion fermée ou inexistante')
        
        elif command == 'recv':
            connection_state = check_connection()            
            if connection_state == 1:
                try:
                    connection_with_server.setblocking(False)
                    last_added = recv_buffer
                    while '#eof#' not in last_added:
                        last_added = connection_with_server.recv(4096).decode()
                        recv_buffer += last_added
                        
                    connection_with_server.setblocking(True)

                except BlockingIOError:
                    pass
                else:
                    data = re.findall('#sof#.*#name:(.*)#(.*)#eof#', recv_buffer, re.DOTALL)    
                    if len(data) >= 1:
                        print('info: données récupérées avec succès')
                        send_buffer = data[0]
                        
                    elif len(recv_buffer) == 0:
                        print("error: pas de donnée reçue")
                    else:
                        print('error: format des données invalide')
                    check_connection()
                    recv_buffer = ''
                
            elif connection_state == 0:
                print('error: connexion intérompue', file=sys.stderr)
            else:
                print('error: connexion fermée ou inexistante', file=sys.stderr)
                
        elif command == 'send':
            if send_buffer != ():
                if len(args) == 0:
                    filename = send_buffer[0]
                else:
                    filename = args[0]
                
                army_management_category.add_html_doc(send_buffer[1], filename)
                print('info: document envoyé avec succès')
                send_buffer = ()
                
            else:
                print('error: le buffer est vide')
                
        elif command == '':
            pass
        
        else:
            print('error: this command does not exist', file=sys.stderr)
                     
