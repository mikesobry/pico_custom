from odoo import models, fields, api
from odoo.exceptions import UserError
from .stock_picking import PALLET_CODE

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

    def action_print_pico(self):
        self.ensure_one()
        return self.env.ref(
            'pico_custom.report_wave_deliveryslip_action'
        ).report_action(self)

    def action_add_pallets(self):
        for b in self:
            missing = b.pallets_expected - b.pallets_loaded
            if missing > 0:
                b._pallet_target_picking()._add_pallet_move(missing)
        return True

    def _pallet_target_picking(self):
        """Picking van de wave die de pallets draagt: de eerste die al een epal-move heeft, anders de eerste."""
        self.ensure_one()
        moves = self.picking_ids.move_ids.filtered(
            lambda m: m.product_id.default_code == PALLET_CODE)
        return moves[:1].picking_id or self.picking_ids.sorted('id')[:1]

    def action_return_pallets(self):
        self.ensure_one()
        picking = self.picking_ids.filtered(
            lambda p: p.state == 'done' and any(
                m.product_id.default_code == PALLET_CODE for m in p.move_ids))[:1]
        if not picking:
            raise UserError(self.env._("Geen gevalideerde picking met epal in deze wave."))
        wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id, active_model='stock.picking'
        ).create({'picking_id': picking.id})
        wizard.product_return_moves.filtered(
            lambda l: l.product_id.default_code != PALLET_CODE).unlink()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Pallets retour"),
            'res_model': 'stock.return.picking',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }