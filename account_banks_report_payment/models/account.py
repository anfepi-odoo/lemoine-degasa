# -*- coding: utf-8 -*-
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


from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from odoo.tools.float_utils import float_compare
import datetime
import calendar

import tempfile

import xlwt
from io import BytesIO
import base64

from itertools import zip_longest

import logging
_logger = logging.getLogger(__name__)

logger_debug = False

format_date = "%Y-%m-%d"

class AccountMoveBankReportData(models.Model):
    _name = 'account.move.bank.report.data'
    _description = 'Datos Reporte Movimientos Contables de Banco'
    _order = "payment_date"

    def _get_current_user(self):
        return self.env.user.id

    name = fields.Char('Nombre Registro',size=256)

    payment_type = fields.Selection([
                                        ('customer','Cliente'),
                                        ('supplier','Proveedor'),
                                        ('internal_transfer','Interno')
                                    ], string="Tipo de Pago")
    reference = fields.Char('Referencia Factura',size=256)
    journal_id = fields.Many2one('account.journal', 'Diario')
    payment_id = fields.Many2one('account.payment', 'Pago')
    statement_id = fields.Many2one('account.bank.statement', 'Estado de Cuenta')
    move_id = fields.Many2one('account.move', 'Movimiento')
    payment_date  = fields.Date(string='Fecha Pago')
    payment_amount  = fields.Float(string='Monto Pago')
    iva_amount  = fields.Float(string='Monto IVA')
    account_origin_id = fields.Many2one('account.account', 'Cuenta Origen')
    partner_id = fields.Many2one('res.partner', 'Contacto')
    invoice_id = fields.Many2one('account.move', 'Factura')
    invoice_date  = fields.Date(string='Fecha Factura')
    invoice_amount  = fields.Float(string='Monto Factura')
    uuid = fields.Char('UUID',size=256)
    user_id = fields.Many2one('res.users', 'Usuario', default=_get_current_user)

    payment_currency_id = fields.Many2one('res.currency', string="Moneda Pago")
    invoice_currency_id = fields.Many2one('res.currency', string="Moneda Factura")
    payment_reference = fields.Char('Referencia Pago',size=256)
    company_id = fields.Many2one('res.company', string="Compañia")

