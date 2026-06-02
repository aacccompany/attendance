import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { runPasskeyAuthentication } from "../../services/webauthn_service";
import { gatherPasskeyContext } from "../../services/passkey_context_service";

import PublicKioskModule from "@hr_attendance/public_kiosk/public_kiosk_app";

const { kioskAttendanceApp } = PublicKioskModule;

patch(kioskAttendanceApp.prototype, {
    setup() {
        super.setup(...arguments);
        this.passkeyState = useState({ loading: false, error: "" });
        this.notification = useService("notification");
    },

    async onPasskeyClick() {
        if (this.passkeyState.loading) return;
        this.passkeyState.loading = true;
        this.passkeyState.error = "";
        try {
            const context = await gatherPasskeyContext();
            const credential = await runPasskeyAuthentication();
            const result = await rpc("/attendance/passkey/authentication/complete", { credential, context });
            if (result.error) throw new Error(result.error);
            const employeeData = await rpc("attendance_employee_data", {
                token: this.props.token,
                employee_id: result.employee_id,
            });
            if (employeeData && employeeData.employee_name) {
                this.employeeData = employeeData;
                this.switchDisplay("greet");
            } else {
                this.switchDisplay("main");
            }
        } catch (err) {
            this.passkeyState.error = err.message || "ยืนยันตัวตนไม่สำเร็จ";
            this.notification.add(this.passkeyState.error, { type: "danger" });
        } finally {
            this.passkeyState.loading = false;
        }
    },
});
