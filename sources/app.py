# -*- coding:Utf-8 -*-


from sources.config import config
import json
import os
import random
import re
import sys
import threading

import discord
from discord.ext import commands



bot = commands.Bot(config['bot']['prefix'])

@bot.event
async def on_ready():
    pass

@bot.command(name='test', help='test func')
@commands.has_role('MJ')
async def test(ctx, *args):
    print(ctx.message.author)
    a = await ctx.send(args)


async def on_command_error(ctx, error):
    await ctx.send(error)
    

def advanced_configuration_pannel(battle_category):
    stop = False
    
    print('Panneau de configuration avancée')
    print('Commandes disponibles:\n')
    print('quit: quitter le panneau de configuration')
    print('edit <mode> <camp> <id>: editer un escouade, le mode peut être "a", "w" ou "rm"')
    print("get <camp> <id>: affiche la composition d'une escouade")
    print("load <filename>: charge une configuration d'armée depuis un fichier json")
    print("save <filename>: sauvegarde la configuration de l'armée dans un fichier json")
    print('eval <expr>: évalue une expression')
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
                    
            else:
                print('battle has not started yet')
            

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
                print('battle has not started yet')      
                
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
                    print('battle has not started yet')      
            else:        
                print('error: wrong argument number', file=sys.stderr)   
                     
