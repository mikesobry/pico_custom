# pico_custom/models/stock_move.py

from odoo import models, fields, api
import re
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    requested_pallets = fields.Integer(
        string='Pal',
        compute='_compute_requested_pallets',
        store=False
    )

    # nieuw invoerveld
    loaded_pallets = fields.Float(
        string='Pal geladen',
        help='Aantal effectief geladen pallets voor deze stock move.',
        digits=(16, 0),
    )

    pico_batch_code = fields.Char(
        string="Lot",
        help="Interne productiebatch (bv. PK035)"
    )

    line_weight = fields.Float(
        string="Weight (kg)",
        compute='_compute_line_weight',
        help="totale gewicht van lijn",
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
    """
    def get_first_batch(self):
        _logger.warning("get_first_batch called on %s", self)
        return self.pico_batch_code or ''
    """

    @api.depends('product_uom_qty', 'product_id.weight')
    def _compute_line_weight(self):
        for move in self:
            qty = move.quantity or 0.0
            weight = move.product_id.weight or 0.0
            move.line_weight = qty * weight

    @api.onchange('quantity', 'product_id')
    def _onchange_line_weight(self):
        for move in self:
            move.line_weight = (move.quantity or 0.0) * (move.product_id.weight or 0.0)

    def _prepare_merge_moves_distinct_fields(self):
        _logger.warning("prepare_merge_moves_distinct_fields CALLED !!!!!")
        fields = super()._prepare_merge_moves_distinct_fields()

        if any(m.picking_id.picking_type_id.code == 'outgoing' for m in self):
            fields.append('pico_batch_code')

        return fields

    @api.onchange('pico_batch_code')
    def _onchange_pico_batch_code(self):
        """Normalize batch code: two letters + zero-padded number (3 digits)"""
        for move in self:
            if not move.pico_batch_code:
                continue

            val = move.pico_batch_code.strip().upper()
            m = re.match(r'^([A-Z]{2})0*(\d+)$', val)
            if m:
                prefix, number = m.groups()
                move.pico_batch_code = f"{prefix}{int(number):03d}"
                _logger.info("Normalized pico_batch_code: %s", move.pico_batch_code)
            else:
                _logger.warning("Invalid pico_batch_code format: %s", move.pico_batch_code)