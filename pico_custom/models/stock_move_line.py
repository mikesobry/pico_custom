# pico_custom_repo/models/stock_move_line.py

from odoo import models, fields, api
import logging
import re
import copy

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    pallets_loaded = fields.Float(
        string="Pallets Loaded",
        help='Aantal effectief geladen pallets voor dit lotnummer.',
        digits=(16, 0),
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

    @api.onchange("pallets_loaded")
    def _onchange_pallets_loaded(self):
        for line in self:
            if line.product_id.pieces_per_pallet:
                line.quantity = (
                        line.pallets_loaded *
                        line.product_id.pieces_per_pallet
                )

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

    """ Berekent het totale gewicht van de stock move line zelf"""
    @api.depends('quantity', 'product_id.weight')
    def _compute_line_weight(self):
        for line in self:
            line.line_weight = line.quantity * line.product_id.weight

    """
    def _get_aggregated_product_quantities(self, **kwargs):
        strict = kwargs.get('strict', False)
        except_package = kwargs.get('except_package', False)

        # Start met originele aggregated data
        res = super()._get_aggregated_product_quantities(**kwargs)

        if strict and not self.filtered(lambda l: l.result_package_id):
            _logger.warning("🔥 STRICT TRUE BUT NO PACKAGE LINES, returning empty dict")
            return {}

        res_split = {}

        for line_key, data in res.items():
            # Haal move lines uit data of fallback naar picking moves
            move_lines = data.get('move_line_ids')
            moves = move_lines.mapped('move_id') if move_lines else self.picking_id.move_ids.filtered(
                lambda m: m.product_id == (data.get('product_id') or data.get('product'))
            )

            product = data.get('product_id') or data.get('product') or (moves[:1].product_id if moves else None)

            # Loop per move, niet op geaggregeerde quantity
            for i, move in enumerate(moves, start=1):
                line_key_split = f"{line_key}_{i}"
                new_data = copy.deepcopy(data)

                # --- Quantity, pallets, lot en weight correct per move ---
                delivered_qty = move.quantity  # v19: quantity is de geleverde hoeveelheid
                pallets = move.loaded_pallets or 0
                lot = move.pico_batch_code or ''

                new_data.update({
                    'quantity': delivered_qty,
                    'pallet_qty': int(pallets),
                    'pico_lot': lot,
                    'weight': delivered_qty * (product.weight or 0.0) if product else 0.0,
                })

                res_split[line_key_split] = new_data

                _logger.info(
                    "SPLIT LINE '%s': product=%s, qty=%s, pallets=%s, pico_lot=%s",
                    line_key_split,
                    product.display_name if product else None,
                    delivered_qty,
                    pallets,
                    lot
                )

        return res_split
        """

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