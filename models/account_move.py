from odoo import models, fields, api 

class AccountMove(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one(
        'stock.picking',
        string="Library Picking",
        readonly=True
    )
    is_penalty_invoice = fields.Boolean(
        string="Is Penalty Invoice",
        default=False,
        readonly=True
    )