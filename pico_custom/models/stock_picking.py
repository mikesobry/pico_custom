from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

PALLET_CODE = 'epal'   # interne referentie van het palletproduct


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pallets_loaded = fields.Integer(
        string="Pallets uit",
        compute="_compute_weights",
        store=False,
    )
    pallets_expected = fields.Integer(
        string="Pallets verwacht",
        compute="_compute_weights",
        store=False,
    )
    pallets_received = fields.Integer(
        string="Pallets retour",
        compute="_compute_weights",
        store=False,
    )
    pallet_balance = fields.Integer(
        string="Pallet saldo",
        compute="_compute_weights",
        store=False,
    )
    total_net_weight = fields.Float(
        string="Netto gewicht (kg)",
        compute="_compute_weights",
        store=False,
    )
    total_gross_weight = fields.Float(
        string="Bruto gewicht (kg)",
        compute="_compute_weights",
        store=False,
    )

    @api.depends(
        "move_ids.move_line_ids.pallets_loaded",
        "move_ids.move_line_ids.quantity",
        "move_ids.move_line_ids.line_weight",
        "move_ids.move_line_ids.product_id",
        "return_ids.state",
        "return_ids.move_line_ids.quantity",
    )
    def _compute_weights(self):
        for picking in self:
            lines = picking.move_ids.move_line_ids
            pallet_lines = lines.filtered(
                lambda l: l.product_id.default_code == PALLET_CODE
            )
            goods_lines = lines - pallet_lines

            # Verwacht: wat de goederenlijnen aan pallets vragen
            picking.pallets_expected = int(sum(goods_lines.mapped('pallets_loaded')))

            # Uit: effectief de hoeveelheid op de epal-lijn(en)
            picking.pallets_loaded = int(sum(pallet_lines.mapped('quantity')))

            returned = picking.return_ids.filtered(
                lambda r: r.state == 'done'
            ).move_line_ids.filtered(
                lambda l: l.product_id.default_code == PALLET_CODE
            )
            picking.pallets_received = int(sum(returned.mapped('quantity')))
            picking.pallet_balance = picking.pallets_loaded - picking.pallets_received

            picking.total_gross_weight = sum(lines.mapped('line_weight'))
            picking.total_net_weight = sum(goods_lines.mapped('line_weight'))