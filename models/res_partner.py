from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_member = fields.Boolean(string="Is Library Member", default=False)
    cnic = fields.Char(string="CNIC Number")
    age = fields.Integer(string="Age")

    issued_books_count = fields.Integer(
        string="Borrowed Books",
        compute="_compute_library_stats",
    )
    reserved_books_count = fields.Integer(
        string="Reserved Books",
        compute="_compute_library_stats",
    )
    returned_books_count = fields.Integer(
        string="Returned Books",
        compute="_compute_library_stats",
    )

    def _compute_library_stats(self):
        """Calculates actual book quantities (stock.move) instead of transfer counts."""
        for partner in self:
            borrowed_moves = self.env["stock.move"].search(
                [
                    ("picking_id.partner_id", "=", partner.id),
                    ("picking_id.picking_type_id.code", "=", "outgoing"),
                    ("picking_id.state", "=", "done"),
                    ("picking_id.return_date", "=", False),
                ]
            )
            partner.issued_books_count = int(
                sum(m.quantity or m.product_uom_qty for m in borrowed_moves)
            )

            reserved_moves = self.env["stock.move"].search(
                [
                    ("picking_id.partner_id", "=", partner.id),
                    ("picking_id.picking_type_id.code", "=", "outgoing"),
                    ("picking_id.state", "=", "assigned"),
                ]
            )
            partner.reserved_books_count = int(
                sum(m.quantity or m.product_uom_qty for m in reserved_moves)
            )

            # 3. Returned Books (incoming done receipts)
            returned_moves = self.env["stock.move"].search(
                [
                    ("picking_id.partner_id", "=", partner.id),
                    ("picking_id.picking_type_id.code", "=", "incoming"),
                    ("picking_id.state", "=", "done"),
                ]
            )
            partner.returned_books_count = int(
                sum(m.quantity or m.product_uom_qty for m in returned_moves)
            )

    def action_view_issued_books(self):
        """Opens list view of individual currently borrowed book items."""
        self.ensure_one()
        return {
            "name": "Borrowed Books",
            "type": "ir.actions.act_window",
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": [
                ("picking_id.partner_id", "=", self.id),
                ("picking_id.picking_type_id.code", "=", "outgoing"),
                ("picking_id.state", "=", "done"),
                ("picking_id.return_date", "=", False),
            ],
        }

    def action_view_reserved_books(self):
        """Opens list view of individual reserved book items."""
        self.ensure_one()
        return {
            "name": "Reserved Books",
            "type": "ir.actions.act_window",
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": [
                ("picking_id.partner_id", "=", self.id),
                ("picking_id.picking_type_id.code", "=", "outgoing"),
                ("picking_id.state", "=", "assigned"),
            ],
        }

    def action_view_returned_books(self):
        """Opens list view of individual returned book items."""
        self.ensure_one()
        return {
            "name": "Returned Books",
            "type": "ir.actions.act_window",
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": [
                ("picking_id.partner_id", "=", self.id),
                ("picking_id.picking_type_id.code", "=", "incoming"),
                ("picking_id.state", "=", "done"),
            ],
        }