from odoo import models, fields, api


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_method = fields.Selection(
        selection=[
            ('manual', 'Manual'),
            ('passkey', 'Passkey'),
            ('rfid', 'RFID'),
        ],
        string='Check-in Method',
        default='manual',
        readonly=True,
    )
    passkey_log_count = fields.Integer(
        compute='_compute_passkey_log_count', string='Passkey Logs', compute_sudo=True
    )

    @api.depends('employee_id')
    def _compute_passkey_log_count(self):
        groups = self.env['hr.attendance.passkey.log']._read_group(
            domain=[('attendance_id', 'in', self.ids)],
            groupby=['attendance_id'],
            aggregates=['__count'],
        )
        mapping = {attendance.id: count for attendance, count in groups}
        for rec in self:
            rec.passkey_log_count = mapping.get(rec.id, 0)

    def action_open_passkey_logs(self):
        self.ensure_one()
        action = self.env.ref('hr_attendance_passkey.hr_attendance_passkey_log_action', raise_if_not_found=False)
        result = action.read()[0] if action else {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.passkey.log',
            'view_mode': 'tree,form',
        }
        result.setdefault('context', {})
        result['context'] = {**result['context'], 'default_attendance_id': self.id}
        result['domain'] = [('attendance_id', '=', self.id)]
        return result
