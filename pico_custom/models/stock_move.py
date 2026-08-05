# pico_custom_repo/models/stock_move.py

from odoo import models, fields, api
import re
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    requested_pallets = fields.Integer(
        string='Pal',
        compute='_compute_requested_pallets',
        store=False
    )

    # invoerveld voor het aantal geladen pallets
    loaded_pallets = fields.Float(
        string='Pal geladen',
        compute="_compute_loaded_pallets",
        inverse="_inverse_loaded_pallets",
        help='Aantal effectief geladen pallets voor deze stock move.',
        digits=(16, 0),
    )

    # invoerveld voor het lotnummer van de aantal geladen pallets
    pico_batch_code = fields.Char(
        string="Lot",
        compute="_compute_pico_batch_code",
        inverse="_inverse_pico_batch_code",
        help="Interne productiebatch (bv. PK035)"
    )

    # berekend veld voor het totale gewicht van de stock move
    line_weight = fields.Float(
        string="Weight (kg)",
        compute='_compute_line_weight',
        help="totale gewicht van move",
        store=True
    )

    move_line_count = fields.Integer(
        compute="_compute_move_line_count",
        store = False
    )

    """ Berekent het aantal gewenste pallets op basis van het aantal bestelde stuks"""
    @api.depends('product_uom_qty', 'product_id.pieces_per_pallet')
    def _compute_requested_pallets(self):
        for move in self:
            ppp = move.product_id.pieces_per_pallet or 0.0
            if ppp:
                move.requested_pallets = float(move.product_uom_qty) / float(ppp)
            else:
                move.requested_pallets = 0.0


    @api.depends('move_line_ids.pallets_loaded')
    def _compute_loaded_pallets(self):
        for move in self:
            move.loaded_pallets = sum(move.move_line_ids.mapped('pallets_loaded'))

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
                    "product_id": move.product_id.id,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "quantity": qty,
                    "pallets_loaded": move.loaded_pallets,
                    "pico_batch_code": move.pico_batch_code,
                })

            # ---------------------------
            # EXACT 1 line → UPDATE
            # ---------------------------
            elif len(move.move_line_ids) == 1:

                line = move.move_line_ids[0]

                line.write({
                    "quantity": qty,
                    "pallets_loaded": move.loaded_pallets,
                    "pico_batch_code": move.pico_batch_code,
                })

            # ---------------------------
            # MEERDERE lines → NIETS
            # ---------------------------
            else:
                _logger.warning(
                    "Skipping inverse: move %s has multiple lines",
                    move.id
                )

    @api.depends('move_line_ids.pico_batch_code')
    def _compute_pico_batch_code(self):
        for move in self:
            batches = list(filter(None, move.move_line_ids.mapped('pico_batch_code')))

            if not batches:
                move.pico_batch_code = False
            elif len(batches) == 1:
                move.pico_batch_code = batches[0]
            else:
                """ move.pico_batch_code = "MULTI" """
                move.pico_batch_code = f"{len(batches)} lots"

    def _inverse_pico_batch_code(self):
        _logger.warning("INVERSE PICO BATCH MOVE LINE EXECUTION ")

        for move in self:

            if len(move.move_line_ids) == 1:
                line = move.move_line_ids[0]

                line.write({
                    "pico_batch_code": move.pico_batch_code,
                })

    def _compute_move_line_count(self):
        for move in self:
            move.move_line_count = len(move.move_line_ids)

    """
    @api.onchange('loaded_pallets', 'pico_batch_code')
    def _onchange_sync_move_line_execution(self):
        _logger.warning("ONCHANGE MOVE LINE EXECUTION ")
        for move in self:
            _logger.warning("MOVE LINE EXECUTION %s ", move)
            _logger.warning("MOVE LINE EXECUTION IDS %s ", move.move_line_ids)
            if not move.move_line_ids:
                continue

            move_line = move.move_line_ids[0]

            ppp = move.product_id.pieces_per_pallet or 1
            qty_done = move.loaded_pallets * ppp

            move.move_line_ids = [
                (1, move.move_line_ids[0].id, {
                    'quantity': qty_done,
                    'pallets_loaded': move.loaded_pallets,
                    'pico_batch_code': move.pico_batch_code,
                })
            ]
    """

    """
    @api.onchange('loaded_pallets')
    def _onchange_loaded_pallets(self):
        for move in self:

            ppp = move.product_id.pieces_per_pallet
            if not ppp:
                continue

            values = {
                "product_id": move.product_id.id,
                "pallets_loaded": move.loaded_pallets,
                "pico_batch_code": move.pico_batch_code,
                "quantity": move.loaded_pallets * ppp,
            }

            lines = move.move_line_ids

            # -------------------------------------------------
            # GEEN LIJN → CREATE
            # -------------------------------------------------
            if not lines:

                move.move_line_ids = [(0, 0, values)]

                # ⚠️ opnieuw ophalen NA command
                new_line = move.move_line_ids[-1]

                _logger.warning(
                    "CREATED LINE -> repr=%s | id=%s | origin_id=%s",
                    new_line,
                    new_line.id,
                    new_line._origin.id,
                )

            # -------------------------------------------------
            # EXACT 1 LIJN → UPDATE
            # -------------------------------------------------
            elif len(lines) == 1:

                line = lines[0]

                move.move_line_ids = [
                    (1, line.id or line._origin.id, values)
                ]

                _logger.warning(
                    "UPDATED LINE -> repr=%s | id=%s | origin=%s",
                    line,
                    line.id,
                    line._origin.id,
                )

            # -------------------------------------------------
            # DEBUG ALLE LIJNEN
            # -------------------------------------------------
            _logger.warning(
                "ALL LINES -> %s",
                [
                    (
                        repr(l),
                        l.id,
                        l._origin.id,
                        l.pallets_loaded,
                        l.quantity,
                        l.pico_batch_code,
                    )
                    for l in move.move_line_ids
                ]
            )
    """

    """Wanneer het aantal geladen pallets wordt ingevoerd, bereken het aantal stuks."""
    """
    @api.onchange('loaded_pallets')
    def _onchange_loaded_pallets(self):

        for move in self:
            if move.loaded_pallets and move.product_id.pieces_per_pallet:
                move.quantity = (
                        move.loaded_pallets * move.product_id.pieces_per_pallet
                )
                _logger.warning(
                    "Loaded pallets gewijzigd: %s pallets x %s stuks = %s stuks totaal",
                    move.loaded_pallets,
                    move.product_id.pieces_per_pallet,
                    move.product_uom_qty,
                )
    """

    """ Berekent het totale gewicht van de stock move zelf"""
    @api.depends('move_line_ids.line_weight')
    def _compute_line_weight(self):
        _logger.warning("COMPUTED lINE WEIGHT CALLED !!!!!")
        for move in self:
            move.line_weight = sum(move.move_line_ids.mapped('line_weight'))

    @api.depends('move_line_ids.pallets_loaded', 'move_line_ids.pico_batch_code')
    def _compute_has_execution_lines(self):
        for move in self:
            move.has_execution_lines = len(move.move_line_ids) > 1

    """Herberekent het gewicht van de stock move zelf indien de qty aangepast werd"""
    @api.onchange('quantity', 'product_id')
    def _onchange_line_weight(self):
        for move in self:
            move.line_weight = (move.quantity or 0.0) * (move.product_id.weight or 0.0)

    """ Hulp def om stock moves niet te mergen, uniek maken op lot
        Zal later weg mogen indien we splitten via details ipv nieuwe stock move aan te maken.
    """
    """
    def _prepare_merge_moves_distinct_fields(self):
        _logger.warning("prepare_merge_moves_distinct_fields CALLED !!!!!")
        fields = super()._prepare_merge_moves_distinct_fields()

        if any(m.picking_id.picking_type_id.code == 'outgoing' for m in self):
            fields.append('pico_batch_code')

        return fields
    """

    """ Regex op lotnummer toepassen pl1 en pl01 naar pl 001 te krijgen"""
    @api.onchange('pico_batch_code')
    def _onchange_pico_batch_code(self):
        """Normalize batch code: two letters + zero-padded number (3 digits)"""
        for move in self:
            if not move.pico_batch_code:
                continue

            val = move.pico_batch_code.strip().upper()
            m = re.match(r'^([A-Z]{2})0*(\d+)$', val)
            if m:
                prefix, number = m.groups()
                move.pico_batch_code = f"{prefix}{int(number):03d}"
                _logger.info("Normalized pico_batch_code: %s", move.pico_batch_code)
            else:
                _logger.warning("Invalid pico_batch_code format: %s", move.pico_batch_code)


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
                    line.quantity,
                    line.pico_batch_code,
                )

        return super().action_show_details()

    """ Write gebruiken om eerst odoo logica aan te roepen, en dan pas ui data te syncen"""

    """
    def write(self, vals):
        _logger.warning("MOVE WRITE VALS: %s", vals)
        res = super().write(vals)

        if any(f in vals for f in ["loaded_pallets", "pico_batch_code"]):
            for move in self:
                move._post_write_execution_sync()

        return res
    """

    """
    @api.model_create_multi
    def create(self, vals_list):
        _logger.warning("CREATE STOCKMOVE DEF ENTERED")
        moves = super().create(vals_list)

        for move, vals in zip(moves, vals_list):

            if vals.get("loaded_pallets") or vals.get("pico_batch_code"):
                _logger.warning("_post_write_execution_sync CALLED !!!!!")
                move._post_write_execution_sync()

        return moves
    """

    """ Sync ui data naar moveline data"""
    """
    def _post_write_execution_sync(self):
        self.ensure_one()

        if not self.loaded_pallets:
            _logger.warning("if not self.loaded_pallets: !!!!!")
            return

        ppp = self.product_id.pieces_per_pallet or 1
        qty_done = self.loaded_pallets * ppp

        # ---------------------------
        # GEEN lines → CREATE
        # ---------------------------
        if not self.move_line_ids:
            _logger.warning("POST WRITE MOVE: No moveline part!!!!!")
            line = self.env['stock.move.line'].create({
                "move_id": self.id,
                "product_id": self.product_id.id,
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "qty_done": qty_done,
                "pallets_loaded": self.loaded_pallets,
                "pico_batch_code": self.pico_batch_code,
            })

            _logger.warning("No moveline part called")
            _logger.warning("line %s", line)

        # ---------------------------
        # EXACT 1 line → UPDATE
        # ---------------------------
        elif len(self.move_line_ids) == 1:
            _logger.warning("POST WRITE MOVE: HAS ONE moveline part!!!!!")
            line = self.move_line_ids[0]

            line.with_context(bypass_reservation_update=True).write({
                "qty_done": qty_done,
                "pallets_loaded": self.loaded_pallets,
                "pico_batch_code": self.pico_batch_code,
            })

        # ---------------------------
        # MULTI → NIETS
        # ---------------------------
    """