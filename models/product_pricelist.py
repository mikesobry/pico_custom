from odoo import models
import logging

_logger = logging.getLogger(__name__)

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def read(self, fields=None, load='_classic_read'):
        res = super().read(fields=fields, load=load)

        for rec_dict, rec_obj in zip(res, self):
            if 'item_ids' in rec_dict:
                # Sorteer recordset op de naam die in de UI getoond wordt
                sorted_items = rec_obj.item_ids.sorted(key=lambda r: r.name or '')
                # Update de dict voor frontend
                rec_dict['item_ids'] = sorted_items.ids
                # Log de naam van elk item (zoals in de “Toepasbaar op” kolom)
                item_names = [item.name for item in sorted_items]
                _logger.warning(f"Pricelist {rec_obj.name} item_ids gesorteerd: {item_names}")

        return res