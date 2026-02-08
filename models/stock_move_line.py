# pico_custom/models/stock_move_line.py

from odoo import models
import logging
import copy

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

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
