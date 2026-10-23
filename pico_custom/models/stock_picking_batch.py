from odoo import models, fields, api

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    pallets_loaded = fields.Float(compute='_compute_pico_totals', digits=(16, 0))
    pallets_received = fields.Integer(compute='_compute_pico_totals')
    pallet_balance = fields.Integer(compute='_compute_pico_totals')
    total_net_weight = fields.Float(compute='_compute_pico_totals')
    total_gross_weight = fields.Float(compute='_compute_pico_totals')

    @api.depends('picking_ids.pallets_loaded', 'picking_ids.pallets_received',
                 'picking_ids.total_net_weight', 'picking_ids.total_gross_weight')
    def _compute_pico_totals(self):
        for b in self:
            p = b.picking_ids
            b.pallets_loaded = sum(p.mapped('pallets_loaded'))
            b.pallets_received = sum(p.mapped('pallets_received'))
            b.pallet_balance = b.pallets_loaded - b.pallets_received
            b.total_net_weight = sum(p.mapped('total_net_weight'))
            b.total_gross_weight = sum(p.mapped('total_gross_weight'))