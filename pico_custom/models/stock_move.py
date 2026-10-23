# pico_custom_repo/models/stock_move.py

from odoo import models, fields, api
import re
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    # info veld voor het aantal bestelde pallets per move
    requested_pallets = fields.Integer(
        string='Pal',
        compute='_compute_requested_pallets',
        store=False
    )

    # invoerveld voor het aantal geladen pallets
    loaded_pallets = fields.Float(
        string='Pal geladen',
        compute="_compute_loaded_pallets",
        help='Aantal effectief geladen pallets voor deze stock move.',
        digits=(16, 0)
    )

    # invoerveld voor het lotnummer van de aantal geladen pallets
    pico_batch_code = fields.Char(
        string="Lot",
        compute="_compute_pico_batch_code",
        help="Pico-lotcode uit de move lines; 'multi' bij meerdere verschillende codes."
    )

    # berekend veld voor het totale gewicht van de stock move
    line_weight = fields.Float(
        string="Weight (kg)",
        compute='_compute_line_weight',
        help="totale gewicht van move",
        store=True
    )

    """ TODO: waarom error indien verwijderd? Waar wordt dit gebruikt? Of gewoon DB model error?"""
    move_line_count = fields.Integer(
        compute="_compute_move_line_count",
        store = False
    )

    @api.depends('move_line_ids.pico_batch_code')
    def _compute_pico_batch_code(self):
        for move in self:
            codes = sorted({c for c in move.move_line_ids.mapped('pico_batch_code') if c})
            if not codes:
                move.pico_batch_code = False
            elif len(codes) == 1:
                move.pico_batch_code = codes[0]
            else:
                move.pico_batch_code = "multi"

    def _compute_move_line_count(self):
        for move in self:
            move.move_line_count = len(move.move_line_ids)

    """ Berekent het aantal gewenste pallets op basis van het aantal bestelde stuks"""
    @api.depends('product_uom_qty', 'product_id.pieces_per_pallet')
    def _compute_requested_pallets(self):
        for move in self:
            ppp = move.product_id.pieces_per_pallet or 0.0
            if ppp:
                move.requested_pallets = float(move.product_uom_qty) / float(ppp)
            else:
                move.requested_pallets = 0.0

    """ haalt het aantal geladen pallets op uit de stock move line"""
    @api.depends('move_line_ids.pallets_loaded')
    def _compute_loaded_pallets(self):
        for move in self:
            move.loaded_pallets = sum(move.move_line_ids.mapped('pallets_loaded'))

    """ shortcut kolom: 
        schrijft het aantal geladen pallets op naar de stock move line 
        Mag enkel wanneer er geen enkele of maar één stock move line bestaat
    """
    """
    def _inverse_loaded_pallets(self):
        _logger.warning("INVERSE LOAD MOVE LINE EXECUTION ")

        for move in self:

            ppp = move.product_id.pieces_per_pallet or 1
            qty = move.loaded_pallets * ppp

            # ---------------------------
            # GEEN lines → CREATE
            # ---------------------------
            if not move.move_line_ids:
                _logger.warning("INVERSE LOAD MOVE LINE CREATION!! ")
                self.env['stock.move.line'].create({
                    "move_id": move.id,
                    "picking_id": move.picking_id.id,
                    "company_id": move.company_id.id,
                    "product_id": move.product_id.id,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "quantity": qty,
                    "pallets_loaded": move.loaded_pallets
                })

            # ---------------------------
            # EXACT 1 line → UPDATE
            # ---------------------------
            elif len(move.move_line_ids) == 1:

                line = move.move_line_ids[0]

                line.write({
                    "quantity": qty,
                    "pallets_loaded": move.loaded_pallets
                })

            # ---------------------------
            # MEERDERE lines → NIETS
            # ---------------------------
            else:
                _logger.warning(
                    "Skipping inverse: move %s has multiple lines",
                    move.id
                )
    """

    """ Berekent het totale gewicht van de stock move zelf"""
    @api.depends('move_line_ids.line_weight')
    def _compute_line_weight(self):
        _logger.warning("COMPUTED lINE WEIGHT CALLED !!!!!")
        for move in self:
            move.line_weight = sum(move.move_line_ids.mapped('line_weight'))

    """Herberekent het gewicht van de stock move zelf indien de qty aangepast werd"""
    @api.onchange('quantity', 'product_id')
    def _onchange_line_weight(self):
        for move in self:
            move.line_weight = (move.quantity or 0.0) * (move.product_id.weight or 0.0)

    """Forceer details altijd zichtbaar"""
    @api.depends('product_id', 'picking_type_id', 'state')
    def _compute_show_details_visible(self):
        super()._compute_show_details_visible()

        for move in self:
            # force split availability
            move.show_details_visible = True


    """tijdelijke functie om moveline data te kunnen zien bij popup detail"""
    def action_show_details(self):

        for move in self:
            _logger.warning("=== OPEN DETAILS POPUP ===")

            for line in move.move_line_ids:
                _logger.warning(
                    "MOVE LINE -> id=%s origin=%s pallets=%s qty=%s batch=%s",
                    line.id,
                    line._origin.id,
                    line.pallets_loaded,
                    line.quantity
                )

        return super().action_show_details()