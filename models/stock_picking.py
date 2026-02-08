from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _logger.warning("### STOCK PICKING FILE LOADED ###")

    '''pallets_loaded = fields.Float(string="Pallets uit")'''
    pallets_loaded = fields.Float(
        string="Pallets uit",
        compute="_compute_weights",
        store=False,
    )
    pallets_received = fields.Integer(string="Pallets retour")

    pallet_balance = fields.Integer(
        string="Pallet saldo",
        compute="_compute_weights",
        store=False
    )

    total_net_weight = fields.Float(
        string="Netto gewicht (kg)",
        compute="_compute_weights",
        store=False
    )

    total_gross_weight = fields.Float(
        string="Bruto gewicht (kg)",
        compute="_compute_weights",
        store=False
    )
    '''
    @api.depends(
        "move_ids.quantity",
        "move_ids.product_id.weight",
        "move_ids.loaded_pallets",
        "move_ids.line_weight",
        "pallets_loaded",
        "pallets_received",
    )
    '''

    @api.depends(
        "move_ids.loaded_pallets",
        "move_ids.line_weight",
        "pallets_received",
    )

    def _compute_weights(self):
        for picking in self:
            pallets_list = picking.move_ids.mapped('loaded_pallets')

            _logger.warning(
                "PICKING %s | moves=%s | loaded_pallets=%s",
                picking.name,
                picking.move_ids.ids,
                pallets_list,
            )

            net = sum(picking.move_ids.mapped('line_weight'))
            '''pallets = sum(picking.move_ids.mapped('loaded_pallets'))'''
            pallets = sum(pallets_list)

            _logger.warning(
                "PICKING %s | total pallets = %s",
                picking.name,
                pallets,
            )

            picking.pallets_loaded = pallets
            picking.total_net_weight = net
            picking.total_gross_weight = net + (pallets * 30.0)
            picking.pallet_balance = picking.pallets_loaded - picking.pallets_received

    """
    def get_delivery_table_lines(self):
        Geeft een lijst van dicts terug, één per move, met de info voor de leveringsbon.
        _logger.warning("CALLED: get_delivery_table_lines")

        lines = []
        for move in self.move_ids.filtered(lambda m: m.state != 'cancel'):
            ppp = move.product_id.pieces_per_pallet or 0
            pallets = move.product_uom_qty / ppp if ppp else 0
            weight = move.product_id.weight * move.product_uom_qty if move.product_id.weight else 0
            lines.append({
                'product': move.product_id.display_name,
                'lot': move.pico_batch_code or '',
                'delivered': move.quantity_done,
                'pallets': pallets,
                'weight': weight,
            })
        return lines
    """