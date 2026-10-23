from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pallets_loaded = fields.Integer(
        string="Pallets uit",
        compute="_compute_weights",
        store=False
    )
    pallets_received = fields.Integer(
        string="Pallets retour"
    )

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

    """ compute totals based on move_ids. line information """
    @api.depends(
        "move_ids.move_line_ids.pallets_loaded",
        "move_ids.move_line_ids.line_weight",
        "pallets_received",
    )
    def _compute_weights(self):
        for picking in self:
            picking.pallets_loaded = sum(picking.move_ids.move_line_ids.mapped('pallets_loaded'))
            picking.pallet_balance = picking.pallets_loaded - picking.pallets_received

            picking.total_net_weight = sum(picking.move_ids.move_line_ids.mapped('line_weight'))
            picking.total_gross_weight = picking.total_net_weight + (picking.pallets_loaded * 30.0)