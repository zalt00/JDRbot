# -*- coding:Utf-8 -*-

import discord
from discord.ext import commands
from . import battle_manager
import random
from .config import config
import json
import re


class BattleCategory(commands.Cog, name='Battle manager commands'):
    """Controls the execution of the battle."""
    def __init__(self, bot):
        
        self.bot = bot
        
        self.current_battle = None  # instance de la classe Battle, controle le déroulement du combat
        self.armies_message = None  # référence du message envoyé avec la commande start_battle, 
        # indiquant les compositions des armees et l'état actuel du combat
        self.has_battle_started = False  # permet de savoir si le combat a commencé ou non
        
        self.roll1_message = None  # référence du message envoyé par la commande roll camp l'utilisateur a le rôle camp1
        self.roll2_message = None  # même chose mais pour le camp 2
        self.roll1_actions = ''  # historique des actions faites grace aux jets de dé
        self.roll2_actions = ''
        self.roll1_list = []  # liste des valeurs des jets
        self.roll2_list = []
        
        self.damage_repartition = {}  # répartition courante des dégats
        self.damage_repartition_message = None  # référence du message renseignant la répartition courante des dégats
        self.moved_damage_amount = 0  # nombre de dégats déplacés sur la répartition des dégats


    @commands.command(name='start_battle', help="starts the battle (MJ only)")
    @commands.has_role('MJ')
    async def start_battle(self, ctx):
        
        self.current_battle = battle_manager.Battle()
        self.has_battle_started = True
        self.armies_message = await ctx.send(self.format_both_camps_data())
        
        await ctx.message.delete()    
    
    
    @commands.command(name='end_battle', help="ends the battle (MJ only)")
    @commands.has_role('MJ')
    async def end_battle(self, ctx):
        
        # envoie une sauvegarde des compositions des armées dans le 
        # salon des bilans des combats, utile pour se souvenir des pertes etc
        # si on veut pouvoir recharger les armées plus tard utiliser la commande save
        summary_channel = bot.get_channel(config['channels'].getint('summary'))
        await summary_channel.send(self.armies_message.content)
        
        self.current_battle = None
        self.has_battle_started = False
        await self.armies_message.delete()
        self.armies_message = None
        
        await ctx.message.delete()
    
    @commands.command(name='reload', help='debug command, reload the default json file (MJ only)')
    @commands.has_role('MJ')
    async def reload_armies(self, ctx):
        if self.has_battle_started:
            self.current_battle.load_armies()
            await self.armies_message.edit(content=self.format_both_camps_data())
            await ctx.message.delete()        
    
    def format_both_camps_data(self):
        """format the composition of the armies into a clean, ready to send discord message content"""
        camp1_str = self.format_army_data(self.current_battle.army1_squads, marker='  ', max_length=50)
        camp2_str = self.format_army_data(self.current_battle.army2_squads, marker='  ', max_length=50)
        
        lines1 = camp1_str.splitlines()
        lines2 = camp2_str.splitlines()
        
        # longueur des lignes de la version formattée de l'armée du camp 1
        max_length = len(max(lines1, key=lambda line: len(line)))  
        
        # balise permettant une formattage plus facile
        comp = '{:<' + str(max_length + 2) + '}'
        
        # les ``` permettent d'avoir un code block dans discord, et ainsi avoir des caractères toujours de la meme taille
        lines = [f'``` {comp}      Armée 2'.format('  Armée 1')]
        
        for i in range(max(len(lines1), len(lines2))):
            try:
                line1 = lines1[i]
            except IndexError:
                line1 = ''
                
            try:
                line2 = lines2[i]
            except IndexError:
                line2 = ''
                
            lines.append(f'{comp}|   {"{}"}'.format(line1, line2))
            
        lines.append('```')
        
        txt = '\n'.join(lines)
        
        # infos additionnelles sur le combat inter-escouades en cours
        if self.current_battle.attacking_squad is not None:
            txt += f"\n{self.format_squad_data('', self.current_battle.attacking_squad, title=' attaquant')}"
            txt += f"\n{self.format_squad_data('', self.current_battle.defending_squad, title=' défenseur')}"
        
        return txt
        
    def format_army_data(self, data, marker='**', max_length=-1):
        txt = ''
        for i, squad in enumerate(data):
            title = 'escouade'
            if self.has_battle_started:
                if squad == self.current_battle.defending_squad:
                    title = 'DEFENSEUR'
                elif squad == self.current_battle.attacking_squad:
                    title = 'ATTAQUANT'
            txt += self.format_squad_data(i, squad, title=title, marker=marker, max_length=max_length)
            txt += '\n'
        return txt
    
    def format_squad_data(self, i, squad, title='escouade', marker='**', damage_repart=None, max_length=-1):
        lines = [f'{marker}{title} {i}{marker}']
        
        identical_units_detection_util = {}  # permet de détecter les unités similaires pour un affichage plus épuré
        
        for unit_id, unit in enumerate(squad):
            line_id = len(lines)
            type_, atk, pv = unit["type"], unit["atk"], unit["pv"]
            
            if damage_repart is not None:
                damage = damage_repart.get(unit_id, 0)
            else:
                damage = 0
            
            if (type_, atk, pv, damage) in identical_units_detection_util:
                
                target_line_id, units_identifiers = identical_units_detection_util[(type_, atk, pv, damage)]
                units_identifiers.append(unit_id)
                s = f'{len(units_identifiers)} {type_}, {atk}/{pv}, id: {units_identifiers}'
                if damage != 0:
                    s += f', damage: {damage}'
                
                if max_length != -1 and len(s) > max_length:
                    number_of_sublines = len(s) // max_length
                    sublines = []
                    for i in range(number_of_sublines):
                        sublines.append(s[i * max_length:(i + 1) * max_length])
                    sublines.append(s[(i + 1) * max_length:])
                    s = '\n'.join(sublines)
                
                lines[target_line_id] = s
                
            else:
                identical_units_detection_util[(type_, atk, pv, damage)] = line_id, [unit_id]
                s = f'1 {type_}, {atk}/{pv}, id: {unit_id}'
                if damage != 0:
                    s += f', damage: {damage}'
                    
                if max_length != -1 and len(s) > max_length:
                    number_of_sublines = len(s) // max_length
                    sublines = []
                    for i in range(number_of_sublines):
                        sublines.append(s[i * max_length:(i + 1) * max_length])
                    sublines.append(s[(i + 1) * max_length:])
                    s = '\n'.join(sublines)            
                    
                lines.append(s)
                
        lines.append('')
        
        return '\n'.join(lines)
    
    
    @commands.command(name="iis", help='begins an inter-squad battle against squad1 and squad2 (MJ only)')
    @commands.has_role('MJ')
    async def initiate_inter_squad_battle(self, ctx, squad1: int, squad2: int, whos_attacking: int):
        if self.has_battle_started:
            self.current_battle.initiate_inter_squad_battle(squad1, squad2, whos_attacking)
            await self.armies_message.edit(content=self.format_both_camps_data())
            await ctx.send(f"""Le camp {whos_attacking} attaque
Force totale: {self.current_battle.get_total_strength(self.current_battle.attacking_squad)}
Défense totale : {self.current_battle.get_total_thougness(self.current_battle.defending_squad)}""")
        
        
    @commands.command(name="roll", help='roll the dices for the inter-squad battles actions')
    async def roll(self, ctx, n: int):
        role_names = [r.name for r in ctx.message.author.roles]  # noms des roles de l'auteur du message
        if 'camp1' in role_names:
            
            await ctx.send('Lancer des jets pour le camp 1')
            self.roll1_list, self.roll1_message = await self._roll(ctx, n)
            self.roll1_actions = []
            
        elif 'camp2' in role_names:
            
            await ctx.send('Lancer des jets pour le camp 2')        
            self.roll2_list, self.roll2_message = await self._roll(ctx, n)
            self.roll2_actions = []
        
    
    async def _roll(self, ctx, n):
        rolls = []
        for _ in range(n):
            rolls.append(random.randint(1, config['game'].getint('dice')))
            
        rolls.sort()  # trie les valeurs pour une meilleure visibilité
        
        txt = f"`valeurs: {', '.join(['{:>2}'.format(roll) for roll in rolls])}`\n`total: {sum(rolls)}`"
        msg = await ctx.send(txt)
        return rolls, msg
    
    
    @commands.command(name='rm', help="removes values from the opponent's roll (MJ only)")
    @commands.has_role('MJ')
    async def remove(self, ctx, *args):
        role_names = [r.name for r in ctx.message.author.roles]
        if 'camp1' in role_names:
            await self._use(ctx, 2, *args, opening_text='jets supprimés')
        elif 'camp2' in role_names:
            await self._use(ctx, 1, *args, opening_text='jets supprimés')    
    
    @commands.command(name='u', help="uses values from your roll")
    async def use(self, ctx, *args):
        role_names = [r.name for r in ctx.message.author.roles]
        if 'camp1' in role_names:
            await self._use(ctx, 1, *args)
        elif 'camp2' in role_names:
            await self._use(ctx, 2, *args) 
        
    async def _use(self, ctx, camp, *args, opening_text='derniers jets utlisés'):
        if camp == 1:
            rolls = self.roll1_list
            message = self.roll1_message
            roll_actions = self.roll1_actions
        else:
            rolls = self.roll2_list
            message = self.roll2_message
            roll_actions = self.roll2_actions
            
        values = []
        additional_txt = ''
        for v in args:
            try:
                values.append(int(v))
            except ValueError:
                additional_txt += f'{v} '  # si l'argument n'est pas une valeur numérique, l'ajoute dans l'onglet "action"
            
        for v in list(values):
            try:
                rolls.remove(v)
            except ValueError:
                values.remove(v)  # supprime l'argument si la valeur n'est pas dans les jets
        
        sum_ = sum(values)
        
        roll_actions.append(f'{opening_text}: {values} = {sum_}, action: {additional_txt}')
        
        txt = f"`valeurs: {', '.join(['{:>2}'.format(roll) for roll in rolls])}`\n`total: {sum(rolls)}`\n"
        txt += '\n'.join(roll_actions)
        await message.edit(content=txt)
        await ctx.message.delete()
    
    @commands.command(name='damage', help="start the repartition of the damages inflicted to defender's units")
    async def start_damage_repartition(self, ctx):
        self.moved_damage_amount = 0
        
        await ctx.message.delete()    
        
        self.damage_repartition.clear()
        squad = self.current_battle.defending_squad
        
        txt = self.format_squad_data('', squad, title='défenseurs')
        
        self.damage_repartition_message = await ctx.send(f'{txt}\ndégats totaux: 0')
        
    @commands.command(name='d', help='change the damage dealt to a specific unit')
    async def damage(self, ctx, unit_id: int, amount: int):
        await self._damage(ctx, unit_id, amount)
    
    async def _damage(self, ctx, unit_id, amount):
        self.damage_repartition[unit_id] = amount
        total_damage = sum(self.damage_repartition.values())
        
        self.current_battle.set_damage_repartition(self.damage_repartition)
        preview = self.current_battle.get_preview_with_current_damage_repartition()
        
        txt = self.format_squad_data('', preview, title='défenseurs', damage_repart=self.damage_repartition)
        
        await self.damage_repartition_message.edit(content=f'{txt}\ndégats totaux: {total_damage}')    
        
    @commands.command(name='m', help='moves a certain amount a damage from an unit to another')
    async def move(self, ctx, unit_id_1: int, unit_id_2:int, amount: int):
        
        await ctx.message.delete()
        
        # le fonctionnement global de cette fonction est de diminuer de amount les dégats 
        # infligés à l'unité 1 et d'augmenter de cette meme valeur les dégats infligés à l'unité 2
        amount1 = self.damage_repartition[unit_id_1]
        amount2 = self.damage_repartition[unit_id_2]
        
        amount1 -= amount
        amount2 += amount
        
        self.moved_damage_amount += amount
        
        await self._damage(ctx, unit_id_1, amount1)
        await self._damage(ctx, unit_id_2, amount2)
        
        await self.damage_repartition_message.edit(content=f'{self.damage_repartition_message.content}\ndégats déplacés: {self.moved_damage_amount}')
    
    
    @commands.command(name="apply", help='applies the damage repartition and updates the armies message (MJ only)')
    @commands.has_role('MJ')
    async def apply_damage(self, ctx):
        await ctx.message.delete()
        
        self.current_battle.apply_damages()
        await self.armies_message.edit(content=self.format_both_camps_data())    
        
        await self.damage_repartition_message.edit(content=self.damage_repartition_message.content + ', appliqués')
        
    @commands.command(name='end', help='ends the squad turn (MJ only)')
    @commands.has_role('MJ')
    async def end_squad_turn(self, ctx):
        self.current_battle.end_inter_squad_turn()
        await self.armies_message.edit(content=self.format_both_camps_data())
        await ctx.send(f"""Le camp {self.current_battle.who_is_attacking} attaque
Force totale: {self.current_battle.get_total_strength(self.current_battle.attacking_squad)}
Défense totale : {self.current_battle.get_total_thougness(self.current_battle.defending_squad)}""")    
        
    
    @commands.command(name='edit', help='edit a squad composition (for more advanced features use the advanced config pannel) (MJ only)')
    @commands.has_role('MJ')
    async def edit_squad(self, ctx, mode, army, squad_id: int, *args):
        army_squads = self.current_battle.army1_squads if army == '1' else self.current_battle.army2_squads
        squad = army_squads[squad_id]    
        if mode == 'rm':
            unit_id = int(args[0])
            squad.pop(unit_id)
        elif mode in ('a', 'as'):
            if mode == 'as':
                string_buffer = ' '.join(args)
                number, type_, atk, pv = re.findall('([0-9]+) ([a-zA-Z -éèêà]+), ([0-9]+)/([0-9]+)', string_buffer)[0]
            else:
                number, type_, atk, pv = args
            for i in range(int(number)):
                squad.append({'atk': int(atk), 'pv': int(pv), 'type': type_})
                
        await self.armies_message.edit(content=self.format_both_camps_data())
    
    @commands.command(name='save', help='save the composition of the army into a json file (for more advanced features use the advanced config pannel) (MJ only)')
    @commands.has_role('MJ')
    async def save(self, ctx, filename):
        with open(filename, 'w') as datafile:
            json.dump([self.current_battle.army1_squads, self.current_battle.army2_squads], datafile)
        await ctx.message.add_reaction('👍')
    
    @commands.command(name='update', help='updates changes made with the advanced configuration pannel (MJ only)')
    @commands.has_role('MJ')
    async def update(self, ctx):
        await self.armies_message.edit(content=self.format_both_camps_data())
        await ctx.message.delete()
