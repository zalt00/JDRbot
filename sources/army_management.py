# -*- coding:Utf-8 -*-

import discord
from discord.ext import commands
from .config import config
import io
from typing import Any


class ArmyManagementCategory(commands.Cog, name='Army management commands'):
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.docs = {}
        
    def add_html_doc(self, raw_html: str, filename: str) -> None:
        if not filename.endswith('.html'):
            filename += '.html'
            
        html_doc = io.BytesIO(raw_html.encode())
        discord_file = discord.File(fp=html_doc, filename=filename)
        self.docs[filename] = discord_file
    
    @commands.has_role('MJ')    
    @commands.command(name='available_docs', help='gets the available docs (MJ only)')        
    async def get_available_docs(self, ctx):
        r = '`\n`'
        await ctx.send(f'Available docs are:\n`{r.join(self.docs.keys())}`')
    
    @commands.has_role('MJ')    
    @commands.command(name='send_doc', help='sends a doc (MJ only)')         
    async def send_doc(self, ctx, filename: str):
        if not filename.endswith('html'):
            filename += '.html'
            
        if filename in self.docs:
            await ctx.send(file=self.docs[filename])
            await ctx.message.delete()    
        else:
            await ctx.send(f'Erreur: le document "{filename}" n\'existe pas, utilisez la commande `available_docs` pour avoir la liste des documents disponibles')
            
