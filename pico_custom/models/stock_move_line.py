# pico_custom_repo/models/stock_move_line.py

from odoo import models, fields, api
import logging
import re
import math
import copy

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    pallets_loaded = fields.Float(
        string="Pallets Loaded",
        compute="_compute_pallets_loaded",
        store=True,
        readonly=False,
        digits=(16, 0),
        help='Aantal effectief geladen pallets voor dit lotnummer.'
    )

    pico_batch_code = fields.Char(
        string="Lot",
        help="Interne productiebatch (bv. PK035)"
    )

    # berekend veld voor het totale gewicht van de stock move
    line_weight = fields.Float(
        string="Weight (kg)",
        compute='_compute_line_weight',
        help="totale gewicht van de line zelf",
        store=True
    )

    """
    @api.onchange("pallets_loaded")
    def _onchange_pallets_loaded(self):
        for line in self:
            if line.product_id.pieces_per_pallet:
                line.quantity = (
                        line.pallets_loaded *
                        line.product_id.pieces_per_pallet
                )
    """

    @api.onchange("pallets_loaded", "product_uom_id")
    def _onchange_pallets_loaded(self):
        for line in self:
            ppp = line.product_id.pieces_per_pallet
            if not ppp:
                continue
            qty_base = line.pallets_loaded * ppp
            if line.product_uom_id and line.product_uom_id != line.product_id.uom_id:
                line.quantity = line.product_id.uom_id._compute_quantity(
                    qty_base, line.product_uom_id, round=False
                )
            else:
                line.quantity = qty_base

    @api.depends('quantity', 'product_uom_id', 'product_id.pieces_per_pallet')
    def _compute_pallets_loaded(self):
        for line in self:
            ppp = line.product_id.pieces_per_pallet
            if not ppp or not line.product_uom_id:
                line.pallets_loaded = line.pallets_loaded
                continue
            qty_base = line.product_uom_id._compute_quantity(
                line.quantity, line.product_id.uom_id, round=False
            )
            line.pallets_loaded = math.ceil(round(qty_base / ppp, 6)) if qty_base else 0

    """ Regex op lotnummer toepassen pl1 en pl01 naar pl 001 te krijgen"""
    @api.onchange('pico_batch_code')
    def _onchange_pico_batch_code(self):
        """Normalize batch code: two letters + zero-padded number (3 digits)"""
        for line in self:
            if not line.pico_batch_code:
                continue

            val = line.pico_batch_code.strip().upper()
            m = re.match(r'^([A-Z]{2})0*(\d+)$', val)
            if m:
                prefix, number = m.groups()
                line.pico_batch_code = f"{prefix}{int(number):03d}"
                _logger.info("Normalized pico_batch_code: %s", line.pico_batch_code)
            else:
                _logger.warning("Invalid pico_batch_code format: %s", line.pico_batch_code)

    """ Berekent het totale gewicht van de stock move line zelf
    @api.depends('quantity', 'product_id.weight')
    def _compute_line_weight(self):
        for line in self:
            line.line_weight = line.quantity * line.product_id.weight
    """

    @api.depends('quantity', 'product_uom_id', 'product_id.weight')
    def _compute_line_weight(self):
        for line in self:
            qty_base = line.product_uom_id._compute_quantity(
                line.quantity, line.product_id.uom_id
            ) if line.product_uom_id and line.product_id else line.quantity
            line.line_weight = qty_base * (line.product_id.weight or 0.0)

    def _get_aggregated_product_quantities(self, **kwargs):

        _logger.warning("******* PICO TEST: _get_aggregated_product_quantities CALLED *******")

        result = {}

        for line in self:
            key = f"{line.move_id.id}_{line.id}"

            result[key] = {
                'name': line.product_id.display_name,

                'description': (
                    line.description_picking
                    if line.description_picking
                       and line.description_picking not in (
                           line.product_id.display_name,
                           line.product_id.name,
                       )
                    else ''
                ),

                'product_uom': line.product_uom_id,

                'quantity': line.quantity,

                'pallets_loaded': int(line.pallets_loaded or 0),

                'pico_lot': line.pico_batch_code or '',

                # tijdelijk hardcoded
                'weight': line.line_weight or 0.0,

                # velden die Odoo verwacht
                'qty_ordered': line.move_id.product_uom_qty,

                'packaging_qty_ordered': 0,
                'packaging_quantity': 0,

                'packaging_uom_id': line.product_uom_id,

                'move_lines': line,
            }

            _logger.info(
                "PICO AGGREGATE: picking=%s, lines=%s, result_keys=%s",
                self.mapped('picking_id').ids,
                self.ids,
                list(result.keys()),
            )

        return result

    def write(self, vals):
        _logger.warning("WRITE MOVE LINE %s", vals)
        return super().write(vals)

    def create(self, vals):
        _logger.warning("MOVE LINE CREATE %s", vals)
        return super().create(vals)