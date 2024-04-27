import pdb
purchase_obj = self.env['purchase.order']
purchase_br = purchase_obj.browse(4045)
purchase_br.write({'state':'purchase'})


#pdb.runcall(purchase_br._create_picking)

StockPicking = env['stock.picking']
picking_vals = purchase_br._prepare_picking()
picking = StockPicking.sudo().create(picking_vals)

# pdb.runcall(purchase_br._create_picking)
# purchase_br.order_line._create_stock_moves
pdb.runcall(purchase_br.order_line._create_stock_moves, picking)
