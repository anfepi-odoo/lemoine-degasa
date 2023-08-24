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

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval, time

# class ResPartner(models.Model):
#     _inherit = 'res.partner'

#     @api.model
#     def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
#         if not self.env.user.dont_show_suppliers and not self.env.user.dont_show_customers:
#             res = super(ResPartner, self)._search(args, offset=offset, limit=limit,
#                                                     order=order, count=count, access_rights_uid=access_rights_uid)

#             return res

#         cr = self.env.cr
#         suppliers_and_customers_same_time = []
#         suppliers_ids = []
#         customers_ids = []

#         #### Proveedores y Clientes ####
#         cr.execute("""
#             select id,name,supplier_rank,supplier_rank from res_partner where supplier_rank>=1 and customer_rank>=1;
#             """)
#         cr_res = cr.fetchall()
#         if cr_res and cr_res[0] and cr_res[0][0]:
#             suppliers_and_customers_same_time = [x[0] for x in cr_res]

#         #### Proveedores ####
#         cr.execute("""
#             select id,name,supplier_rank,supplier_rank from res_partner where supplier_rank>=1 and customer_rank=0;
#             """)
#         cr_res = cr.fetchall()
#         if cr_res and cr_res[0] and cr_res[0][0]:
#             suppliers_ids = [x[0] for x in cr_res]

#         #### Clientes ####
#         cr.execute("""
#             select id,name,supplier_rank,supplier_rank from res_partner where supplier_rank = 0 and customer_rank>=1;
#             """)
#         cr_res = cr.fetchall()
#         if cr_res and cr_res[0] and cr_res[0][0]:
#             customers_ids = [x[0] for x in cr_res]

#         if self.env.user.dont_show_suppliers and not self.env.user.dont_show_customers:
#             ids_show = customers_ids + suppliers_and_customers_same_time
#             args.append(('id', 'in', tuple(ids_show)))

#         if self.env.user.dont_show_customers and not self.env.user.dont_show_suppliers:
#             ids_show = suppliers_ids + suppliers_and_customers_same_time
#             args.append(('id', 'in', tuple(ids_show)))

#             # args.append(('customer_rank', '=', 0))
#             # args.append(('supplier_rank', '>', 0))
#         res = super(ResPartner, self)._search(args, offset=offset, limit=limit,
#                                                     order=order, count=count, access_rights_uid=access_rights_uid)

#         return res

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     @api.model
#     def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):

#         if self.env.user.journal_ids.ids:
#             args.append(('journal_id', 'in', self.env.user.journal_ids.ids))
#         res = super(AccountMove, self)._search(args, offset=offset, limit=limit,
#                                                     order=order, count=count, access_rights_uid=access_rights_uid)

#         return res


class IrRule(models.Model):
    _inherit = 'ir.rule'

    multi_company_rule = fields.Boolean('Regla Especial Multi-company', help="Funciona tomando en cuenta los registros hijos de la company.")


    @api.onchange('multi_company_rule')
    def onchange_multi_company_rule(self):
        if self.multi_company_rule:
            if 'company_ids' not in self.domain_force:
                raise ValidationError("El Dominio no incluye el parametro 'company_ids' dentro de la definición de la Regla.")
    
    def get_child_company_ids(self, company_ids):
        """METODO RECURSIVO QUE OBTIENE LOS IDS DE UBICACIONES HIJAS DE UNA UBICACION DADA"""
        new_company_ids = []
        company_obj = self.env['res.company'].sudo()
        res = company_obj.browse(company_ids).sudo()
        #SE RECORREN LOS IDS
        for rec in company_obj.with_context(active_test=False).browse(company_ids):           
            child_ids = [x.id for x in rec.child_ids]
            location_inactives = company_obj.search([('id', 'child_of', child_ids)])
            if location_inactives:
                location_inactives_list = [x.id for x in location_inactives]
                child_ids.extend(location_inactives_list)
            new_company_ids.extend(child_ids)

        if new_company_ids != []:
            new_company_ids = self.get_child_company_ids(new_company_ids)
        new_company_ids.extend(company_ids)
        new_company_ids = list(set(new_company_ids))
        return new_company_ids

    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('self.env.uid', 'self.env.su', 'model_name', 'mode',
                       'tuple(self._compute_domain_context_values())'),
    )
    def _compute_domain(self, model_name, mode="read"):
        rules = self._get_rules(model_name, mode=mode)
        if not rules:
            return

        # browse user and rules as SUPERUSER_ID to avoid access errors!
        eval_context = self._eval_context()
        user_groups = self.env.user.groups_id
        global_domains = []                     # list of domains
        group_domains = []                      # list of domains
        for rule in rules.sudo():
            domain_force = rule.domain_force or ""
            if "('company_id', 'in', company_ids)" in domain_force:
                company_ids = self.env.companies.ids
                child_company_ids = self.get_child_company_ids(company_ids)
                new_domain_ids = "('company_id', 'in', %s)" % child_company_ids
                domain_force = domain_force.replace("('company_id', 'in', company_ids)",new_domain_ids)
            # evaluate the domain for the current user
            dom = safe_eval(domain_force, eval_context) if domain_force else []

            dom = expression.normalize_domain(dom)
            if not rule.groups:
                global_domains.append(dom)
            elif rule.groups & user_groups:
                group_domains.append(dom)
                # #### Cherman - Aqui hacemos la Magia - si es super regla va al inicio como global saltandose el OR ####
                # if rule.multi_company_rule:
                #     global_domains.append(dom)
                #     company_ids = self.env.companies.ids
                #     print ("############ company_ids: ",company_ids)
                #     print ("############ dom: ",dom)
                # else:
                #     group_domains.append(dom)

        # combine global domains and group domains
        if not group_domains:
            return expression.AND(global_domains)
        return expression.AND(global_domains + [expression.OR(group_domains)])

