/**
 * PasskeyRegisterWizard — Backend client action
 *
 * Opened from the Employee form when an HR manager clicks
 * "Register Passkey on This Device".  Runs the WebAuthn registration
 * ceremony in the manager's browser, then persists the credential
 * on the server.
 */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import {
    prepareRegistrationOptions,
    serializeRegistrationCredential,
} from "../../services/webauthn_service";

class PasskeyRegisterWizard extends Component {
    static template = "hr_attendance_passkey.PasskeyRegisterWizard";
    // Accept all props — Odoo passes action, actionService, etc.
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");

        // In Odoo 17+, the action descriptor is passed as props.action
        const ctx = this.props.action?.context || {};
        this.employeeId = ctx.employee_id;
        this.employeeName = ctx.employee_name || "Employee";

        this.state = useState({
            /** idle | registering | success | error */
            phase: "idle",
            message: "",
            deviceName: "",
        });
    }

    async onRegister() {
        if (!this.employeeId) {
            this.state.phase = "error";
            this.state.message = "No employee context found.";
            return;
        }

        this.state.phase = "registering";
        this.state.message = "Follow the Passkey prompt on your device…";

        try {
            // 1. Get registration options from server
            const rawOptions = await rpc(
                "/attendance/passkey/registration/begin",
                { employee_id: this.employeeId }
            );
            if (rawOptions.error) throw new Error(rawOptions.error);

            const options = prepareRegistrationOptions(rawOptions);

            // 2. Invoke the browser's credential creation ceremony
            const credential = await navigator.credentials.create({ publicKey: options });
            if (!credential) throw new Error("Credential creation was cancelled.");

            const serialised = serializeRegistrationCredential(credential);

            // 3. Verify and persist on the server
            const result = await rpc(
                "/attendance/passkey/registration/complete",
                {
                    credential: serialised,
                    device_name: this.state.deviceName || navigator.userAgent.slice(0, 80),
                }
            );
            if (result.error) throw new Error(result.error);

            this.state.phase = "success";
            this.state.message = "Passkey registered successfully!";

            this.notification.add("Passkey registered.", { type: "success" });
            setTimeout(() => this.actionService.doAction({ type: "ir.actions.act_window_close" }), 1500);
        } catch (err) {
            this.state.phase = "error";
            this.state.message = err.message || "Registration failed.";
        }
    }

    onClose() {
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }

    onRetry() {
        this.state.phase = "idle";
        this.state.message = "";
    }
}

registry.category("actions").add("hr_attendance_passkey.register_passkey", PasskeyRegisterWizard);
