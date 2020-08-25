# -*- coding:Utf-8 -*-

from sources.app import bot, advanced_configuration_pannel
from sources import battle
from sources import army_management
from sources.config import config
import threading


def main():
    army_management_category = army_management.ArmyManagementCategory(bot)
    battle_category = battle.BattleCategory(bot)
    
    thread = threading.Thread(target=advanced_configuration_pannel, args=[army_management_category, battle_category])
    thread.start()
    
    bot.add_cog(army_management_category)
    bot.add_cog(battle_category)
    bot.run(config['bot']['token'])    

if __name__ == '__main__':
    main()
    
