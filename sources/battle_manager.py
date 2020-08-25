# -*- coding:Utf-8 -*-

from .config import config
import json


class Battle:
    def __init__(self):
        self.army1_squads = []  # escouades de l'armée 1
        self.army2_squads = []  # escouades de l'armée 2

        self.load_armies()

        self.current_squad1 = None
        self.current_squad2 = None
        
        self.attacking_squad = None  # escouade en train d'attaquer l'escouade defending_squad
        self.defending_squad = None
        
        self.current_damage_repartition = {}  # répartition courante des dégats (second niveau)
        
        self.who_is_attacking = -1  # 1 pour le camp 1, 2 pour le camp 2, -1 pour non défini

    def initiate_inter_squad_battle(self, i1, i2, who_is_attacking):
        self.current_squad1 = self.army1_squads[i1]
        self.current_squad2 = self.army2_squads[i2]
        
        # redéfini attacking_squad et defending_squad en fonction de quelle escouade attaque et laquelle défend
        self.attacking_squad = self.current_squad1
        self.defending_squad = self.current_squad2        
        if who_is_attacking == 2:
            self.attacking_squad, self.defending_squad = self.defending_squad, self.attacking_squad
            
        self.who_is_attacking = who_is_attacking
            
    def end_inter_squad_turn(self):
        self.apply_damages()
        
        # à la fin du tour, les attaquants et les défenseurs sont échangés
        self.defending_squad, self.attacking_squad = self.attacking_squad, self.defending_squad
        self.who_is_attacking = 2 if self.who_is_attacking == 1 else 1
        
        self.current_damage_repartition = []
    
    def apply_damages(self):
        """apply damages to the defending squad"""
        for unit_id, damage in self.current_damage_repartition.items():
            self.defending_squad[unit_id]['pv'] -= damage
            
    def get_preview_with_current_damage_repartition(self):
        """return a copy of the defending squad with the damages applied, without actually applying them to the defending squad"""        
        preview = [unit.copy() for unit in self.defending_squad]
        for unit_id, damage in self.current_damage_repartition.items():
            preview[unit_id]['pv'] -= damage        
        return preview
    
    def set_damage_repartition(self, damage_repartition):
        self.current_damage_repartition = damage_repartition
        
    def load_army1_squads(self, path='default'):
        self.army1_squads = self._load(path)[0]

    def load_army2_squads(self, path='default'):
        self.army2_squads = self._load(path)[1]
    
    def load_armies(self, path='default'):
        """loads the armies the json file located using the path argument, or uses the default one"""
        self.army1_squads, self.army2_squads = self._load(path)
            
    @staticmethod
    def _load(path):
        if path == 'default':
            path = config['game']['datafile']
        with open(path, encoding='utf8') as datafile:
            data = json.load(datafile)
        return data
            
    def get_total_strength(self, squad):
        """returns the total strength of a squad, without taking into consideration the dead units"""
        total_strength = 0
        for unit in squad:
            if unit['pv'] > 0:
                total_strength += unit['atk']
        return total_strength
                
    def get_total_thougness(self, squad):
        """returns the total thougness of a squad, without taking into consideration the dead units"""        
        total_thougness = 0
        for unit in squad:
            if unit['pv'] > 0:
                total_thougness += unit['pv']
        return total_thougness
