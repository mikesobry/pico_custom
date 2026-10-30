{
    'name': 'Pico Custom',
    'version': '1.0',
    'summary': 'Aanpassingen voor Pico / Sobry BV',
    'description': 'Voegt extra velden toe zoals aantal stuks per pallet bij producten.',
    'category': 'Custom',
    'author': 'Mike Sobry',
    'license': 'LGPL-3',
    'depends': [
        'product',  # voor product.template
        'sale',     # voor sale.order
        'sale_stock', #voor 14 dagen extra op picking date
        'stock',    #voor stock.move
        'stock_picking_batch'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/stock_move_views.xml',
        'views/stock_move_operations.xml',
        'views/stock_picking.xml',
        'views/pallet_check_wizard_views.xml',
        'report/stock_picking_report_inherit.xml',
        'views/sale_res_config_settings_view_form.xml',
        'report/sale_report_plantool_templates.xml', #pdf plantool
        'report/sale_report_plantool.xml', #pdf plantool
        'report/stock_batch_deliveryslip_templates.xml',
        'report/stock_batch_deliveryslip.xml',
    ],
    'installable': True,
    'application': False,
}
