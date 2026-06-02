{
    'name': 'HR Attendance — Passkey Check-in',
    'version': '19.0.1.1.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Kiosk check-in via WebAuthn Passkey',
    'author': 'Custom',
    'depends': ['hr_attendance', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_attendance_passkey_log_rules.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_passkey_log_views.xml',
    ],
    'assets': {
        'hr_attendance.assets_public_attendance': [
            'hr_attendance_passkey/static/src/scss/passkey_kiosk.scss',
            'hr_attendance_passkey/static/src/js/services/webauthn_service.js',
            'hr_attendance_passkey/static/src/js/services/passkey_context_service.js',
            'hr_attendance_passkey/static/src/js/components/passkey_kiosk_extension/passkey_kiosk_extension.js',
            'hr_attendance_passkey/static/src/js/components/passkey_kiosk_extension/passkey_kiosk_extension.xml',
        ],
        'web.assets_backend': [
            'hr_attendance_passkey/static/src/js/services/webauthn_service.js',
            'hr_attendance_passkey/static/src/js/services/passkey_context_service.js',
            'hr_attendance_passkey/static/src/js/components/passkey_register_wizard/passkey_register_wizard.js',
            'hr_attendance_passkey/static/src/js/components/passkey_register_wizard/passkey_register_wizard.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
