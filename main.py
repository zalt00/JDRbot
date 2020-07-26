# -*- coding:Utf-8 -*-

from sources.app import bot, advanced_configuration_pannel
import sources.battle_category
from sources.config import config
import threading


def main():
    battle_category = sources.battle_category.BattleCategory(bot)
    
    thread = threading.Thread(target=advanced_configuration_pannel, args=[battle_category])
    thread.start()
    
    bot.add_cog(battle_category)
    bot.run(config['bot']['token'])    

if __name__ == '__main__':
    main()
    
