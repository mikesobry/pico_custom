from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_weight = fields.Float(
        string='Totaal netto Gewicht (kg)',
        compute='_compute_total_weight'
    )

    total_gross_weight = fields.Float(
        string='Totaal bruto gewicht (kg)',
        compute='_compute_total_gross_weight'
    )

    total_pallets = fields.Float(
        string='Totaal aantal pallets besteld',
        compute='_compute_total_pallets'
    )

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

    @api.depends('total_weight', 'total_pallets')
    def _compute_total_gross_weight(self):
        for order in self:
            order.total_gross_weight = order.total_weight + (order.total_pallets * 30.0)

    @api.depends('order_line.pallet_qty')
    def _compute_total_pallets(self):
        for order in self:
            order.total_pallets = sum(order.order_line.mapped('pallet_qty'))

    # zet de picking date 14 dagen later dan de confirm sale order date.
    def _action_confirm(self):
        # Eerst standaard gedrag laten lopen
        res = super()._action_confirm()

        # Lees configuratie
        param = self.env['ir.config_parameter'].sudo().get_param(
            'pico_custom.sale_preparation_days',
            default=14
        )
        prep_days = int(param)

        for order in self:
            # Enkel indien GEEN leverdatum ingevuld
            if not order.commitment_date:

                new_date = order.date_order + timedelta(days=prep_days)

                # Pickings aanpassen
                for picking in order.picking_ids:
                    picking.write({
                        'scheduled_date': new_date,
                        'date_deadline': new_date,
                    })

                    # Moves syncen (extra veiligheid)
                    picking.move_ids.write({
                        'date': new_date,
                        'date_deadline': new_date,
                    })

        return res