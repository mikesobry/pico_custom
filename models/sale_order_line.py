from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pallet_qty = fields.Float(
        string='Aantal bestelde pallets',
        digits=(16, 0),
    )
    line_weight = fields.Float(string='Gewicht (kg)', compute='_compute_line_weight')

    @api.onchange('pallet_qty')
    def _onchange_pallet_qty(self):
        _logger.warning(">>> Onchange fired for %s", self.pallet_qty)
        _logger.warning(">>> Onchange pallet_qty triggered <<<")
        if self.product_id and self.product_id.pieces_per_pallet:
            self.product_uom_qty = self.pallet_qty * self.product_id.pieces_per_pallet

    @api.depends('product_id', 'product_uom_qty')
    def _compute_line_weight(self):
        for line in self:
            line.line_weight = (line.product_id.weight or 0.0) * line.product_uom_qty

