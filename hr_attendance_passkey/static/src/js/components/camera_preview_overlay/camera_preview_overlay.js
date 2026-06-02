import { Component, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { runPasskeyAuthentication } from "../../services/webauthn_service";
import { gatherPasskeyContext } from "../../services/passkey_context_service";

/**
 * CameraPreviewOverlay
 *
 * Full-screen modal that:
 *  1. Opens the front-facing camera.
 *  2. Triggers navigator.credentials.get (WebAuthn / Passkey).
 *  3. On success, grabs a JPEG frame from the video, sends both the
 *     serialised credential and the snapshot to the backend.
 */
export class CameraPreviewOverlay extends Component {
    static template = "hr_attendance_passkey.CameraPreviewOverlay";

    static props = {
        /** Called with { action, employee_id, employee_name } on success. */
        onSuccess: Function,
        /** Called when the user dismisses the overlay without authenticating. */
        onClose: Function,
    };

    setup() {
        this.notification = useService("notification");

        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");

        this.state = useState({
            /** idle | starting | ready | authenticating | success | error */
            phase: "idle",
            message: "",
            statusText: "กำลังเตรียมกล้อง…",
            stream: null,
        });

        onMounted(() => this._startCamera());
        onWillUnmount(() => this._stopCamera());
    }

    // ------------------------------------------------------------------
    // Camera helpers
    // ------------------------------------------------------------------

    async _startCamera() {
        this.state.phase = "starting";
        this.state.statusText = "กำลังเปิดกล้อง…";
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
                audio: false,
            });
            this.state.stream = stream;
            const video = this.videoRef.el;
            video.srcObject = stream;
            await video.play();
            this.state.phase = "ready";
            this.state.statusText = "กดปุ่ม \"แสกนหน้า\" หรือ \"เข้างาน (Keypass)\"";
        } catch (err) {
            this.state.phase = "error";
            this.state.message = `เปิดกล้องไม่ได้: ${err.message}`;
            this.state.statusText = "กล้องผิดพลาด";
        }
    }

    _stopCamera() {
        if (this.state.stream) {
            this.state.stream.getTracks().forEach((t) => t.stop());
            this.state.stream = null;
        }
    }

    /**
     * Capture a single frame from the live video and return a data-URI
     * encoded as JPEG at medium quality to keep the payload small.
     */
    _captureJpeg(quality = 0.72) {
        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg", quality);
    }

    // ------------------------------------------------------------------
    // Authentication flow
    // ------------------------------------------------------------------

    /** Auto-start the camera when the user first clicks the overlay CTA. */
    async onStartClick() {
        await this._startCamera();
    }

    async onFaceScanClick() {
        if (this.state.phase !== "ready") return;

        this.state.phase = "authenticating";
        this.state.statusText = "กำลังตรวจจับใบหน้า…";
        this.state.message = "";

        try {
            const snapshot = this._captureJpeg();
            const result = await rpc(
                "/attendance/face/recognize",
                { snapshot }
            );

            if (result.error) throw new Error(result.error);

            this.state.phase = "success";
            this.state.message = result.action === "check_in" ? "เช็คอินสำเร็จ!" : "เช็คเอาท์สำเร็จ!";
            this.state.statusText = result.employee_name;

            setTimeout(() => {
                this._stopCamera();
                this.props.onSuccess(result);
            }, 1800);
        } catch (err) {
            this.state.phase = "error";
            this.state.message = err.message || "แสกนหน้าไม่สำเร็จ";
            this.state.statusText = "กรุณาลองอีกครั้ง";
        }
    }

    async onAuthenticateClick() {
        if (this.state.phase !== "ready") return;

        this.state.phase = "authenticating";
        this.state.statusText = "ทำตามคำแนะนำบนอุปกรณ์ของคุณ…";
        this.state.message = "";

        try {
            // 1. Run the WebAuthn ceremony (challenge fetch + credential.get)
            const context = await gatherPasskeyContext();
            const serialisedCredential = await runPasskeyAuthentication();

            // 2. Capture snapshot immediately after successful assertion
            const snapshot = this._captureJpeg();

            // 3. Complete authentication on the server (creates the attendance record)
            const result = await rpc(
                "/attendance/passkey/authentication/complete",
                { credential: serialisedCredential, snapshot, context }
            );

            if (result.error) throw new Error(result.error);

            this.state.phase = "success";
            this.state.message = result.action === "check_in" ? "เช็คอินสำเร็จ!" : "เช็คเอาท์สำเร็จ!";
            this.state.statusText = result.employee_name;

            // Give the user a moment to see the success frame before closing
            setTimeout(() => {
                this._stopCamera();
                this.props.onSuccess(result);
            }, 1800);
        } catch (err) {
            this.state.phase = "error";
            this.state.message = err.message || "ยืนยันตัวตนไม่สำเร็จ";
            this.state.statusText = "กรุณาลองอีกครั้ง";
        }
    }

    onRetry() {
        this.state.phase = "idle";
        this.state.message = "";
        this.state.statusText = "กำลังเริ่มกล้องใหม่…";
        this._startCamera();
    }

    onClose() {
        this._stopCamera();
        this.props.onClose();
    }
}
