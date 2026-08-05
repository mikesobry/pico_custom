from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pieces_per_pallet = fields.Integer(string='Aantal stuks per pallet')

