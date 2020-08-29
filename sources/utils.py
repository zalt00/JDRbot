# -*- coding:Utf-8 -*-


_authorized_commands = [set(), set()]

def set_authorizations(camp, *authorized_names):
    _authorized_commands[camp - 1] = set(authorized_names)

def add_authorizations(camp, *authorized_ids):
    _authorized_commands[camp - 1] |= set(authorized_names)

def restricted_command(name):
    def _check(ctx):
        role_names = [r.name for r in ctx.message.author.roles]  # noms des roles de l'auteur du message
        if 'MJ' in role_names and False:
            return True
        elif 'camp1' in role_names:
            return name in _authorized_commands[0]
        elif 'camp2' in role_names:
            return name in _authorized_commands[1]
        else:
            return False
    return _check
    
