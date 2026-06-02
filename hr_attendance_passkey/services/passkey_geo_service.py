from odoo import api, models


class HrAttendancePasskeyGeoService(models.AbstractModel):
    _name = "hr.attendance.passkey.geo.service"
    _description = "Passkey Attendance Geolocation Service"

    @api.model
    def _reverse_geocode(self, latitude, longitude):
        """Return reverse geocoding information for a given coordinate pair.

        The default implementation is a noop returning the original coordinates.
        Deployments can inherit/override this method to plug external providers
        such as Google Maps or OpenStreetMap.
        """
        if latitude is None or longitude is None:
            return {}

        return {
            "latitude": latitude,
            "longitude": longitude,
            "city": False,
            "country": False,
            "location_name": False,
        }
