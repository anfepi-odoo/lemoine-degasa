from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = 'pos.config'

    max_cash_limit = fields.Float(string="Límite Máximo de Efectivo", default=0.0, help="Nivel máximo de efectivo permitido en la caja.")


