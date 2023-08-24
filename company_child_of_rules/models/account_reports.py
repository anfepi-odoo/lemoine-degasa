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

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def _init_filter_hierarchy(self, options, previous_options=None):
        # Only propose the option if there are groups
        rule_obj = self.env['ir.rule'].sudo()

        company_ids = self.env.companies.ids

        child_company_ids = rule_obj.get_child_company_ids(company_ids)

        if self.filter_hierarchy is not None and self.env['account.group'].search([('company_id', 'in', child_company_ids)], limit=1):
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy

    def _init_filter_multi_company(self, options, previous_options=None):

        if self.filter_multi_company:
            if self._context.get('allowed_company_ids'):
                rule_obj = self.env['ir.rule'].sudo()

                company_ids = self._context['allowed_company_ids']

                child_company_ids = rule_obj.get_child_company_ids(company_ids)

                # Retrieve the companies through the multi-companies widget.
                companies = self.env['res.company'].browse(child_company_ids)
            else:
                # When called from testing files, 'allowed_company_ids' is missing.
                # Then, give access to all user's companies.
                rule_obj = self.env['ir.rule'].sudo()

                company_ids = self.env.companies.ids

                child_company_ids = rule_obj.get_child_company_ids(company_ids)

                companies = self.env['res.company'].browse(child_company_ids)

            if len(companies) > 1:
                options['multi_company'] = [
                    {'id': c.id, 'name': c.name} for c in companies
                ]

    def print_xlsx(self, options):
        rule_obj = self.env['ir.rule'].sudo()
        company_ids = self._context['allowed_company_ids']
        allowed_company_ids = rule_obj.get_child_company_ids(company_ids)
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xlsx',
                         'financial_id': self.env.context.get('id'),
                         'allowed_company_ids': allowed_company_ids,
                         }
                }

# class AccountJournal(models.Model):
#     _inherit ='account.journal'


#     @api.model
#     def search(self, args, offset=0, limit=None, order=None, count=False):
#         res = super(AccountJournal, self).search(args, offset=offset, limit=limit, order=order, count=count)
#         print ("### RES: ", res)
#         return res
        
