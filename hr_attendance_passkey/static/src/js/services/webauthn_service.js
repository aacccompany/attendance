/**
 * WebAuthn / Passkey client-side helpers.
 *
 * All conversion utilities between the browser's ArrayBuffer world
 * and the base64url strings that py_webauthn expects on the server.
 */

import { rpc } from "@web/core/network/rpc";

// ---------------------------------------------------------------------------
// Encoding helpers
// ---------------------------------------------------------------------------

/**
 * base64url → Uint8Array
 * Handles both padded and unpadded input, standard or URL-safe chars.
 */
export function base64urlDecode(value) {
    const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
    const binary = atob(padded);
    return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

/** Uint8Array → base64url (no padding) */
export function base64urlEncode(buffer) {
    const bytes = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : buffer;
    let binary = '';
    for (const b of bytes) binary += String.fromCharCode(b);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// ---------------------------------------------------------------------------
// Options preparation
// ---------------------------------------------------------------------------

/**
 * Convert server-side registration options (JSON-parsed) so that
 * ArrayBuffer fields have the correct runtime type before passing to
 * navigator.credentials.create().
 */
export function prepareRegistrationOptions(options) {
    options.challenge = base64urlDecode(options.challenge).buffer;
    options.user.id = base64urlDecode(options.user.id).buffer;
    if (Array.isArray(options.excludeCredentials)) {
        options.excludeCredentials = options.excludeCredentials.map((c) => ({
            ...c,
            id: base64urlDecode(c.id).buffer,
        }));
    }
    return options;
}

/**
 * Convert server-side authentication options so they are ready for
 * navigator.credentials.get().
 */
export function prepareAuthenticationOptions(options) {
    options.challenge = base64urlDecode(options.challenge).buffer;
    if (Array.isArray(options.allowCredentials)) {
        options.allowCredentials = options.allowCredentials.map((c) => ({
            ...c,
            id: base64urlDecode(c.id).buffer,
        }));
    }
    return options;
}

// ---------------------------------------------------------------------------
// Credential serialisation
// ---------------------------------------------------------------------------

/**
 * Serialise a PublicKeyCredential (registration) to a plain JSON-safe object.
 */
export function serializeRegistrationCredential(credential) {
    return {
        id: credential.id,
        rawId: base64urlEncode(credential.rawId),
        type: credential.type,
        response: {
            attestationObject: base64urlEncode(credential.response.attestationObject),
            clientDataJSON: base64urlEncode(credential.response.clientDataJSON),
        },
    };
}

/**
 * Serialise a PublicKeyCredential (authentication assertion) to a plain
 * JSON-safe object that py_webauthn's AuthenticationCredential can parse.
 */
export function serializeAuthenticationCredential(credential) {
    return {
        id: credential.id,
        rawId: base64urlEncode(credential.rawId),
        type: credential.type,
        authenticatorAttachment: credential.authenticatorAttachment || null,
        response: {
            authenticatorData: base64urlEncode(credential.response.authenticatorData),
            clientDataJSON: base64urlEncode(credential.response.clientDataJSON),
            signature: base64urlEncode(credential.response.signature),
            userHandle: credential.response.userHandle
                ? base64urlEncode(credential.response.userHandle)
                : null,
        },
    };
}

// ---------------------------------------------------------------------------
// High-level flow helpers
// ---------------------------------------------------------------------------

/**
 * Run the full WebAuthn authentication ceremony.
 * Calls the backend to get a challenge, invokes navigator.credentials.get,
 * then returns the serialised credential ready to send back to the server.
 *
 * @returns {Promise<object>} serialised credential
 */
export async function runPasskeyAuthentication() {
    // 1. Get challenge from the server
    const rawOptions = await rpc('/attendance/passkey/authentication/begin', {});
    if (rawOptions.error) throw new Error(rawOptions.error);

    const options = prepareAuthenticationOptions(rawOptions);

    // 2. Prompt the user's authenticator
    const credential = await navigator.credentials.get({ publicKey: options });
    if (!credential) throw new Error('No credential returned by the authenticator.');

    return serializeAuthenticationCredential(credential);
}
