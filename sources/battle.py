# -*- coding:Utf-8 -*-

import discord
from discord.ext import commands
from . import battle_manager
import random
from .config import config
from . import utils
import json
import re


class BattleCategory(commands.Cog, name='Battle manager commands'):
    """Controls the execution of the battle."""
    def __init__(self, bot):
        
        self.bot = bot
        
        self.current_battle = None  # instance de la classe Battle, controle le déroulement du combat
        self.armies_messages = []  # références des messages envoyés avec la commande start_battle, 
        # indiquant les compositions des armees et l'état actuel du combat
        self.has_battle_started = False  # permet de savoir si le combat a commencé ou non
        
        self.intersquads_fight_progression_message = None  # référence du message principal de la progression de la bataille inter-escouades
        self.intersquads_fight_embed_data = dict(title='Undefined', whos_attacking=0, attackers_rolls='', defenders_rolls='', damage_repartition='')
        self.intersquads_fight_embed = None        
        
        self.current_view = 'default'  # apparence courante de intersquads_fight_progression_message (default ou squads)
        
        self.roll1_message = None  # référence du message envoyé par la commande roll quand l'utilisateur a le rôle camp1
        self.roll2_message = None  # même chose mais pour le camp 2
        self.roll1_actions = ''  # historique des actions faites grace aux jets de dé
        self.roll2_actions = ''
        self.roll1_list = []  # liste des valeurs des jets
        self.roll2_list = []
        
        self.damage_repartition = {}  # répartition courante des dégats
        self.damage_repartition_message = None  # référence du message renseignant la répartition courante des dégats
        self.moved_damage_amount = 0  # nombre de dégats déplacés sur la répartition des dégats
        
        self.bot.event(self.on_reaction_add)  # enregistre cette méthode en temps qu'évènement
    
    async def on_reaction_add(self, reaction, user):
        if reaction.message.id == self.intersquads_fight_progression_message.id:
            role_names = [r.name for r in user.roles]  # noms des roles de l'auteur du message       
            
            if str(reaction) == '✅':
                if self.current_view == 'default':
                    if ('camp1' in role_names and self.current_battle.priority == 1) or ('camp2' in role_names and self.current_battle.priority == 2):
                        self.current_battle.change_priority()
                        await self.update_restrictions()
                        await reaction.remove(user)
                        
                    elif 'JDR PVP utils' not in role_names:
                        await reaction.remove(user)
                elif 'JDR PVP utils' not in role_names:
                    await reaction.remove(user)
            
            elif str(reaction) == '👀':
                if 'JDR PVP utils' not in role_names:
                    await reaction.remove(user)
                    if self.current_view == 'default':
                        await self.change_to_squads_view()
                    else:
                        await self.change_to_default_view()


    @commands.command(name='start_battle', help="starts the battle (MJ only)")
    @commands.has_role('MJ')
    async def start_battle(self, ctx):
        await ctx.channel.purge(limit=10)
        
        self.current_battle = battle_manager.Battle()
        self.has_battle_started = True
        self.armies_messages = [await ctx.send('hello'), await ctx.send('hello')]                
        
        await self.refresh_armies_message()    
    
    @commands.command(name='end_battle', help="ends the battle (MJ only)")
    @commands.has_role('MJ')
    async def end_battle(self, ctx):
        
        # envoie une sauvegarde des compositions des armées dans le 
        # salon des bilans des combats, utile pour se souvenir des pertes etc
        # si on veut pouvoir recharger les armées plus tard utiliser la commande save
        summary_channel = self.bot.get_channel(config['channels'].getint('summary'))
        await summary_channel.send(self.armies_messages[0].content, embed=self.armies_messages[0].embeds[0])
        
        self.current_battle = None
        self.has_battle_started = False
        await self.armies_messages[0].delete()
        await self.armies_messages[1].delete()
        
        self.armies_message = []
        
        await ctx.message.delete()
    
    @commands.command(name='reload', help='debug command, reload the default json file (MJ only)')
    @commands.has_role('MJ')
    async def reload_armies(self, ctx):
        if self.has_battle_started:
            self.current_battle.load_armies()
            await self.refresh_armies_message()
            await ctx.message.delete()        
    
    async def refresh_armies_message(self):
        main_armies_message, inter_squads_message = self.armies_messages
        
        channel = main_armies_message.channel
        
        await main_armies_message.delete()
        await inter_squads_message.delete()
        
        self.armies_messages[0] = await channel.send(content='', **self.format_both_camps_data())
        
        if self.current_battle.attacking_squad is not None: 
        
            embed = discord.Embed(title='Combats inter-escouades', description='\n', color=0x43b581)
            embed.add_field(name='attaquant', value=self.format_squad_data('', self.current_battle.attacking_squad, no_title=True))
            embed.add_field(name='défenseur', value=self.format_squad_data('', self.current_battle.defending_squad, no_title=True))
            embed.set_footer(text='force totale: {}\ndéfense totale: {}'.format(
                self.current_battle.get_total_strength(self.current_battle.attacking_squad),
                self.current_battle.get_total_thougness(self.current_battle.defending_squad)))
            
        else:
            embed = discord.Embed(title='Combats inter-escouades', description='aucun combat inter-escouades pour le moment', color=0x43b581)            
        
        self.armies_messages[1] = await channel.send(content='', embed=embed)        
        
    
    def format_both_camps_data(self, embeded=True, color=0x7289da):
        """format the composition of the armies into a clean, ready to send discord message content"""
        camp1_str = self.format_army_data(self.current_battle.army1_squads, marker='  ', max_length=50)
        camp2_str = self.format_army_data(self.current_battle.army2_squads, marker='  ', max_length=50)
        
        if not embeded:
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
            
            return dict(content=txt)
        
        else:
            embed = discord.Embed(title='Armées', description='\n', color=color)
            embed.add_field(name="Armée 1", value=camp1_str, inline=True)
            embed.add_field(name="Armée 2", value=camp2_str, inline=True)
            
            return dict(embed=embed)
            
        
    def format_army_data(self, data, marker='**', max_length=-1):
        txt = ''
        for i, squad in enumerate(data):
            title = 'escouade'
            txt += self.format_squad_data(i, squad, title=title, marker=marker, max_length=max_length)
            txt += '\n'
        return txt
    
    def format_squad_data(self, i, squad, title='escouade', marker='**', damage_repart=None, max_length=-1, no_title=False):
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
        
        if no_title:
            lines.pop(0)
        
        return '\n'.join(lines)
    
    
    async def create_intersquads_progression_embed(self, ctx):
        self.intersquads_fight_embed_data = dict(title='Undefined', whos_attacking=0, attackers_rolls='', defenders_rolls='', damage_repartition='')
        embed = discord.Embed(title=self.intersquads_fight_embed_data['title'], description='Ajoutez la réaction "✅" quand vous avez terminé')
        self.intersquads_fight_embed = embed
        
        self.intersquads_fight_progression_message = await ctx.send(embed=embed)
        await self.intersquads_fight_progression_message.add_reaction('✅')
        await self.intersquads_fight_progression_message.add_reaction('👀')        
    
    async def change_intersquads_progression_embed_data(self, **options):
        
        if self.intersquads_fight_progression_message is not None:
            embed = self.intersquads_fight_embed  # embed sur lequel travailler
            
            if 'title' in options:
                embed.title = options['title']
                self.intersquads_fight_embed_data['title'] = options['title']
            
            # options à partir de "whos_attacking"
            if 'whos_attacking' in options:
                
                if options['whos_attacking'] == 0:  # si cette option est mise à 0, vu que les autres options dépendent de
                    # celle ci, toutes les autres options sont mises à zéro
                    embed.clear_fields()
                    self.intersquads_fight_embed_data['attackers_rolls'] = ''
                    self.intersquads_fight_embed_data['defenders_rolls'] = ''
                    self.intersquads_fight_embed_data['damage_repartition'] = ''
                else:
                       
                    name = f'Le camp {options["whos_attacking"]} attaque'
                    value = 'Force totale: {}\nDéfense totale: {}'.format(
                            self.current_battle.get_total_strength(self.current_battle.attacking_squad),
                            self.current_battle.get_total_thougness(self.current_battle.defending_squad))
                    
                    if self.intersquads_fight_embed_data['whos_attacking'] == 0:
                        embed.add_field(name=name, value=value, inline=False)
                    else:
                        embed.set_field_at(0, name=name, value=value, inline=False)
                        
                self.intersquads_fight_embed_data['whos_attacking'] =  options['whos_attacking']
            
            # options à partir de "attackers_rolls"
            if self.intersquads_fight_embed_data['whos_attacking'] != 0:
                if 'attackers_rolls' in options:
                    
                    if options['attackers_rolls'] == '':  # pareil que pour whos_attacking, si cette option est mise à la
                        # valeur nulle, alors les options qui en dépendent sont remises à zéro
                        for _ in range(len(embed.fields) - 1):
                            embed.remove_field(1)
                        self.intersquads_fight_embed_data['defenders_rolls'] = ''
                        self.intersquads_fight_embed_data['damage_repartition'] = ''                            
                        
                    else:
                        name = 'Jets des attaquants:'
                        value = options['attackers_rolls']
                        
                        if self.intersquads_fight_embed_data['attackers_rolls'] == '':
                            embed.add_field(name=name, value=value, inline=False)
                        else:
                            embed.set_field_at(1, name=name, value=value, inline=False)
                            
                    self.intersquads_fight_embed_data['attackers_rolls'] =  options['attackers_rolls']
                
                # options à partir de "defenders_rolls"
                if self.intersquads_fight_embed_data['attackers_rolls'] != '':
                    if 'defenders_rolls' in options:
                        
                        if options['defenders_rolls'] == '':  # même chose que whos_attacking et attackers_rolls
                            for _ in range(len(embed.fields) - 2):
                                embed.remove_field(2)
                            self.intersquads_fight_embed_data['damage_repartition'] = ''                                                        
                            
                        else:
                            name = 'Jets des défenseurs:'
                            value = options['defenders_rolls']
                            
                            if self.intersquads_fight_embed_data['defenders_rolls'] == '':
                                embed.add_field(name=name, value=value, inline=False)
                            else:
                                embed.set_field_at(2, name=name, value=value, inline=False)
                                
                        self.intersquads_fight_embed_data['defenders_rolls'] =  options['defenders_rolls']                         
                    
                    # option "damage_repartition"
                    if self.intersquads_fight_embed_data['defenders_rolls'] != '':
                        if 'damage_repartition' in options:
                            
                            if options['damage_repartition'] == '':
                                embed.remove_field(3)
                            else:
                                name = 'Répartition des dégâts:'
                                value = options['damage_repartition']
                                
                                if self.intersquads_fight_embed_data['damage_repartition'] == '':
                                    embed.add_field(name=name, value=value, inline=False)
                                else:
                                    embed.set_field_at(3, name=name, value=value, inline=False)      
                            
                            self.intersquads_fight_embed_data['damage_repartition'] =  options['damage_repartition']
                            
                                
            await self.intersquads_fight_progression_message.edit(embed=embed)
            
            
    @commands.command(name="iis", help='begins an inter-squad battle against squad1 and squad2 (MJ only)')
    @commands.has_role('MJ')
    async def initiate_inter_squad_battle(self, ctx, squad1: int, squad2: int, whos_attacking: int):
        await ctx.message.delete()
        
        if self.has_battle_started:
            self.current_battle.initiate_inter_squad_battle(squad1, squad2, whos_attacking)
            await self.create_intersquads_progression_embed(ctx)
            await self.change_intersquads_progression_embed_data(whos_attacking=whos_attacking)
            
            await self.update_restrictions()       
            
            await self.refresh_armies_message()
            
        
    @commands.command(name="roll", help='roll the dices for the inter-squad battles actions')
    @commands.check(utils.restricted_command('roll'))
    async def roll(self, ctx, n: int):
        await ctx.message.delete()
        
        role_names = [r.name for r in ctx.message.author.roles]  # noms des roles de l'auteur du message
        if 'camp1' in role_names:
            
            self.roll1_list = await self._roll(ctx, n, self.current_battle.who_is_attacking == 1)
            self.roll1_actions = []
            
        elif 'camp2' in role_names:
            
            self.roll2_list = await self._roll(ctx, n, self.current_battle.who_is_attacking == 2)
            self.roll2_actions = []
        
    
    async def _roll(self, ctx, n, is_attacking):
        rolls = []
        for _ in range(n):
            rolls.append(random.randint(1, config['game'].getint('dice')))
            
        rolls.sort()  # trie les valeurs pour une meilleure visibilité
        
        txt = f"`valeurs: {', '.join(['{:>2}'.format(roll) for roll in rolls])}`\n`total: {sum(rolls)}`"
        
        if is_attacking:
            await self.change_intersquads_progression_embed_data(attackers_rolls=txt)
        else:
            await self.change_intersquads_progression_embed_data(defenders_rolls=txt)
        
        return rolls
    
    
    @commands.command(name='rm', help="removes values from the opponent's roll (MJ only)")
    @commands.has_role('MJ')
    async def remove(self, ctx, *args):
        role_names = [r.name for r in ctx.message.author.roles]
        if 'camp1' in role_names:
            await self._use(ctx, 2, *args, opening_text='jets supprimés')
        elif 'camp2' in role_names:
            await self._use(ctx, 1, *args, opening_text='jets supprimés')    
    
    @commands.command(name='u', help="uses values from your roll")
    @commands.check(utils.restricted_command('u'))    
    async def use(self, ctx, *args):
        role_names = [r.name for r in ctx.message.author.roles]
        if 'camp1' in role_names:
            await self._use(ctx, 1, *args)
        elif 'camp2' in role_names:
            await self._use(ctx, 2, *args) 
        
    async def _use(self, ctx, camp, *args, opening_text='derniers jets utlisés'):
        if camp == 1:
            rolls = self.roll1_list
            roll_actions = self.roll1_actions
        else:
            rolls = self.roll2_list
            roll_actions = self.roll2_actions
        
        if camp == self.current_battle.who_is_attacking:
            option_name = 'attackers_rolls'
        else:
            option_name = 'defenders_rolls'
        
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
        
        await self.change_intersquads_progression_embed_data(**{option_name: txt})
        
        await ctx.message.delete()
    
    @commands.command(name='damage', help="start the repartition of the damages inflicted to defender's units")
    @commands.check(utils.restricted_command('damage'))        
    async def start_damage_repartition(self, ctx):
        await ctx.message.delete()        
        
        self.moved_damage_amount = 0
                
        self.damage_repartition.clear()
        squad = self.current_battle.defending_squad
        
        txt = self.format_squad_data('', squad, title='défenseurs')
        
        await self.change_intersquads_progression_embed_data(damage_repartition=f'{txt}\ndégats totaux: 0')
                
    @commands.command(name='d', help='change the damage dealt to a specific unit')
    @commands.check(utils.restricted_command('d'))            
    async def damage(self, ctx, unit_id: int, amount: int):
        await self._damage(ctx, unit_id, amount)
        
        await ctx.message.delete()
    
    async def _damage(self, ctx, unit_id, amount):
        self.damage_repartition[unit_id] = amount
        total_damage = sum(self.damage_repartition.values())
        
        self.current_battle.set_damage_repartition(self.damage_repartition)
        preview = self.current_battle.get_preview_with_current_damage_repartition()
        
        txt = self.format_squad_data('', preview, title='défenseurs', damage_repart=self.damage_repartition)
        
        await self.change_intersquads_progression_embed_data(damage_repartition=f'{txt}\ndégats totaux: {total_damage}')
        
    @commands.command(name='m', help='moves a certain amount a damage from an unit to another')
    @commands.check(utils.restricted_command('m'))                
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
        
        await self.change_intersquads_progression_embed_data(
            damage_repartition=f'{self.intersquads_fight_embed_data["damage_repartition"]}\ndégats déplacés: {self.moved_damage_amount}')    
    
    @commands.command(name="apply", help='applies the damage repartition and updates the armies message (MJ only)')
    @commands.has_role('MJ')
    async def apply_damage(self, ctx):
        await ctx.message.delete()
        
        self.current_battle.apply_damages()
        await self.refresh_armies_message()    
        await self.change_intersquads_progression_embed_data(
            damage_repartition=f'{self.intersquads_fight_embed_data["damage_repartition"]}, appliqués') 
        
    @commands.command(name='end', help='ends the squad turn (MJ only)')
    @commands.has_role('MJ')
    async def end_squad_turn(self, ctx):
        await ctx.message.delete()
        self.current_battle.end_inter_squad_turn()
        await self.refresh_armies_message()
        await self.change_intersquads_progression_embed_data(whos_attacking=self.current_battle.who_is_attacking, attackers_rolls='')
        await self.update_restrictions()
        
    async def update_restrictions(self):
        attacking_camp = self.current_battle.who_is_attacking
        defending_camp = attacking_camp % 2 + 1
        
        if self.current_battle.priority_pass_count == 0:
            utils.set_authorizations(attacking_camp, 'roll')
            utils.set_authorizations(defending_camp)
            await self.change_intersquads_progression_embed_data(title='En attente des jets des attaquants')
            
        elif self.current_battle.priority_pass_count == 1:
            utils.set_authorizations(attacking_camp)
            utils.set_authorizations(defending_camp, 'roll')
            await self.change_intersquads_progression_embed_data(title='En attente des jets des défenseurs')
            
        elif self.current_battle.priority_pass_count == 2:
            utils.set_authorizations(attacking_camp, 'u', 'damage', 'd')
            utils.set_authorizations(defending_camp)   
            await self.change_intersquads_progression_embed_data(title='En attente des actions des attaquants')            
            
        elif self.current_battle.priority_pass_count == 3:
            utils.set_authorizations(attacking_camp)
            utils.set_authorizations(defending_camp, 'm', 'u')
            await self.change_intersquads_progression_embed_data(title='En attente des actions des défenseurs')                        
        
        else:
            utils.set_authorizations(attacking_camp)
            utils.set_authorizations(defending_camp)    
            await self.change_intersquads_progression_embed_data(title='Tour terminé')                                    
    
    async def change_to_squads_view(self):
        if self.current_view == 'default':             
            await self.intersquads_fight_progression_message.edit(embed=self.armies_messages[1].embeds[0])
            self.current_view = 'squads'
        
    async def change_to_default_view(self):
        if self.current_view == 'squads': 
            await self.intersquads_fight_progression_message.edit(embed=self.intersquads_fight_embed)
            self.current_view = 'default'
    
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
                
        await self.refresh_armies_message()
    
    @commands.command(name='save', help='save the composition of the army into a json file (for more advanced features use the advanced config pannel) (MJ only)')
    @commands.has_role('MJ')
    async def save(self, ctx, filename):
        with open(filename, 'w') as datafile:
            json.dump([self.current_battle.army1_squads, self.current_battle.army2_squads], datafile)
        await ctx.message.add_reaction('👍')
    
    @commands.command(name='update', help='updates changes made with the advanced configuration pannel (MJ only)')
    @commands.has_role('MJ')
    async def update(self, ctx):
        await self.refresh_armies_message()
        await ctx.message.delete()
