# -*- encoding: utf-8 -*-
# Coded by German Ponce Dominguez 
#     ▬▬▬▬▬.◙.▬▬▬▬▬  
#       ▂▄▄▓▄▄▂  
#    ◢◤█▀▀████▄▄▄▄▄▄ ◢◤  
#    █▄ █ █▄ ███▀▀▀▀▀▀▀ ╬  
#    ◥ █████ ◤  
#     ══╩══╩═  
#       ╬═╬  
#       ╬═╬ Dream big and start with something small!!!  
#       ╬═╬  
#       ╬═╬ You can do it!  
#       ╬═╬   Let's go...
#    ☻/ ╬═╬   
#   /▌  ╬═╬   
#   / \
# Cherman Seingalt - german.ponce@outlook.com

import logging
import warnings
import json

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval, time


class AccountAccount(models.Model):
    _inherit ='account.account'

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        company_count = 1
        self.env.cr.execute("select count(*) from res_company;")
        cr_res = self.env.cr.fetchall()
        company_count = cr_res[0][0]
        for account in self:
            if company_count > 1:
                name = account.code + ' ' + account.name + ' [' + account.company_id.name + ']'
            else:
                name = account.code + ' ' + account.name
            #name = account.code + ' ' + account.name
            result.append((account.id, name))
        return result

class AccountAnalyticAccount(models.Model):
    _inherit ='account.analytic.account'

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        company_count = 1
        self.env.cr.execute("select count(*) from res_company;")
        cr_res = self.env.cr.fetchall()
        company_count = cr_res[0][0]
        for account in self:
            if account.company_id:
                if company_count > 1:
                    if account.code:
                        name = account.code + ' ' + account.name + ' [' + account.company_id.name + ']'
                    else:
                        name = account.name + ' [' + account.company_id.name + ']'
                else:
                    if account.code:
                        name = account.code 
                    if account.name:
                        name = name + ' ' + account.name
            else:
                if account.code:
                    name = account.code 
                if account.name:
                    name = name + ' ' + account.name
            #name = account.code + ' ' + account.name
            result.append((account.id, name))
        return result
        