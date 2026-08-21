from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_book = fields.Boolean(string="Is a Book")
    author = fields.Char(string="Author")
    publisher = fields.Char(string="Publisher")