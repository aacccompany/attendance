import base64
import json
import logging

from markupsafe import Markup, escape

from odoo import _, fields, http
from odoo.http import request
from odoo.tools.misc import format_datetime

_logger = logging.getLogger(__name__)

try:
    import webauthn
    from webauthn.helpers.structs import (
        AuthenticationCredential,
        AuthenticatorAssertionResponse,
        AuthenticatorAttestationResponse,
        PublicKeyCredentialDescriptor,
        RegistrationCredential,
        UserVerificationRequirement,
    )
    _WEBAUTHN_AVAILABLE = True
except Exception as e:
    _WEBAUTHN_AVAILABLE = False
    _logger.warning('webauthn unavailable: %s', e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rp_id():
    return request.httprequest.host.split(':')[0]


def _origin():
    return f"{request.httprequest.scheme}://{request.httprequest.host}"


def _b64url(value: str) -> bytes:
    """Convert a base64url string (with or without padding) to bytes."""
    return webauthn.base64url_to_bytes(value)


def _client_ip():
    forwarded = request.httprequest.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.httprequest.remote_addr or request.httprequest.environ.get("REMOTE_ADDR")


def _prepare_context(payload):
    context = dict(payload or {})

    user_agent = request.httprequest.headers.get("User-Agent", "")
    if user_agent and not context.get("user_agent"):
        context["user_agent"] = user_agent

    ip_address = _client_ip()
    if ip_address:
        context.setdefault("ip_address", ip_address)

    session_id = getattr(request.session, "sid", None)
    if session_id:
        context.setdefault("session_id", session_id)

    location = dict(context.get("location") or {})
    for field_name in ("latitude", "longitude"):
        if field_name in location and location[field_name] is not None:
            try:
                location[field_name] = float(location[field_name])
            except (TypeError, ValueError):
                location[field_name] = None
    context["location"] = location

    return context


def _render_passkey_success_message(employee, action, context, event_datetime):
    device = context.get("device") or {}
    browser = context.get("browser") or {}
    operating_system = context.get("operating_system") or {}
    location = context.get("location") or {}

    action_label = {
        "check_in": _("Check In"),
        "check_out": _("Check Out"),
    }.get(action, _("Unknown"))

    device_label = ", ".join(
        filter(None, [device.get("name"), device.get("type") and device.get("type").title()])
    ) or _("Unspecified")
    browser_label = " ".join(filter(None, [browser.get("name"), browser.get("version")])) or _(
        "Unspecified"
    )
    os_label = " ".join(
        filter(None, [operating_system.get("name"), operating_system.get("version")])
    ) or _("Unspecified")
    ip_address = context.get("ip_address") or _("Unavailable")

    timestamp = format_datetime(request.env, event_datetime) if event_datetime else ""

    items = [
        f"<li><strong>{escape(_('Employee'))}:</strong> {escape(employee.name)}</li>",
        f"<li><strong>{escape(_('Action'))}:</strong> {escape(action_label)}</li>",
        f"<li><strong>{escape(_('Device'))}:</strong> {escape(device_label)}</li>",
        f"<li><strong>{escape(_('Browser'))}:</strong> {escape(browser_label)}</li>",
        f"<li><strong>{escape(_('OS'))}:</strong> {escape(os_label)}</li>",
        f"<li><strong>{escape(_('IP Address'))}:</strong> {escape(ip_address)}</li>",
    ]

    if location.get("city") or location.get("country") or location.get("location_name"):
        location_parts = [location.get("location_name"), location.get("city"), location.get("country")]
        location_label = ", ".join([part for part in location_parts if part])
        items.append(
            f"<li><strong>{escape(_('Location'))}:</strong> {escape(location_label)}</li>"
        )

    if timestamp:
        items.append(f"<li><strong>{escape(_('Time'))}:</strong> {escape(timestamp)}</li>")

    title = escape(_("Passkey authentication successful"))
    items_markup = Markup("".join(items))
    return Markup("<p>{}</p><ul>{}</ul>").format(title, items_markup)


def _parse_registration_credential(cred: dict) -> 'RegistrationCredential':
    resp = cred.get('response', {})
    return RegistrationCredential(
        id=cred['id'],
        raw_id=_b64url(cred['rawId']),
        response=AuthenticatorAttestationResponse(
            client_data_json=_b64url(resp['clientDataJSON']),
            attestation_object=_b64url(resp['attestationObject']),
            transports=resp.get('transports'),
        ),
        authenticator_attachment=cred.get('authenticatorAttachment'),
    )


def _parse_authentication_credential(cred: dict) -> 'AuthenticationCredential':
    resp = cred.get('response', {})
    user_handle = resp.get('userHandle')
    return AuthenticationCredential(
        id=cred['id'],
        raw_id=_b64url(cred['rawId']),
        response=AuthenticatorAssertionResponse(
            client_data_json=_b64url(resp['clientDataJSON']),
            authenticator_data=_b64url(resp['authenticatorData']),
            signature=_b64url(resp['signature']),
            user_handle=_b64url(user_handle) if user_handle else None,
        ),
        authenticator_attachment=cred.get('authenticatorAttachment'),
    )


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class WebAuthnController(http.Controller):

    # ------------------------------------------------------------------
    # Passkey Registration  (called by HR manager in the backend)
    # ------------------------------------------------------------------

    @http.route(
        '/attendance/passkey/registration/begin',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def registration_begin(self, employee_id, **kw):
        if not _WEBAUTHN_AVAILABLE:
            return {'error': 'webauthn not installed on the server.'}

        employee = request.env['hr.employee'].browse(int(employee_id))
        if not employee.exists():
            return {'error': 'Employee not found.'}

        existing = request.env['hr.employee.passkey'].search(
            [('employee_id', '=', employee.id), ('active', '=', True)]
        )
        exclude = [
            PublicKeyCredentialDescriptor(id=_b64url(pk.credential_id))
            for pk in existing
        ]

        options = webauthn.generate_registration_options(
            rp_id=_rp_id(),
            rp_name=request.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', default='Odoo'
            ),
            user_id=str(employee.id).encode(),
            user_name=employee.work_email or employee.login or employee.name,
            user_display_name=employee.name,
            exclude_credentials=exclude,
        )

        request.session['passkey_reg_challenge'] = base64.b64encode(options.challenge).decode()
        request.session['passkey_reg_employee'] = employee.id

        return json.loads(webauthn.options_to_json(options))

    @http.route(
        '/attendance/passkey/registration/complete',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def registration_complete(self, credential, device_name=None, **kw):
        if not _WEBAUTHN_AVAILABLE:
            return {'error': 'webauthn not installed on the server.'}

        raw_challenge = request.session.pop('passkey_reg_challenge', None)
        employee_id = request.session.pop('passkey_reg_employee', None)
        if not raw_challenge or not employee_id:
            return {'error': 'No pending registration session.'}

        challenge = base64.b64decode(raw_challenge)

        try:
            reg_credential = _parse_registration_credential(credential)
            verified = webauthn.verify_registration_response(
                credential=reg_credential,
                expected_challenge=challenge,
                expected_rp_id=_rp_id(),
                expected_origin=_origin(),
                require_user_verification=False,
            )
        except Exception as exc:
            _logger.warning('Passkey registration failed: %s', exc)
            return {'error': str(exc)}

        request.env['hr.employee.passkey'].create({
            'employee_id': employee_id,
            'credential_id': base64.urlsafe_b64encode(verified.credential_id).rstrip(b'=').decode(),
            'public_key': base64.b64encode(verified.credential_public_key).decode(),
            'sign_count': verified.sign_count,
            'device_name': device_name or 'Unknown device',
        })

        return {'status': 'ok'}

    # ------------------------------------------------------------------
    # Passkey Authentication  (called by the kiosk — public auth)
    # ------------------------------------------------------------------

    @http.route(
        '/attendance/passkey/authentication/begin',
        type='jsonrpc', auth='public', methods=['POST'],
        csrf=False,
    )
    def authentication_begin(self, **kw):
        if not _WEBAUTHN_AVAILABLE:
            return {'error': 'webauthn not installed on the server.'}

        options = webauthn.generate_authentication_options(
            rp_id=_rp_id(),
            allow_credentials=[],
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        request.session['passkey_auth_challenge'] = base64.b64encode(options.challenge).decode()
        return json.loads(webauthn.options_to_json(options))

    @http.route(
        '/attendance/passkey/authentication/complete',
        type='jsonrpc', auth='public', methods=['POST'],
        csrf=False,
    )
    def authentication_complete(self, credential, **kw):
        if not _WEBAUTHN_AVAILABLE:
            return {'error': 'webauthn not installed on the server.'}

        raw_challenge = request.session.pop('passkey_auth_challenge', None)
        if not raw_challenge:
            return {'error': 'No active authentication session.'}

        challenge = base64.b64decode(raw_challenge)
        cred_id_b64 = credential.get('id', '')

        PasskeyModel = request.env['hr.employee.passkey'].sudo()
        passkey = PasskeyModel.search(
            [('credential_id', '=', cred_id_b64), ('active', '=', True)],
            limit=1,
        )
        if not passkey:
            return {'error': 'Credential not registered.'}

        context_payload = _prepare_context(kw.get('context'))
        authenticator_raw = credential.get('authenticatorAttachment')
        authenticator_type = {
            'cross-platform': 'cross_platform',
        }.get(authenticator_raw, authenticator_raw)
        if authenticator_type not in {'platform', 'cross_platform'}:
            authenticator_type = False
        log_service = request.env['hr.attendance.passkey.log.service'].sudo()

        try:
            auth_credential = _parse_authentication_credential(credential)
            verified = webauthn.verify_authentication_response(
                credential=auth_credential,
                expected_challenge=challenge,
                expected_rp_id=_rp_id(),
                expected_origin=_origin(),
                credential_public_key=base64.b64decode(passkey.public_key),
                credential_current_sign_count=passkey.sign_count,
                require_user_verification=False,
            )
        except Exception as exc:
            _logger.warning('Passkey authentication failed for cred %s: %s', cred_id_b64, exc)
            log_service._create_passkey_log(
                employee=passkey.employee_id,
                status='failed',
                action=None,
                attendance=None,
                credential_id=cred_id_b64,
                authenticator_type=authenticator_type,
                notes=str(exc),
                context=context_payload,
            )
            return {'error': str(exc)}

        passkey.sign_count = verified.new_sign_count

        employee = passkey.employee_id
        AttModel = request.env['hr.attendance'].sudo()
        open_att = AttModel.search(
            [('employee_id', '=', employee.id), ('check_out', '=', False)],
            limit=1,
        )
        now = fields.Datetime.now()

        attendance = open_att
        if open_att:
            open_att.write({'check_out': now})
            action = 'check_out'
        else:
            attendance = AttModel.create({
                'employee_id': employee.id,
                'check_in': now,
                'check_in_method': 'passkey',
            })
            action = 'check_in'
        attendance = attendance or open_att

        log_record = log_service._create_passkey_log(
            employee=employee,
            attendance=attendance,
            status='success',
            action=action,
            event_datetime=now,
            credential_id=cred_id_b64,
            authenticator_type=authenticator_type,
            context=context_payload,
        )

        body = _render_passkey_success_message(employee, action, context_payload, now)

        mail_context = {"mail_post_autofollow": False}

        if attendance and hasattr(attendance, "message_post"):
            _logger.info(
                "Passkey attendance chatter posting on attendance %s for employee %s",
                attendance.ids,
                employee.ids,
            )
            msg_id = attendance.with_context(**mail_context).sudo().message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            _logger.info("Passkey attendance chatter posted: message %s", msg_id)

        if hasattr(employee, "message_post"):
            _logger.info(
                "Passkey attendance chatter posting on employee %s",
                employee.ids,
            )
            msg_id = employee.with_context(**mail_context).sudo().message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            _logger.info("Passkey employee chatter posted: message %s", msg_id)

        return {
            'status': 'ok',
            'action': action,
            'employee_id': employee.id,
            'employee_name': employee.name,
            'log_id': log_record.id if log_record else False,
        }

