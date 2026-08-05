# pico_custom_repo/models/migrate_stock_move_lines.py

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockMoveMigration(models.Model):
    _inherit = "stock.move"

    def migrate_batch_codes_to_move_lines(self, dry_run=True):
        """
        Migratie van pico_batch_code / loaded_pallets / quantity
        van stock.move (legacy, verweesde kolommen) naar stock.move.line.

        dry_run=True  (default): enkel loggen, GEEN write.
        dry_run=False: schrijft ENKEL de eenduidige 1-op-1 gevallen.
                       Multi-line gevallen worden NOOIT automatisch geschreven,
                       ongeacht dry_run -- die blijven altijd manueel.

        BELANGRIJK: deze methode commit niet zelf. Na een write-run
        moet je zelf beslissen of je de wijzigingen bevestigt:
            env.cr.commit()
        Zolang je niet commit, kan je gerust een write-run testen en
        herroepen door de shell te verlaten zonder commit.
        """

        _logger.info("=" * 80)
        _logger.info("PICO BATCH MIGRATION (dry_run=%s)", dry_run)
        _logger.info("=" * 80)

        # Raw SQL leesactie: pico_batch_code/loaded_pallets zijn niet-stored
        # compute-velden, maar de legacy DB-kolommen bevatten nog data.
        self.env.cr.execute("""
            SELECT id, pico_batch_code, loaded_pallets, state
            FROM stock_move
            WHERE pico_batch_code IS NOT NULL
               OR loaded_pallets IS NOT NULL
        """)
        rows = self.env.cr.fetchall()
        legacy_data = {r[0]: {"batch": r[1], "pallets": r[2], "state": r[3]} for r in rows}

        moves = self.browse(list(legacy_data.keys()))

        _logger.info("Aantal kandidaat-moves gevonden: %s", len(moves))

        stats = {
            "written": 0,
            "would_write": 0,
            "manual_multi_open": 0,
            "manual_multi_done": 0,
            "no_lines": 0,
            "already_filled": 0,
            "cancelled": 0,
            "suspicious": 0,
        }

        for move in moves:
            data = legacy_data[move.id]
            old_batch = data["batch"]
            old_pallets = data["pallets"]
            old_state = data["state"]
            old_qty = move.quantity  # normaal, stored veld -- gewoon via ORM

            # ------------------------------------------------------
            if old_state == "cancel":
                stats["cancelled"] += 1
                _logger.info("[SKIP-CANCEL] %s | move_id=%s", move.picking_id.name, move.id)
                continue

            # ------------------------------------------------------
            # Verdachte waarden -- nooit automatisch schrijven
            # ------------------------------------------------------
            if old_pallets is not None and old_pallets < 0:
                stats["suspicious"] += 1
                _logger.error(
                    "[SUSPICIOUS-SKIP] %s | move_id=%s | negatieve pallets=%s -- manueel bekijken",
                    move.picking_id.name, move.id, old_pallets,
                )
                continue

            lines = move.move_line_ids

            # ------------------------------------------------------
            if not lines:
                stats["no_lines"] += 1
                _logger.warning(
                    "[NO-LINES] %s | move_id=%s | state=%s | batch=%s | pallets=%s",
                    move.picking_id.name, move.id, old_state, old_batch, old_pallets,
                )
                continue

            # ------------------------------------------------------
            # Meerdere move lines: NOOIT automatisch schrijven.
            # Wel: check of je ze zelf al manueel hebt aangevuld.
            # ------------------------------------------------------
            if len(lines) > 1:
                missing = lines.filtered(lambda l: not l.pico_batch_code and not l.pallets_loaded)

                if not missing:
                    stats["manual_multi_done"] += 1
                    _logger.info(
                        "[MULTI-ALREADY-DONE] %s | move_id=%s | alle %s lines al ingevuld",
                        move.picking_id.name, move.id, len(lines),
                    )
                else:
                    stats["manual_multi_open"] += 1
                    _logger.warning(
                        "[MANUAL-MULTI-OPEN] %s | move_id=%s | %s/%s lines nog leeg | "
                        "move_batch=%s | move_pallets=%s | move_qty=%s",
                        move.picking_id.name, move.id, len(missing), len(lines),
                        old_batch, old_pallets, old_qty,
                    )
                    for line in missing:
                        _logger.warning(
                            "    -> nog leeg: line_id=%s | qty=%s", line.id, line.quantity,
                        )
                continue

            # ------------------------------------------------------
            # Exact 1 move line
            # ------------------------------------------------------
            line = lines[0]

            if line.pico_batch_code or line.pallets_loaded:
                stats["already_filled"] += 1
                _logger.info(
                    "[ALREADY-FILLED] %s | move_id=%s | line_id=%s",
                    move.picking_id.name, move.id, line.id,
                )
                continue

            if dry_run:
                stats["would_write"] += 1
                _logger.info(
                    "[WOULD-WRITE] %s | move_id=%s | line_id=%s | "
                    "batch: %s -> %s | pallets: %s -> %s | qty: %s -> %s",
                    move.picking_id.name, move.id, line.id,
                    line.pico_batch_code, old_batch,
                    line.pallets_loaded, old_pallets,
                    line.quantity, old_qty,
                )
            else:
                _logger.info(
                    "[WRITE] %s | move_id=%s | line_id=%s | "
                    "batch: %s -> %s | pallets: %s -> %s | qty: %s -> %s",
                    move.picking_id.name, move.id, line.id,
                    line.pico_batch_code, old_batch,
                    line.pallets_loaded, old_pallets,
                    line.quantity, old_qty,
                )
                line.write({
                    "pico_batch_code": old_batch,
                    "pallets_loaded": old_pallets,
                    "quantity": old_qty,
                })
                stats["written"] += 1

        _logger.info("=" * 80)
        _logger.info("SAMENVATTING (dry_run=%s)", dry_run)
        _logger.info("=" * 80)
        _logger.info("Written                        : %s", stats["written"])
        _logger.info("Would write (enkel bij dry_run) : %s", stats["would_write"])
        _logger.info("Al ingevuld (1 line)            : %s", stats["already_filled"])
        _logger.info("Multi-line: nog open            : %s", stats["manual_multi_open"])
        _logger.info("Multi-line: al manueel gedaan    : %s", stats["manual_multi_done"])
        _logger.info("Geen move lines                 : %s", stats["no_lines"])
        _logger.info("Verdacht (bv. negatief) - skip   : %s", stats["suspicious"])
        _logger.info("Cancelled                       : %s", stats["cancelled"])
        _logger.info("=" * 80)
        if dry_run:
            _logger.info("DRY RUN -- ER IS NIETS GEWIJZIGD IN DE DATABASE.")
        else:
            _logger.info("WRITES UITGEVOERD, MAAR NOG NIET GECOMMIT.")
            _logger.info("Roep zelf env.cr.commit() aan om te bevestigen.")
        _logger.info("=" * 80)

        return stats