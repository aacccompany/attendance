from odoo import api, fields, models


class HrAttendancePasskeyLog(models.Model):
    _name = "hr.attendance.passkey.log"
    _description = "Attendance Passkey Authentication Log"
    _order = "event_datetime desc, id desc"

    _check_company_auto = True

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="employee_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    attendance_id = fields.Many2one(
        "hr.attendance",
        string="Attendance",
        index=True,
    )
    action = fields.Selection(
        selection=[
            ("check_in", "Check In"),
            ("check_out", "Check Out"),
        ],
        string="Action",
        index=True,
    )
    authentication_method = fields.Selection(
        selection=[
            ("passkey", "Passkey"),
        ],
        string="Authentication Method",
        default="passkey",
        required=True,
    )
    status = fields.Selection(
        selection=[
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Status",
        index=True,
        required=True,
    )
    event_datetime = fields.Datetime(
        string="Event Date",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    credential_id = fields.Char(string="Credential ID", index=True)
    authenticator_type = fields.Selection(
        selection=[
            ("platform", "Platform"),
            ("cross_platform", "Cross Platform"),
        ],
        string="Authenticator Type",
    )
    device_name = fields.Char(string="Device Name")
    device_type = fields.Char(string="Device Type")
    browser = fields.Char(string="Browser")
    browser_version = fields.Char(string="Browser Version")
    operating_system = fields.Char(string="Operating System")
    operating_system_version = fields.Char(string="OS Version")
    user_agent = fields.Text(string="User Agent")
    ip_address = fields.Char(string="IP Address")
    latitude = fields.Float(string="Latitude")
    longitude = fields.Float(string="Longitude")
    location_name = fields.Char(string="Location")
    country = fields.Char(string="Country")
    city = fields.Char(string="City")
    session_id = fields.Char(string="Session ID")
    notes = fields.Text(string="Notes")
