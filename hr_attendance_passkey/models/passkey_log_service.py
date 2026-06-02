from odoo import _, api, fields, models


class HrAttendancePasskeyLogService(models.AbstractModel):
    _name = "hr.attendance.passkey.log.service"
    _description = "Passkey Attendance Logging Service"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def _create_passkey_log(
        self,
        *,
        employee,
        status,
        action=None,
        attendance=None,
        authentication_method="passkey",
        credential_id=None,
        authenticator_type=None,
        event_datetime=None,
        notes=None,
        context=None,
    ):
        """Create a structured log entry for passkey authentication events.

        Parameters
        ----------
        employee : recordset | int
            Employee record or ID.
        status : str
            "success" or "failed".
        action : str | None
            "check_in" or "check_out" when known.
        attendance : recordset | int | None
            Related attendance record for successful events.
        authentication_method : str
            Defaults to "passkey" but kept configurable for future reuse.
        credential_id : str | None
            Credential identifier provided by WebAuthn.
        authenticator_type : str | None
            Either "platform" or "cross_platform".
        event_datetime : datetime | None
            Optionally override the timestamp (defaults to now).
        notes : str | None
            Optional textual context (e.g., error message on failure).
        context : dict | None
            Additional client context gathered in the browser. Expected keys:
                - user_agent
                - ip_address
                - session_id
                - device: { name, type }
                - browser: { name, version }
                - operating_system: { name, version }
                - location: { latitude, longitude, city, country, location_name }
        """
        employee_rec = self._ensure_employee(employee)
        attendance_rec = self._ensure_attendance(attendance)

        context = context or {}
        location = context.get("location") or {}
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is not None and longitude is not None:
            geo_values = self._reverse_geocode(latitude, longitude)
            location.setdefault("city", geo_values.get("city"))
            location.setdefault("country", geo_values.get("country"))
            location.setdefault("location_name", geo_values.get("location_name"))

        vals = {
            "employee_id": employee_rec.id,
            "attendance_id": attendance_rec.id if attendance_rec else False,
            "action": action,
            "authentication_method": authentication_method,
            "status": status,
            "event_datetime": event_datetime,
            "credential_id": credential_id,
            "authenticator_type": authenticator_type,
            "notes": notes,
            "user_agent": context.get("user_agent"),
            "ip_address": context.get("ip_address"),
            "session_id": context.get("session_id"),
            "device_name": (context.get("device") or {}).get("name"),
            "device_type": (context.get("device") or {}).get("type"),
            "browser": (context.get("browser") or {}).get("name"),
            "browser_version": (context.get("browser") or {}).get("version"),
            "operating_system": (context.get("operating_system") or {}).get("name"),
            "operating_system_version": (context.get("operating_system") or {}).get("version"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "city": location.get("city"),
            "country": location.get("country"),
            "location_name": location.get("location_name"),
        }
        vals = self._finalize_values(vals)

        return self.env["hr.attendance.passkey.log"].sudo().create(vals)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @api.model
    def _ensure_employee(self, employee):
        if not employee:
            raise ValueError(_("Missing employee for passkey log."))
        employee_model = self.env["hr.employee"]
        if isinstance(employee, int):
            employee = employee_model.browse(employee)
        if not employee or not employee.exists():
            raise ValueError(_("Employee does not exist for passkey log."))
        return employee

    @api.model
    def _ensure_attendance(self, attendance):
        if not attendance:
            return self.env["hr.attendance"].browse()
        attendance_model = self.env["hr.attendance"]
        if isinstance(attendance, int):
            attendance = attendance_model.browse(attendance)
        return attendance if attendance and attendance.exists() else attendance_model.browse()

    @api.model
    def _reverse_geocode(self, latitude, longitude):
        geo_service = self.env["hr.attendance.passkey.geo.service"]
        return geo_service._reverse_geocode(latitude, longitude)

    @api.model
    def _finalize_values(self, values):
        clean_values = {**values}
        clean_values.setdefault("event_datetime", fields.Datetime.now())
        for key, value in list(clean_values.items()):
            if value is None:
                clean_values[key] = False
        return clean_values
