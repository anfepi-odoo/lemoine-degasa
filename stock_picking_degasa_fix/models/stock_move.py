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

from collections import defaultdict
from datetime import timedelta
from itertools import groupby
from odoo.tools import groupby as groupbyelem
from operator import itemgetter

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet

import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"



    def _action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        # Use OrderedSet of id (instead of recordset + |= ) for performance
        move_create_proc, move_to_confirm, move_waiting = OrderedSet(), OrderedSet(), OrderedSet()
        to_assign = defaultdict(OrderedSet)
        for move in self:
            if move.state != 'draft':
                continue
            # if the move is preceded, then it's waiting (if preceding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                move_waiting.add(move.id)
            else:
                if move.procure_method == 'make_to_order':
                    move_create_proc.add(move.id)
                else:
                    move_to_confirm.add(move.id)
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                to_assign[key].add(move.id)

        move_create_proc, move_to_confirm, move_waiting = self.browse(move_create_proc), self.browse(move_to_confirm), self.browse(move_waiting)

        # create procurements for make to order moves
        procurement_requests = []
        for move in move_create_proc:
            values = move._prepare_procurement_values()
            origin = move._prepare_procurement_origin()
            procurement_requests.append(self.env['procurement.group'].Procurement(
                move.product_id, move.product_uom_qty, move.product_uom,
                move.location_id, move.rule_id and move.rule_id.name or "/",
                origin, move.company_id, values))
        self.env['procurement.group'].run(procurement_requests, raise_user_error=not self.env.context.get('from_orderpoint'))

        move_to_confirm.write({'state': 'confirmed'})
        (move_waiting | move_create_proc).write({'state': 'waiting'})
        # procure_method sometimes changes with certain workflows so just in case, apply to all moves
        (move_to_confirm | move_waiting | move_create_proc).filtered(lambda m: m.picking_type_id.reservation_method == 'at_confirm')\
            .write({'reservation_date': fields.Date.today()})

        # assign picking in batch for all confirmed move that share the same details
        for moves_ids in to_assign.values():
            self.browse(moves_ids).with_context(clean_context(self.env.context))._assign_picking()
        new_push_moves = self.filtered(lambda m: not m.picking_id.immediate_transfer)._push_apply()
        self._check_company()
        moves = self
        if merge:
            moves = self._merge_moves(merge_into=merge_into)

        # Transform remaining move in return in case of negative initial demand
        neg_r_moves = moves.filtered(lambda move: float_compare(
            move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) < 0)
        for move in neg_r_moves:
            move.location_id, move.location_dest_id = move.location_dest_id, move.location_id
            orig_move_ids, dest_move_ids = [], []
            for m in move.move_orig_ids | move.move_dest_ids:
                from_loc, to_loc = m.location_id, m.location_dest_id
                if float_compare(m.product_uom_qty, 0, precision_rounding=m.product_uom.rounding) < 0:
                    from_loc, to_loc = to_loc, from_loc
                if to_loc == move.location_id:
                    orig_move_ids += m.ids
                elif move.location_dest_id == from_loc:
                    dest_move_ids += m.ids
            move.move_orig_ids, move.move_dest_ids = [(6, 0, orig_move_ids)], [(6, 0, dest_move_ids)]
            move.product_uom_qty *= -1
            if move.picking_type_id.return_picking_type_id:
                move.picking_type_id = move.picking_type_id.return_picking_type_id
            # We are returning some products, we must take them in the source location
            move.procure_method = 'make_to_stock'
        neg_r_moves._assign_picking()

        # call `_action_assign` on every confirmed move which location_id bypasses the reservation + those expected to be auto-assigned
        moves.filtered(lambda move: not move.picking_id.immediate_transfer
                       and move.state in ('confirmed', 'partially_available')
                       and (move._should_bypass_reservation()
                            or move.picking_type_id.reservation_method == 'at_confirm'
                            or (move.reservation_date and move.reservation_date <= fields.Date.today())))\
             ._action_assign()
        # if new_push_moves:
        #     neg_push_moves = new_push_moves.filtered(lambda sm: float_compare(sm.product_uom_qty, 0, precision_rounding=sm.product_uom.rounding) < 0)
        #     _logger.info("\n****************** neg_push_moves: %s " % neg_push_moves)
        #     _logger.info("\n****************** new_push_moves: %s " % new_push_moves)

        #     for rec in new_push_moves - neg_push_moves:
        #         _logger.info("\n****************** rec: %s " % rec)
        #         _logger.info("\n****************** rec.product_id: %s " % rec.product_id)
        #         _logger.info("\n****************** rec.product_id.name: %s " % rec.product_id.name)
        #     result_moves = (new_push_moves - neg_push_moves)
        #     _logger.info("\n****************** result_moves: %s " % result_moves)
        #     (new_push_moves - neg_push_moves)._action_confirm()
        #     # Negative moves do not have any picking, so we should try to merge it with their siblings
        #     _logger.info("\n****************** neg_push_moves: %s " % neg_push_moves)

        #     neg_push_moves._action_confirm(merge_into=neg_push_moves.move_orig_ids.move_dest_ids)

        return moves
        
    # def _action_confirm(self, merge=True, merge_into=False):
    #     """ Confirms stock move or put it in waiting if it's linked to another move.
    #     :param: merge: According to this boolean, a newly confirmed move will be merged
    #     in another move of the same picking sharing its characteristics.
    #     """
    #     # Use OrderedSet of id (instead of recordset + |= ) for performance
    #     move_create_proc, move_to_confirm, move_waiting = OrderedSet(), OrderedSet(), OrderedSet()
    #     to_assign = defaultdict(OrderedSet)
    #     move_ids_origin = []
    #     for move in self:
    #         move_ids_origin.append(move.id)
    #         if move.state != 'draft':
    #             continue
    #         # if the move is preceded, then it's waiting (if preceding move is done, then action_assign has been called already and its state is already available)
    #         if move.move_orig_ids:
    #             move_waiting.add(move.id)
    #         else:
    #             if move.procure_method == 'make_to_order':
    #                 move_create_proc.add(move.id)
    #             else:
    #                 move_to_confirm.add(move.id)
    #         if move._should_be_assigned():
    #             key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
    #             to_assign[key].add(move.id)
    #     print ("########### move_create_proc")
    #     move_create_proc, move_to_confirm, move_waiting = self.browse(move_create_proc), self.browse(move_to_confirm), self.browse(move_waiting)
    #     print ("########### move_create_proc: ", move_create_proc)
    #     print ("########### move_to_confirm: ", move_to_confirm)
    #     print ("########### move_waiting: ", move_waiting)

    #     # create procurements for make to order moves
    #     procurement_requests = []
    #     for move in move_create_proc:
    #         values = move._prepare_procurement_values()
    #         origin = move._prepare_procurement_origin()
    #         procurement_requests.append(self.env['procurement.group'].Procurement(
    #             move.product_id, move.product_uom_qty, move.product_uom,
    #             move.location_id, move.rule_id and move.rule_id.name or "/",
    #             origin, move.company_id, values))
    #     self.env['procurement.group'].run(procurement_requests, raise_user_error=not self.env.context.get('from_orderpoint'))

    #     move_to_confirm.write({'state': 'confirmed'})
    #     (move_waiting | move_create_proc).write({'state': 'waiting'})
    #     # procure_method sometimes changes with certain workflows so just in case, apply to all moves
    #     (move_to_confirm | move_waiting | move_create_proc).filtered(lambda m: m.picking_type_id.reservation_method == 'at_confirm')\
    #         .write({'reservation_date': fields.Date.today()})

    #     # assign picking in batch for all confirmed move that share the same details
    #     for moves_ids in to_assign.values():
    #         self.browse(moves_ids).with_context(clean_context(self.env.context))._assign_picking()
    #     new_push_moves = self.filtered(lambda m: not m.picking_id.immediate_transfer)._push_apply()
    #     self._check_company()
    #     moves = self
    #     if merge:
    #         moves = self._merge_moves(merge_into=merge_into)

    #     # Transform remaining move in return in case of negative initial demand
    #     neg_r_moves = moves.filtered(lambda move: float_compare(
    #         move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) < 0)
    #     for move in neg_r_moves:
    #         move.location_id, move.location_dest_id = move.location_dest_id, move.location_id
    #         orig_move_ids, dest_move_ids = [], []
    #         for m in move.move_orig_ids | move.move_dest_ids:
    #             from_loc, to_loc = m.location_id, m.location_dest_id
    #             if float_compare(m.product_uom_qty, 0, precision_rounding=m.product_uom.rounding) < 0:
    #                 from_loc, to_loc = to_loc, from_loc
    #             if to_loc == move.location_id:
    #                 orig_move_ids += m.ids
    #             elif move.location_dest_id == from_loc:
    #                 dest_move_ids += m.ids
    #         move.move_orig_ids, move.move_dest_ids = [(6, 0, orig_move_ids)], [(6, 0, dest_move_ids)]
    #         move.product_uom_qty *= -1
    #         if move.picking_type_id.return_picking_type_id:
    #             move.picking_type_id = move.picking_type_id.return_picking_type_id
    #         # We are returning some products, we must take them in the source location
    #         move.procure_method = 'make_to_stock'
    #     neg_r_moves._assign_picking()

    #     # call `_action_assign` on every confirmed move which location_id bypasses the reservation + those expected to be auto-assigned
    #     moves_filtered = moves.filtered(lambda move: not move.picking_id.immediate_transfer
    #                    and move.state in ('confirmed', 'partially_available')
    #                    and (move._should_bypass_reservation()
    #                         or move.picking_type_id.reservation_method == 'at_confirm'
    #                         or (move.reservation_date and move.reservation_date <= fields.Date.today())))
    #     for mvfilter in moves_filtered:
    #         if mvfilter.id not in move_ids_origin:
    #             mvfilter._action_assign()
    #     #moves_filtered._action_assign()
    #     # if new_push_moves:
    #     #     new_push_moves._action_confirm()
    #     return moves