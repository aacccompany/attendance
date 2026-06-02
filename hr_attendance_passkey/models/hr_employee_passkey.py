from odoo import models, fields


class HrEmployeePasskey(models.Model):
    _name = 'hr.employee.passkey'
    _description = 'Employee WebAuthn Passkey Credential'
    _order = 'registered_at desc'

    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', index=True,
    )
    # credential_id is the base64url-encoded credential.id from the browser
    credential_id = fields.Char(
        string='Credential ID', required=True, index=True, copy=False,
    )
    # CBOR-encoded public key bytes, stored as base64
    public_key = fields.Text(string='Public Key (CBOR/base64)', required=True, copy=False)
    sign_count = fields.Integer(
        string='Signature Counter', default=0,
        help='Monotonic counter maintained by the authenticator. '
             'Increments on every assertion to detect cloned keys.',
    )
    device_name = fields.Char(string='Device / Authenticator Name')
    registered_at = fields.Datetime(string='Registered At', default=fields.Datetime.now, readonly=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('credential_id_uniq', 'UNIQUE(credential_id)',
         'A passkey credential ID must be unique across all employees.'),
    ]
