from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    requested_pallets = fields.Integer(string='Pal', compute='_compute_requested_pallets', store=False)

    # nieuw invoerveld
    loaded_pallets = fields.Float(
        string='Pal geladen',
        help='Aantal effectief geladen pallets voor deze stock move.'
    )

    @api.depends('product_uom_qty', 'product_id.pieces_per_pallet')
    def _compute_requested_pallets(self):
        for move in self:
            ppp = move.product_id.pieces_per_pallet or 0.0
            if ppp:
                move.requested_pallets = float(move.product_uom_qty) / float(ppp)
            else:
                move.requested_pallets = 0.0

    @api.onchange('loaded_pallets')
    def _onchange_loaded_pallets(self):
        """Wanneer het aantal geladen pallets wordt ingevoerd, bereken het aantal stuks."""
        for move in self:
            if move.loaded_pallets and move.product_id.pieces_per_pallet:
                move.quantity = (
                        move.loaded_pallets * move.product_id.pieces_per_pallet
                )
                _logger.warning(
                    "Loaded pallets gewijzigd: %s pallets x %s stuks = %s stuks totaal",
                    move.loaded_pallets,
                    move.product_id.pieces_per_pallet,
                    move.product_uom_qty,
                )