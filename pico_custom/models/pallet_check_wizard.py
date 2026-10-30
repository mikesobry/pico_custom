from odoo import models, fields


class PalletCheckWizard(models.TransientModel):
    _name = 'pico.pallet.check.wizard'
    _description = 'Palletcontrole bij validatie'

    picking_ids = fields.Many2many('stock.picking')
    message = fields.Text(readonly=True)

    def action_confirm(self):
        self.ensure_one()
        return self.picking_ids.with_context(
            skip_pallet_check=True
        ).button_validate()