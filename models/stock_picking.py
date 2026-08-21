from datetime import date, timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    issue_date = fields.Date(string="Issue Date")
    due_date = fields.Date(string="Due Date")
    return_date = fields.Date(string="Return Date")

    invoice_id = fields.Many2one("account.move", string="Issue Invoice")
    penalty_invoice_id = fields.Many2one(
        "account.move", string="Penalty Invoice"
    )

    def _check_reservation_limit(self):
        """Enforces a maximum limit of 3 reserved books per customer."""
        for picking in self:
            if not picking.partner_id:
                raise UserError(
                    "Please select a customer before reserving or issuing books."
                )

            # 1. Count books currently reserved in other active pickings
            reserved_pickings = self.search(
                [
                    ("partner_id", "=", picking.partner_id.id),
                    ("state", "=", "assigned"),
                    ("id", "!=", picking.id),
                ]
            )

            reserved_qty = sum(
                move.product_uom_qty or move.quantity
                for p in reserved_pickings
                for move in p.move_ids
            )

            # 2. Count books in the current picking request
            current_qty = sum(
                move.product_uom_qty or move.quantity
                for move in picking.move_ids
            )

            total_reserved = reserved_qty + current_qty

            # 3. Block reservation if total exceeds 3
            if total_reserved > 3:
                raise UserError(
                    "Reservation Limit Exceeded!\n\n"
                    f"{picking.partner_id.name} already has {reserved_qty:g} book(s) reserved.\n\n"
                    f"This reservation request contains {current_qty:g} book(s).\n\n"
                    f"Total ({total_reserved:g}) exceeds the maximum limit of 3 books."
                )

    def action_confirm(self):
        """Triggers when clicking 'Reserve' on a Draft transfer."""
        self._check_reservation_limit()
        return super(StockPicking, self).action_confirm()

    def action_assign(self):
        """Triggers when checking availability on a confirmed transfer."""
        self._check_reservation_limit()
        return super(StockPicking, self).action_assign()

    def button_validate(self):
        """Generates issue invoice on delivery or penalty invoice on late return."""
        res = super(StockPicking, self).button_validate()
        today = fields.Date.today()
        due_15_days = today + timedelta(days=15)

        for picking in self:
            if picking.state != "done":
                continue

            # SCENARIO 1: Primary Book Issuance
            if not picking.return_id and not picking.invoice_id:
                picking.issue_date = today
                picking.due_date = due_15_days
                picking._generate_issue_invoice(today, due_15_days)

            # SCENARIO 2: Return Transfer
            elif picking.return_id:
                orig_picking = picking.return_id
                orig_picking.return_date = today

                if orig_picking.due_date and today > orig_picking.due_date:
                    late_days = (today - orig_picking.due_date).days
                    daily_rate = 200.0
                    penalty_amount = late_days * daily_rate
                    orig_picking._generate_penalty_invoice(
                        penalty_amount, late_days
                    )

        return res

    def _generate_issue_invoice(self, today, due_date):
        """Creates main issue invoice using 'Book as a Service' product."""
        for picking in self:
            if not picking.partner_id or picking.invoice_id:
                raise UserError(
                    "Please select a customer before reserving or issuing books."
                )

            service_product = self.env["product.product"].search(
                [("name", "ilike", "Book as a Service")], limit=1
            )

            invoice_lines = []
            for move in picking.move_ids:
                qty = move.quantity or move.product_uom_qty
                book_variant = move.product_id
                unit_price = book_variant.lst_price

                description = (
                    f"{book_variant.display_name} , "
                    f"Quantity: {qty:.2f} , "
                    f"Price : ${unit_price:.2f}"
                )

                line_data = {
                    "product_id": service_product.id
                    if service_product
                    else False,
                    "name": description,
                    "quantity": qty,
                    "price_unit": unit_price,
                }

                if service_product and service_product.taxes_id:
                    line_data["tax_ids"] = [
                        (6, 0, service_product.taxes_id.ids)
                    ]

                invoice_lines.append((0, 0, line_data))

            if invoice_lines:
                invoice = self.env["account.move"].create(
                    {
                        "move_type": "out_invoice",
                        "partner_id": picking.partner_id.id,
                        "invoice_date": today,
                        "invoice_date_due": due_date,
                        "invoice_line_ids": invoice_lines,
                    }
                )
                picking.invoice_id = invoice.id

    def _generate_penalty_invoice(self, amount, late_days):
        """Creates draft penalty invoice for overdue returns."""
        for picking in self:
            if not picking.partner_id or picking.penalty_invoice_id:
                raise UserError(
                    "Please select a customer before reserving or issuing books."
                )

            penalty_line = (0,0,{
                "name": f"Late Return Penalty ({late_days} Days Overdue) - Transfer Ref: {picking.name}",
                "quantity": 1.0,
                "price_unit": amount,
            },)

            invoice = self.env["account.move"].create({
                "move_type": "out_invoice",
                "partner_id": picking.partner_id.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [penalty_line],
            })
            picking.penalty_invoice_id = invoice.id

    @api.model
    def _cron_check_expired_reservations(self):
        """Unreserves stock and resets pickings overdue by 3+ days back to draft."""
        expiration_threshold = fields.Datetime.now() - timedelta(days=3)

        expired_pickings = self.search(
            [
                ("state", "=", "assigned"),
                ("scheduled_date", "<=", expiration_threshold),
            ]
        )

        for picking in expired_pickings:
            picking.do_unreserve()
            picking.write({"state": "draft"})