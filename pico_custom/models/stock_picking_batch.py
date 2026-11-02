from odoo import models, fields, api


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    partner_id = fields.Many2one(
        'res.partner',
        compute='_compute_pico_totals',
        string="Klant",
    )
    pallets_loaded = fields.Integer(compute='_compute_pico_totals')
    pallets_expected = fields.Integer(compute='_compute_pico_totals')
    pallets_received = fields.Integer(compute='_compute_pico_totals')
    pallet_balance = fields.Integer(compute='_compute_pico_totals')
    total_net_weight = fields.Float(compute='_compute_pico_totals')
    total_gross_weight = fields.Float(compute='_compute_pico_totals')

    @api.depends(
        'picking_ids.partner_id',
        'picking_ids.pallets_loaded',
        'picking_ids.pallets_expected',
        'picking_ids.pallets_received',
        'picking_ids.total_net_weight',
        'picking_ids.total_gross_weight',
    )
    def _compute_pico_totals(self):
        for b in self:
            p = b.picking_ids
            b.partner_id = p[:1].partner_id
            b.pallets_loaded = sum(p.mapped('pallets_loaded'))
            b.pallets_expected = sum(p.mapped('pallets_expected'))
            b.pallets_received = sum(p.mapped('pallets_received'))
            b.pallet_balance = b.pallets_loaded - b.pallets_received
            b.total_net_weight = sum(p.mapped('total_net_weight'))
            b.total_gross_weight = sum(p.mapped('total_gross_weight'))

    def action_add_pallets(self):
        self.picking_ids.action_add_pallets()
        return True