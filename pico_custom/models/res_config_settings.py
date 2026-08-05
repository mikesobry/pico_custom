from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_preparation_days = fields.Integer(
        string="Default Sales Preparation Days",
        config_parameter='pico_custom_repo.sale_preparation_days',
        default=14,
    )
