from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    passkey_ids = fields.One2many(
        'hr.employee.passkey', 'employee_id',
        string='Registered Passkeys',
    )
    passkey_count = fields.Integer(
        compute='_compute_passkey_count', string='Passkeys', compute_sudo=True,
    )
    passkey_log_count = fields.Integer(
        compute='_compute_passkey_log_count', string='Passkey Logs', compute_sudo=True
    )

    @api.depends('passkey_ids.active')
    def _compute_passkey_count(self):
        groups = self.env['hr.employee.passkey']._read_group(
            domain=[('employee_id', 'in', self.ids), ('active', '=', True)],
            groupby=['employee_id'],
            aggregates=['__count'],
        )
        mapping = {employee.id: count for employee, count in groups}
        for rec in self:
            rec.passkey_count = mapping.get(rec.id, 0)

    def _compute_passkey_log_count(self):
        groups = self.env['hr.attendance.passkey.log']._read_group(
            domain=[('employee_id', 'in', self.ids)],
            groupby=['employee_id'],
            aggregates=['__count'],
        )
        mapping = {employee.id: count for employee, count in groups}
        for rec in self:
            rec.passkey_log_count = mapping.get(rec.id, 0)

    def action_register_passkey(self):
        """Open the passkey registration wizard (client action handled in JS)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hr_attendance_passkey.register_passkey',
            'target': 'new',
            'context': {'employee_id': self.id, 'employee_name': self.name},
        }

    def action_open_passkey_logs(self):
        self.ensure_one()
        action = self.env.ref('hr_attendance_passkey.hr_attendance_passkey_log_action', raise_if_not_found=False)
        result = action.read()[0] if action else {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.passkey.log',
            'view_mode': 'tree,form',
        }
        result.setdefault('context', {})
        result['context'] = {**result['context'], 'default_employee_id': self.id}
        result['domain'] = [('employee_id', '=', self.id)]
        return result
