from odoo import models, fields, api

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

    def button_validate(self):
        if not self.env.context.get('skip_pallet_check'):
            problems = self.filtered(
                lambda p: p.picking_type_code == 'outgoing'
                          and p.pallets_expected != p.pallets_loaded
            )
            if problems:
                lines = [
                    self.env._(
                        "%(name)s: %(exp)s pallets verwacht, %(got)s 'epal' op de picking.",
                        name=p.name, exp=p.pallets_expected, got=p.pallets_loaded,
                    )
                    for p in problems
                ]
                wizard = self.env['pico.pallet.check.wizard'].create({
                    'picking_ids': [(6, 0, problems.ids)],
                    'message': "\n".join(lines),
                })
                return {
                    'name': self.env._("Pallets controleren"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'pico.pallet.check.wizard',
                    'res_id': wizard.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
        return super().button_validate()