from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_weight = fields.Float(string='Totaal netto Gewicht (kg)', compute='_compute_total_weight')

    """
    def onchange(self, values, field_name, field_onchange):
        _logger.warning(f" Custom onchange called: field_name={field_name}")
        _logger.warning(f"Values: {values}")
        return super().onchange(values, field_name, field_onchange)
    """

    @api.depends('order_line.line_weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(order.order_line.mapped('line_weight'))