class AccountMoveBankReportWizard(models.TransientModel):
    _name = 'account.move.bank.report.wizard'
    _description = 'Asistente Reporte Movimientos Contables de Banco'

    @api.model  
    def default_get(self, fields):
        res = super(AccountMoveBankReportWizard, self).default_get(fields)
        
        child_company_ids = self.get_child_company_ids([self.env.company.id])

        journal_ids = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id','in',child_company_ids)])
        
        if journal_ids:
            res.update(journal_ids=[(6,0,[x.id for x in journal_ids])])
        return res

    def _get_date(self):
        currentDate = datetime.date.today()
        firstDayOfMonth = datetime.date(currentDate.year, currentDate.month, 1)
        return firstDayOfMonth

    def _get_date_end(self):
        currentDate = datetime.date.today()
        lastDayOfMonth = datetime.date(currentDate.year, currentDate.month, calendar.monthrange(currentDate.year, currentDate.month)[1])
        return lastDayOfMonth

    date       = fields.Date(string='Fecha Inicio', default=_get_date, required=True)
    date_stop       = fields.Date(string='Fecha fin', default=_get_date_end, required=True)
    journal_ids = fields.Many2many('account.journal', 'wizard_report_bank_journal_rel', 'wizard_br_id', 'journal_id',
                                     string='Diarios Contables', required=True)

    report_output = fields.Selection([('xlsx','Excel'),('view','Análisis')], string="Tipo de Reporte", default="view", readonly=True)

    xlsx_ready = fields.Boolean('Archivo Listo')

    xlsx_datas_fname = fields.Char('Nombre Archivo',size=256)

    xlsx_file = fields.Binary("Reporte")

    include_statements = fields.Boolean('Incluir Estados de Cuenta')

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


    def get_current_report(self):
        data_obj = self.env['account.move.bank.report.data']
        data_list_statements_ids = []
        data_list_payments_ids = []

        data_list_payments_ids = self.insert_data_from_payments()
        if self.include_statements:
            data_list_statements_ids = self.insert_data_from_bank_statements()

        data_list_ids = data_list_statements_ids + data_list_payments_ids

        if self.report_output == 'xlsx':
            res = self.generate_report_waybill_xlsx()
            return res
        else:
            return {
                'domain': [('id', 'in', data_list_ids)],
                'name': 'Reporte de operaciones bancarias',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'context': {'tree_view_ref': 'account_banks_report_payment.account_move_bank_report_tree'},
                'res_model': 'account.move.bank.report.data',
                'type': 'ir.actions.act_window'
                }
                    
        return True

    def _get_global_taxes(self, roundnumber=2, invoice=False):
        
        round_char = "%."+str(roundnumber)+"f"

        taxes = {}
        #### Cambio Retenciones ####
        taxes_retenciones_ids = []
        for line in invoice.invoice_line_ids.filtered('price_subtotal'):
            price = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
            # tax_line = {tax['id']: tax for tax in line.tax_ids.compute_all(
            #     price, line.currency_id, line.quantity, line.product_id, line.partner_id, self.move_type in ('in_refund', 'out_refund'))['taxes']}
            taxes_line = line.filtered('price_subtotal').tax_ids.flatten_taxes_hierarchy()
            for tax in taxes_line:
                if logger_debug:
                    _logger.info("\n#### tax :%s " % tax)

                if tax.amount_type =='percent':
                    tax_importe = abs(tax.amount) / 100.0 * line.price_subtotal
                elif tax.amount_type =='fixed':
                    tax_importe = abs(tax.amount)
                else:
                    continue

                rate = round(abs(tax.amount), roundnumber)

                tax_amount = round_char % tax_importe
                line_base = round_char % (line.price_subtotal or 0.0)

                if logger_debug:
                    _logger.info("\n#### tax.amount :%s " % tax.amount)
                    _logger.info("\n#### tax_amount :%s " % tax_amount)
                    _logger.info("\n#### line_base :%s " % line_base)

                if tax.id not in taxes:
                    tags_name = ""
                    if tax.invoice_repartition_line_ids:
                        for invrepart in tax.invoice_repartition_line_ids:
                            for tag in invrepart.tag_ids:
                                tags_name = tags_name+" | "+tag.name if tags_name else tag.name
                    if not tags_name:
                        tags_name = tax.name

                    if not 'IVA' in tags_name.upper():
                        if 'IVA' in tax.name.upper():
                            tags_name = tags_name+" | "+'IVA'
                    taxes.update({tax.id: {
                        'name': tags_name,
                        'amount': tax_amount,
                        'rate': rate if tax.amount_type == 'fixed' else rate / 100.0,
                        'tax_amount': tax_amount, #tax_dict.get('amount', tax.amount),
                        'amount_base': line_base,
                    }})

                else:
                    amount_old = float(taxes[tax.id]['amount'])
                    tax_amount_old = float(taxes[tax.id]['tax_amount'])
                    amount_base_old = float(taxes[tax.id]['amount_base'])

                    amount_new = amount_old + float(tax_amount)
                    tax_amount_new = tax_amount_old + float(tax_amount)
                    amount_base_new = amount_base_old + float(line_base)

                    taxes[tax.id].update({
                        'amount': round_char %  amount_new,
                        'tax_amount': round_char %  tax_amount_new,
                        'amount_base': round_char %  amount_base_new,
                    })

        return taxes

    def insert_data_from_payments(self, data_list_payments_ids=[]):
        
        data_obj = self.env['account.move.bank.report.data']
        invoice_obj = self.env['account.move']
        cr = self.env.cr
        cr.execute("""
                    delete from account_move_bank_report_data where user_id=%s;
                    """, (self.env.user.id, ))
        # _name = 'account.move.bank.report.data'
        # journal_id = fields.Many2one('account.journal', 'Diario')
        # move_id = fields.Many2one('account.move', 'Movimiento')
        # payment_date  = fields.Date(string='Fecha Pago')
        # payment_amount  = fields.Float(string='Monto Pago')
        # iva_amount  = fields.Float(string='Monto IVA')
        # account_origin_id = fields.Many2one('account.account', 'Cuenta Origen')
        # partner_id = fields.Many2one('res.partner', 'Contacto')
        # invoice_id = fields.Many2one('account.move', 'Factura')
        # invoice_date  = fields.Date(string='Fecha Factura')
        # invoice_amount  = fields.Float(string='Monto Factura')
        # reference = fields.Char('Referencia',size=256)
        # uuid = fields.Char('UUID',size=256)
        
        # Customer Payments: ('partner_type', '=', 'customer')
        # Vendor Payments: ('partner_type', '=', 'supplier')
        # Transfers: ('is_internal_transfer', '=', True)

        ### Pagos ####

        payment_obj = self.env['account.payment']
        payment_ids = payment_obj.search([('date','>=',self.date),('date','<=',self.date_stop),
                                          ('state','=','posted'),('journal_id','in',tuple(self.journal_ids.ids))])
        # payment_ids = payment_obj.search([('id','=',932)])

        if not payment_ids:
            raise UserError("No se encontro información.")

        user_id = self.env.user.id
        for payment in payment_ids:
            iva_amount = 0.0 ## Pendiente sacar el dato.
            invoice_br = False ## Pendiente sacar el dato.
            partner_type = payment.partner_type
            payment_type = "internal_transfer"
            if partner_type == 'customer':
                payment_type = "customer"
            elif partner_type == 'supplier':
                payment_type = "supplier"

            name = "Pago: %s" % payment.name

            if payment_type == "customer" :
                invoices_related_to_payment = payment.reconciled_invoice_ids
            elif payment_type == 'supplier':
                invoices_related_to_payment = payment.reconciled_bill_ids

            if not invoices_related_to_payment:
                invoices_related_to_payment = invoice_obj.search([('payment_id','=',payment.id),
                                                                  ('move_type','in',('out_invoice','out_refund','in_invoice','in_refund'))])


            if invoices_related_to_payment:
                #### buscamos los montos que le corresponden a cada factura ####
                only_one_invoice = True if len(invoices_related_to_payment) == 1 else False
                for invoice in invoices_related_to_payment.sorted(key=lambda x: (x.invoice_date_due, x.name)):
                    ### Si no es Factura de Cliente no Genera la Relación de Pago y Factura ####
                    if logger_debug:
                        _logger.info("\n#### invoice.id: %s " % invoice)
                        _logger.info("\n#### invoice.name: %s " % invoice.name)
                        _logger.info("\n#### invoice.invoice_date: %s " % invoice.invoice_date)
                        _logger.info("\n#### payment.id: %s " % payment.id)
                        _logger.info("\n#### payment.name: %s " % payment.name)

                    monto_aplicado = 0.0 
                    monto_pago = 0.0
                    if not only_one_invoice:
                        for xline in payment.move_id.line_ids:
                            if payment_type == "customer" :
                                for r in xline.matched_debit_ids:
                                    _logger.info("=====================")
                                    for x in r._fields:
                                        _logger.info("%s: %s" % (x, r[x]))
                                    if r.debit_move_id.move_id.id == invoice.id:
                                        if invoice.currency_id == invoice.company_id.currency_id == payment.currency_id:
                                            monto_pago = r.amount
                                        elif (invoice.company_id.currency_id == payment.currency_id and \
                                            invoice.currency_id != invoice.company_id.currency_id) or \
                                            invoice.currency_id == payment.currency_id:
                                            monto_pago = r.debit_amount_currency
                                        else:
                                            ### Modificación invoice_date ####
                                            monto_pago = invoice.company_id.currency_id.with_context({'date': invoice.invoice_date}).compute(r.amount, invoice.currency_id)

                            elif payment_type == 'supplier':
                                for r in xline.matched_credit_ids:
                                    _logger.info("=====================")
                                    for x in r._fields:
                                        _logger.info("%s: %s" % (x, r[x]))
                                    if r.credit_move_id.move_id.id == invoice.id:
                                        if invoice.currency_id == invoice.company_id.currency_id == payment.currency_id:
                                            monto_pago = r.amount
                                        elif (invoice.company_id.currency_id == payment.currency_id and \
                                            invoice.currency_id != invoice.company_id.currency_id) or \
                                            invoice.currency_id == payment.currency_id:
                                            monto_pago = r.debit_amount_currency
                                        else:
                                            ### Modificación invoice_date ####
                                            monto_pago = invoice.company_id.currency_id.with_context({'date': invoice.invoice_date}).compute(r.amount, invoice.currency_id)
                    else:
                        if invoice.currency_id == invoice.company_id.currency_id == payment.currency_id:
                            monto_pago = payment.amount
                        elif (invoice.company_id.currency_id == payment.currency_id and \
                            invoice.currency_id != invoice.company_id.currency_id) or \
                            invoice.currency_id == payment.currency_id:
                            monto_pago = payment.amount
                        else:
                            ### Modificación invoice_date ####
                            monto_pago = invoice.company_id.currency_id.with_context({'date': invoice.invoice_date}).compute(payment.amount, invoice.currency_id)
                    
                    if monto_pago:
                        #### Sacamos los Impuestos ####
                        invoice_taxes = self._get_global_taxes(2, invoice)

                        ##### buscamos el porcentaje que le corresponde al pago ####
                        if logger_debug:
                            _logger.info("\n###### monto_pago: %s " % monto_pago)
                        monto_pago_payment_currency = 0.0
                        invoice_id = invoice
                        invoice_amount_total = invoice_id.amount_total
                        invoice_amount_total_payment_currency = 0.0

                        x_date = fields.Date.context_today(self)
                        if payment.currency_id==payment.company_id.currency_id or payment.currency_id == invoice_id.currency_id:
                            x_date = payment.date
                        elif payment.currency_id != invoice_id.currency_id:
                            x_date = invoice_id.invoice_date

                        invoice_currency_rate = 1
                        if not invoice_id or invoice_id.currency_id == payment.env.user.company_id.currency_id:
                            invoice_currency_rate = 1.0
                        else:
                            invoice_currency_rate = round(invoice_id.currency_id.with_context({'date': payment.date}).compute(1, payment.currency_id, round=False), 6)
                        
                        #revisa la cantidad que se va a pagar en el docuemnto
                        equivalencia_dr  = round(invoice_currency_rate,6)
                        if payment.currency_id.id != invoice_id.currency_id.id:
                            if payment.currency_id.name == 'MXN':
                                if logger_debug:
                                    _logger.info("\n########## Factura Moneda E. Pago en Pesos >>>> ")
                                invoice_amount_total_payment_currency = invoice_id.amount_total / equivalencia_dr
                                monto_pago_payment_currency = monto_pago / equivalencia_dr
                            else:
                                if logger_debug:
                                    _logger.info("\n########## Factura Moneda E. Pago en Moneda E. >>>> ")
                                invoice_amount_total_payment_currency = invoice_id.amount_total / equivalencia_dr
                                monto_pago_payment_currency = monto_pago / equivalencia_dr
                        else:
                            equivalencia_dr = 1
                            invoice_amount_total_payment_currency = invoice_id.amount_total
                            monto_pago_payment_currency = monto_pago

                        if equivalencia_dr == 1:
                           decimal_presicion = 2
                        else:
                           decimal_presicion = 6


                        paid_percentage = monto_pago_payment_currency / invoice_amount_total_payment_currency

                        if paid_percentage >= 0.9999:
                            paid_percentage = 1.0

                        if logger_debug:
                            _logger.info("\n########## paid_percentage: %s " % paid_percentage)
                            _logger.info("\n########## invoice_taxes: %s " % invoice_taxes)

                        ##### buscamos el monto de IVA que le corresponde al pago ####
                        for tax in invoice_taxes.keys():
                            tax_vals = invoice_taxes[tax]
                            tax_name = tax_vals.get('name')
                            tax_amount = float(tax_vals.get('amount',0.0))
                            if 'IVA' in tax_name.upper():
                                iva_amount = tax_amount * paid_percentage
                                break
                        if iva_amount > 0.0:
                            if invoice.currency_id == invoice.company_id.currency_id == payment.currency_id:
                                _logger.info("\n######## 000000 El monto de IVA es el mismo que la moneda. ")
                            else:
                                if payment.currency_id == invoice.company_id.currency_id:
                                    _logger.info("\n######## 1111 El monto de IVA - Pago en MXN")
                                    iva_amount = round(invoice_id.currency_id.with_context({'date': payment.date}).compute(iva_amount, payment.currency_id, round=False), 6)
                                else:
                                    _logger.info("\n######## 2222 El monto de IVA - Pago en Otra Moneda")
                                    iva_amount = round(payment.currency_id.with_context({'date': payment.date}).compute(iva_amount, invoice_id.currency_id, round=False), 6)
                    
                        ##################################################################

                    name = "Pago: %s" % payment.name
                    if invoice:
                        name = name+" "+" Factura: "+invoice.name
                    
                    xvals = {   
                            'name': name,
                            'payment_type': payment_type,
                            'journal_id': payment.journal_id.id,
                            'move_id': payment.move_id.id,
                            'payment_currency_id': payment.currency_id.id,
                            'payment_date': payment.date,
                            'payment_reference': payment.ref,
                            'payment_amount': monto_pago,
                            'iva_amount': iva_amount,
                            'account_origin_id': payment.destination_account_id.id,
                            'partner_id': payment.partner_id.id,
                            'invoice_id': invoice.id if invoice else False,
                            'invoice_currency_id': invoice.currency_id.id if invoice else False,
                            'invoice_date': invoice.invoice_date if invoice else False,
                            'invoice_amount': invoice.amount_total if invoice else 0.0,
                            'reference': invoice.ref if invoice else False,
                            'uuid': invoice.l10n_mx_edi_cfdi_uuid if invoice else False,
                            'user_id': user_id,
                            'payment_id': payment.id,
                            'company_id': payment.company_id.id,
                        }
                    data_id = data_obj.create(xvals)
                    data_list_payments_ids.append(data_id.id)


            else:
                xvals = {   
                            'name': name,
                            'payment_type': payment_type,
                            'journal_id': payment.journal_id.id,
                            'move_id': payment.move_id.id,
                            'payment_currency_id': payment.currency_id.id,
                            'payment_date': payment.date,
                            'payment_reference': payment.ref,
                            'payment_amount': payment.amount,
                            'iva_amount': iva_amount,
                            'account_origin_id': payment.destination_account_id.id,
                            'partner_id': payment.partner_id.id,
                            'invoice_id': invoice_br.id if invoice_br else False,
                            'invoice_currency_id': invoice_br.currency_id.id if invoice_br else False,
                            'invoice_date': invoice_br.invoice_date if invoice_br else False,
                            'invoice_amount': invoice_br.amount_total if invoice_br else 0.0,
                            'reference': invoice_br.ref if invoice_br else False,
                            'uuid': invoice_br.l10n_mx_edi_cfdi_uuid if invoice_br else False,
                            'user_id': user_id,
                            'payment_id': payment.id,
                            'company_id': payment.company_id.id,
                        }
                data_id = data_obj.create(xvals)
                data_list_payments_ids.append(data_id.id)
        
        return data_list_payments_ids

    def insert_data_from_bank_statements(self, data_list_statements_ids=[]):
        data_obj = self.env['account.move.bank.report.data']
        invoice_obj = self.env['account.move']
        cr = self.env.cr
        cr.execute("""
                    select account_bank_statement_line.id from account_bank_statement_line 
                                      join account_bank_statement
                                        on account_bank_statement.id = account_bank_statement_line.statement_id
                                      join account_move 
                                        on account_move.id = account_bank_statement_line.move_id
                                      where account_bank_statement.journal_id in %s
                                       and account_bank_statement_line.is_reconciled = True
                                       and account_move.date between %s and %s;
                    """, (tuple(self.journal_ids.ids), str(self.date), str(self.date_stop)))

        cr_res = cr.fetchall()
        statement_line_ids = []
        if cr_res and cr_res[0] and cr_res[0][0]:
            statement_line_ids = [x[0] for x in cr_res]
        else:
            return data_list_statements_ids
        # _name = 'account.move.bank.report.data'
        # journal_id = fields.Many2one('account.journal', 'Diario')
        # move_id = fields.Many2one('account.move', 'Movimiento')
        # payment_date  = fields.Date(string='Fecha Pago')
        # payment_amount  = fields.Float(string='Monto Pago')
        # iva_amount  = fields.Float(string='Monto IVA')
        # account_origin_id = fields.Many2one('account.account', 'Cuenta Origen')
        # partner_id = fields.Many2one('res.partner', 'Contacto')
        # invoice_id = fields.Many2one('account.move', 'Factura')
        # invoice_date  = fields.Date(string='Fecha Factura')
        # invoice_amount  = fields.Float(string='Monto Factura')
        # reference = fields.Char('Referencia',size=256)
        # uuid = fields.Char('UUID',size=256)
        
        # Customer Payments: ('partner_type', '=', 'customer')
        # Vendor Payments: ('partner_type', '=', 'supplier')
        # Transfers: ('is_internal_transfer', '=', True)

        ### Pagos ####

        statement_line_obj = self.env['account.bank.statement.line']

        user_id = self.env.user.id
        for payment in statement_line_obj.browse(statement_line_ids):

            account_origin_id = False

            for line in payment.move_id.line_ids:
                if line.account_id:
                    if line.account_id.reconcile:
                        # print ("############## LINE ACCOUNT ID: ", line.account_id)
                        # print ("############## LINE ACCOUNT NAME: ", line.account_id.name)
                        account_origin_id = line.account_id.id
            iva_amount = 0.0 ## Pendiente sacar el dato.
            invoice_br = False ## Pendiente sacar el dato.
            # partner_type = payment.partner_type
            # payment_type = "internal_transfer"
            # if partner_type == 'customer':
            #     payment_type = "customer"
            # elif partner_type == 'supplier':
            #     payment_type = "supplier"

            # name = "Estado de Cuenta: %s" % payment.name

            payment_type = 'internal_transfer'
            
            ######################## Codigo Factura Electronica #################
            move = payment.move_id
            invoice = False

            if move.payment_id:
                currency = move.payment_id.currency_id
                total_amount = move.payment_id.amount
            else:
                if move.statement_line_id.foreign_currency_id:
                    total_amount = move.statement_line_id.amount_currency
                    currency = move.statement_line_id.foreign_currency_id
                else:
                    total_amount = move.statement_line_id.amount
                    currency = move.statement_line_id.currency_id

            pay_rec_lines = move.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
            paid_amount = abs(sum(pay_rec_lines.mapped('amount_currency')))

            mxn_currency = self.env["res.currency"].search([('name', '=', 'MXN')], limit=1)
            if move.currency_id == mxn_currency:
                rate_payment_curr_mxn = None
                paid_amount_comp_curr = paid_amount
            else:
                rate_payment_curr_mxn = move.currency_id._convert(1.0, mxn_currency, move.company_id, move.date, round=False)
                paid_amount_comp_curr = move.company_currency_id.round(paid_amount * rate_payment_curr_mxn)

            for field1, field2 in (('debit', 'credit'), ('credit', 'debit')):
                for partial in pay_rec_lines[f'matched_{field1}_ids']:
                    payment_line = partial[f'{field2}_move_id']
                    invoice_line = partial[f'{field1}_move_id']
                    invoice_amount = partial[f'{field1}_amount_currency']
                    exchange_move = invoice_line.full_reconcile_id.exchange_move_id
                    invoice = invoice_line.move_id

            ###################################################################################################################

            if invoice:
                #### buscamos los montos que le corresponden a cada factura ####
                ### Si no es Factura de Cliente no Genera la Relación de Pago y Factura ####
                if logger_debug:
                    _logger.info("\n#### invoice.id: %s " % invoice)
                    _logger.info("\n#### invoice.name: %s " % invoice.name)
                    _logger.info("\n#### invoice.invoice_date: %s " % invoice.invoice_date)
                    _logger.info("\n#### payment.id: %s " % payment.id)
                    _logger.info("\n#### payment.name: %s " % payment.name)

                if invoice.move_type in ('out_invoice','out_refund'):
                    payment_type = 'customer'
                else:
                    payment_type = 'supplier'
                monto_aplicado = 0.0 
                monto_pago = payment.amount
                for xline in payment.move_id.line_ids:
                    if xline.matched_debit_ids:
                        for r in xline.matched_debit_ids:
                            # _logger.info("=====================")
                            # for x in r._fields:
                            #     _logger.info("%s: %s" % (x, r[x]))
                            if r.debit_move_id.move_id.id == invoice.id:
                                if invoice.currency_id == invoice.company_id.currency_id == payment.currency_id:
                                    monto_pago = r.amount
                                elif (invoice.company_id.currency_id == payment.currency_id and \
                                    invoice.currency_id != invoice.company_id.currency_id) or \
                                    invoice.currency_id == payment.currency_id:
                                    monto_pago = r.debit_amount_currency
                                else:
                                    ### Modificación invoice_date ####
                                    monto_pago = invoice.company_id.currency_id.with_context({'date': invoice.invoice_date}).compute(r.amount, invoice.currency_id)

                    elif xline.matched_credit_ids:
                        for r in xline.matched_credit_ids:
                            # _logger.info("=====================")
                            # for x in r._fields:
                            #     _logger.info("%s: %s" % (x, r[x]))
                            if r.credit_move_id.move_id.id == invoice.id:
                                if invoice.currency_id == invoice.company_id.currency_id == payment.currency_id:
                                    monto_pago = r.amount
                                elif (invoice.company_id.currency_id == payment.currency_id and \
                                    invoice.currency_id != invoice.company_id.currency_id) or \
                                    invoice.currency_id == payment.currency_id:
                                    monto_pago = r.debit_amount_currency
                                else:
                                    ### Modificación invoice_date ####
                                    monto_pago = invoice.company_id.currency_id.with_context({'date': invoice.invoice_date}).compute(r.amount, invoice.currency_id)
                    
                    if monto_pago:
                        #### Sacamos los Impuestos ####
                        invoice_taxes = self._get_global_taxes(2, invoice)

                        ##### buscamos el porcentaje que le corresponde al pago ####
                        if logger_debug:
                            _logger.info("\n###### monto_pago: %s " % monto_pago)
                        monto_pago_payment_currency = 0.0
                        invoice_id = invoice
                        invoice_amount_total = invoice_id.amount_total
                        invoice_amount_total_payment_currency = 0.0

                        x_date = fields.Date.context_today(self)
                        if payment.currency_id==payment.company_id.currency_id or payment.currency_id == invoice_id.currency_id:
                            x_date = payment.date
                        elif payment.currency_id != invoice_id.currency_id:
                            x_date = invoice_id.invoice_date

                        invoice_currency_rate = 1
                        if not invoice_id or invoice_id.currency_id == payment.env.user.company_id.currency_id:
                            invoice_currency_rate = 1.0
                        else:
                            invoice_currency_rate = round(invoice_id.currency_id.with_context({'date': payment.date}).compute(1, payment.currency_id, round=False), 6)
                        
                        #revisa la cantidad que se va a pagar en el docuemnto
                        equivalencia_dr  = round(invoice_currency_rate,6)
                        if payment.currency_id.id != invoice_id.currency_id.id:
                            if payment.currency_id.name == 'MXN':
                                if logger_debug:
                                    _logger.info("\n########## Factura Moneda E. Pago en Pesos >>>> ")
                                invoice_amount_total_payment_currency = invoice_id.amount_total / equivalencia_dr
                                monto_pago_payment_currency = monto_pago / equivalencia_dr
                            else:
                                if logger_debug:
                                    _logger.info("\n########## Factura Moneda E. Pago en Moneda E. >>>> ")
                                invoice_amount_total_payment_currency = invoice_id.amount_total / equivalencia_dr
                                monto_pago_payment_currency = monto_pago / equivalencia_dr
                        else:
                            equivalencia_dr = 1
                            invoice_amount_total_payment_currency = invoice_id.amount_total
                            monto_pago_payment_currency = monto_pago

                        if equivalencia_dr == 1:
                           decimal_presicion = 2
                        else:
                           decimal_presicion = 6


                        paid_percentage = 1
                        if monto_pago_payment_currency and invoice_amount_total_payment_currency:
                            paid_percentage = monto_pago_payment_currency / invoice_amount_total_payment_currency

                        if paid_percentage >= 0.9999:
                            paid_percentage = 1.0

                        if logger_debug:
                            _logger.info("\n########## paid_percentage: %s " % paid_percentage)
                            _logger.info("\n########## invoice_taxes: %s " % invoice_taxes)

                        ##### buscamos el monto de IVA que le corresponde al pago ####
                        for tax in invoice_taxes.keys():
                            tax_vals = invoice_taxes[tax]
                            tax_name = tax_vals.get('name')
                            tax_amount = float(tax_vals.get('amount',0.0))
                            if 'IVA' in tax_name.upper():
                                iva_amount = tax_amount * paid_percentage
                                break
                        if iva_amount > 0.0:
                            if not invoice_id or invoice_id.currency_id == payment.env.user.company_id.currency_id:
                                _logger.info("\n######## El monto de IVA es el mismo que la moneda. ")
                            else:
                                iva_amount = round(payment.currency_id.with_context({'date': payment.date}).compute(iva_amount, invoice_id.currency_id, round=False), 6)
      
                        ##################################################################

                name = "Estado de Cuenta: %s" % payment.name
                if invoice:
                    name = name+" "+" Factura: "+invoice.name
                
                xvals = {   
                        'name': name,
                        'payment_type': payment_type,
                        'journal_id': payment.statement_id.journal_id.id,
                        'move_id': payment.move_id.id,
                        'payment_currency_id': payment.currency_id.id,
                        'payment_date': payment.date,
                        'payment_reference': payment.payment_ref,
                        'payment_amount': monto_pago,
                        'iva_amount': iva_amount,
                        'account_origin_id': account_origin_id,
                        # 'account_origin_id': payment.statement_id.journal_id.default_account_id.id,
                        'partner_id': payment.partner_id.id,
                        'invoice_id': invoice.id if invoice else False,
                        'invoice_currency_id': invoice.currency_id.id if invoice else False,
                        'invoice_date': invoice.invoice_date if invoice else False,
                        'invoice_amount': invoice.amount_total if invoice else 0.0,
                        'reference': invoice.ref if invoice else False,
                        'uuid': invoice.l10n_mx_edi_cfdi_uuid if invoice else False,
                        'user_id': user_id,
                        'statement_id': payment.statement_id.id,
                        'company_id': payment.move_id.company_id.id,
                    }
                data_id = data_obj.create(xvals)
                data_list_statements_ids.append(data_id.id)


            else:
                name = "Estado de Cuenta: %s" % payment.name
                xvals = {   
                            'name': name,
                            'payment_type': payment_type,
                            'journal_id': payment.statement_id.journal_id.id,
                            'move_id': payment.move_id.id,
                            'payment_currency_id': payment.currency_id.id,
                            'payment_date': payment.date,
                            'payment_reference': payment.payment_ref,
                            'payment_amount': payment.amount,
                            'iva_amount': iva_amount,
                            # 'account_origin_id': payment.statement_id.journal_id.default_account_id.id,
                            'account_origin_id': account_origin_id,
                            'partner_id': payment.partner_id.id,
                            'invoice_id': False,
                            'invoice_currency_id': False,
                            'invoice_date': False,
                            'invoice_amount': 0.0,
                            'reference': False,
                            'uuid': False,
                            'user_id': user_id,
                            'statement_id': payment.statement_id.id,
                            'company_id': payment.move_id.company_id.id,
                        }
                data_id = data_obj.create(xvals)
                data_list_statements_ids.append(data_id.id)
        
        return data_list_statements_ids

    def generate_report_waybill_xlsx(self):
        workbook = xlwt.Workbook(encoding='utf-8',style_compression=2)
        heading_format = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        heading_format_left = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold = xlwt.easyxf('font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf('font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        bold_right = xlwt.easyxf('font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz right;')
        bold_left = xlwt.easyxf('font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz left;')

        ### Cutom Color Background fot Comments ####
        xlwt.add_palette_colour("gray_custom", 0x21)
        workbook.set_colour_RGB(0x21, 238, 238, 238)

        tags_data_gray = xlwt.easyxf('font:bold True,height 200;pattern: pattern solid, fore_colour gray_custom;align: horiz center')
        
        tags_data_gray_right = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray_custom;align: horiz right;')
        tags_data_gray_center = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray_custom;align: horiz center;')
        tags_data_gray_left = xlwt.easyxf('font:height 200;pattern: pattern solid, fore_colour gray_custom;align: horiz left;')
            
        

        totals_bold_right = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz right;')
        totals_bold_center = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        totals_bold_left = xlwt.easyxf('font:height 200;pattern: pattern solid, fore_colour gray25;align: horiz left;')
        
        normal_center = xlwt.easyxf('align: horiz center;')
        normal_right = xlwt.easyxf('align: horiz right;')
        normal_left = xlwt.easyxf('align: horiz left;')

        normal_center_yellow = xlwt.easyxf('align: horiz center;pattern: pattern solid, fore_colour light_yellow;')
        normal_right_yellow = xlwt.easyxf('align: horiz right;pattern: pattern solid, fore_colour light_yellow;')
        normal_left_yellow = xlwt.easyxf('align: horiz left;pattern: pattern solid, fore_colour light_yellow;')

        #### Con Bordes #####
        # "borders: top double, bottom double, left double, right double;" # Como botones

        tags_data_gray_right_border = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray_custom;align: horiz right;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        tags_data_gray_center_border = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray_custom;align: horiz center;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        tags_data_gray_left_border = xlwt.easyxf('font:height 200;pattern: pattern solid, fore_colour gray_custom;align: horiz left;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        
        normal_center_yellow_border = xlwt.easyxf('align: horiz center;pattern: pattern solid, fore_colour light_yellow;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        normal_right_yellow_border = xlwt.easyxf('align: horiz right;pattern: pattern solid, fore_colour light_yellow;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        normal_left_yellow_border = xlwt.easyxf('align: horiz left;pattern: pattern solid, fore_colour light_yellow;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')

        normal_center_border = xlwt.easyxf('align: horiz center;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        normal_right_border = xlwt.easyxf('align: horiz right;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        normal_left_border = xlwt.easyxf('align: horiz left;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')

        heading_format_border = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')

        worksheet = workbook.add_sheet('Cartar Porte 2.0', bold_center)
        worksheet.write_merge(0, 0, 0, 3, 'DATOS CLIENTE', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        worksheet.write_merge(0, 0, 4, 6, 'DATOS DEL CFDI', heading_format)
        worksheet.col(0).width  = int(40 * 260)
        worksheet.col(1).width  = int(40 * 260)
        worksheet.col(2).width  = int(18 * 260)
        worksheet.col(3).width  = int(18 * 260)
        worksheet.col(4).width  = int(40 * 260)
        worksheet.col(5).width  = int(18 * 260)
        worksheet.col(6).width  = int(40 * 260)
        worksheet.col(7).width  = int(18 * 260)
        worksheet.col(8).width  = int(18 * 260)
        worksheet.col(9).width  = int(18 * 260)
        worksheet.col(10).width = int(18 * 260)
        worksheet.col(11).width = int(18 * 260)
        worksheet.col(12).width = int(18 * 260)
        worksheet.col(13).width = int(18 * 260)
        worksheet.col(14).width = int(18 * 260)
        worksheet.col(15).width = int(18 * 260)
        worksheet.col(16).width = int(18 * 260)
        worksheet.col(17).width = int(18 * 260)
        worksheet.col(18).width = int(18 * 260)
        worksheet.col(20).width = int(18 * 260)
        worksheet.col(21).width = int(18 * 260)
        worksheet.col(22).width = int(18 * 260)
        
        row = 1
        worksheet.write(row, 0, "Nombre", tags_data_gray_left_border)
        worksheet.write(row, 1, "NOMBREEE", normal_left) # Cambiar

        forma_pago_name = ""
        if self.l10n_mx_edi_payment_method_id:
            forma_pago_name = self.l10n_mx_edi_payment_method_id.code+" - " + self.l10n_mx_edi_payment_method_id.name

        worksheet.write(row, 4, "Forma de Pago (Clave SAT)", tags_data_gray_left_border)
        worksheet.write_merge(row, row, 5, 6, "Forma de Pago (Clave SAT)", normal_left_border) # Cambiar

        row += 1


        ### Figuras de Transporte ###
        row += 3
        worksheet.write_merge(row, row, 0, 6, 'Figuras de Transporte', heading_format_left)
        row += 2
        worksheet.write(row, 0, "Tipo de Figura", tags_data_gray_center_border)
        worksheet.write(row, 1, "Nombre", tags_data_gray_center_border)
        worksheet.write(row, 2, "RFC", tags_data_gray_center_border)
        worksheet.write(row, 3, "Estado (Código SAT)", tags_data_gray_center_border)
        worksheet.write(row, 4, "País (Código)", tags_data_gray_center_border)
        worksheet.write(row, 5, "CP", tags_data_gray_center_border)
        worksheet.write(row, 6, "Tipos Parte Transporte", tags_data_gray_center_border)

        date = str(self.date).replace('-','_')
        date_stop = str(self.date_stop).replace('-','_')
        
        dates_str = date+date_stop

        filename = ('Reporte de Operaciones Bancarias ['+str(dates_str) + '].xls') 
        fp = BytesIO()
        workbook.save(fp)
        
        self.write({
                        'xlsx_datas_fname': base64.encodestring(fp.getvalue()),
                        'xlsx_file': filename,
                    })
        
        fp.close()
        return self._reopen_wizard()


    def download_waybill_data_excel(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        file_url = base_url+"/web/content?model=account.move.bank.report.wizard=xlsx_file&filename_field=xlsx_datas_fname&id=%s&&download=true" % (self.id,)
        self.generate_report_waybill_xlsx()
        return {
                 'type': 'ir.actions.act_url',
                 'url': file_url,
                 'target': 'new'
                }

    def _reopen_wizard(self):
        return { 'type'     : 'ir.actions.act_window',
                 'res_id'   : self.id,
                 'view_mode': 'form',
                 'view_type': 'form',
                 'res_model': 'account.move.bank.report.wizard',
                 'target'   : 'new',
                 'name'     : 'Resultado del Reporte'}
    