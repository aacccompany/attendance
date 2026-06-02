/** @odoo-module */

const SESSION_STORAGE_KEY = "hr_attendance_passkey_session_id";

function generateSessionId() {
    if (window.crypto?.randomUUID) {
        return window.crypto.randomUUID();
    }
    const array = new Uint32Array(4);
    window.crypto?.getRandomValues?.(array);
    return Array.from(array, (num) => num.toString(16).padStart(8, "0")).join("-") || String(Date.now());
}

function ensureSessionId() {
    try {
        const storage = window.localStorage;
        if (!storage) {
            return generateSessionId();
        }
        let sessionId = storage.getItem(SESSION_STORAGE_KEY);
        if (!sessionId) {
            sessionId = generateSessionId();
            storage.setItem(SESSION_STORAGE_KEY, sessionId);
        }
        return sessionId;
    } catch (_err) {
        return generateSessionId();
    }
}

async function getHighEntropyUAData() {
    const uaData = navigator.userAgentData;
    if (uaData && uaData.getHighEntropyValues) {
        try {
            return await uaData.getHighEntropyValues([
                "platform",
                "platformVersion",
                "architecture",
                "model",
                "uaFullVersion",
            ]);
        } catch (err) {
            console.warn("Unable to retrieve high entropy UA data", err);
        }
    }
    return null;
}

function normalizeText(value) {
    return value && value.trim() ? value.trim() : null;
}

function detectBrowser(userAgent, uaHighEntropy) {
    const brands = navigator.userAgentData?.brands || [];
    if (uaHighEntropy?.uaFullVersion) {
        const brand = brands.find((b) => /Chrome|Chromium|Microsoft Edge|Opera/.test(b.brand));
        if (brand) {
            return { name: normalizeText(brand.brand), version: normalizeText(uaHighEntropy.uaFullVersion) };
        }
    }

    const matchers = [
        { regex: /(Edg)\/([\d\.]+)/, name: "Microsoft Edge" },
        { regex: /(OPR)\/([\d\.]+)/, name: "Opera" },
        { regex: /(Chrome)\/([\d\.]+)/, name: "Chrome" },
        { regex: /(Version)\/([\d\.]+).*Safari/, name: "Safari" },
        { regex: /(Firefox)\/([\d\.]+)/, name: "Firefox" },
    ];
    for (const matcher of matchers) {
        const res = matcher.regex.exec(userAgent);
        if (res) {
            return { name: matcher.name, version: normalizeText(res[2]) };
        }
    }
    return {
        name: normalizeText(brands[0]?.brand),
        version: normalizeText(brands[0]?.version),
    };
}

function detectOS(userAgent, uaHighEntropy) {
    const platform = uaHighEntropy?.platform || navigator.userAgentData?.platform;
    const platformVersion = uaHighEntropy?.platformVersion;
    if (platform) {
        return { name: normalizeText(platform), version: normalizeText(platformVersion) };
    }

    const mapping = [
        { regex: /Windows NT 10\.0/, name: "Windows", version: "10" },
        { regex: /Windows NT 11\.0/, name: "Windows", version: "11" },
        { regex: /Windows NT 6\.3/, name: "Windows", version: "8.1" },
        { regex: /Windows NT 6\.2/, name: "Windows", version: "8" },
        { regex: /Windows NT 6\.1/, name: "Windows", version: "7" },
        { regex: /Android ([\d_\.]+)/, name: "Android" },
        { regex: /iPhone OS ([\d_]+)/, name: "iOS" },
        { regex: /iPad; CPU OS ([\d_]+)/, name: "iPadOS" },
        { regex: /Mac OS X ([\d_]+)/, name: "macOS" },
        { regex: /Linux/, name: "Linux" },
    ];
    for (const item of mapping) {
        const match = item.regex.exec(userAgent);
        if (match) {
            return {
                name: item.name,
                version: normalizeText(match[1]?.replace(/_/g, ".") || item.version),
            };
        }
    }
    return { name: null, version: null };
}

function detectDevice(userAgent, uaHighEntropy) {
    const typeRaw = navigator.userAgentData?.mobile
        ? "mobile"
        : uaHighEntropy?.type ||
          (/Tablet|iPad/i.test(userAgent)
              ? "tablet"
              : /Mobile|Android|iPhone/i.test(userAgent)
              ? "mobile"
              : "desktop");

    const type = typeRaw ? typeRaw.charAt(0).toUpperCase() + typeRaw.slice(1) : null;

    const nameRaw = uaHighEntropy?.model || (() => {
        const match = userAgent.match(/(iPhone\s?(\d+\sPro(Max)?)?|iPad|Pixel\s\d+|Galaxy\s[A-Z0-9]+|MacBook\s(?:Air|Pro)|SM-[A-Z0-9]+|Windows Phone)/i);
        if (match) {
            return match[0];
        }
        if (/Macintosh/.test(userAgent)) {
            return "Mac";
        }
        if (/Windows/.test(userAgent)) {
            return "Windows PC";
        }
        return null;
    })();

    return { name: normalizeText(nameRaw), type };
}

function getPosition() {
    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            return resolve({ latitude: null, longitude: null });
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                resolve({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                });
            },
            (_err) => {
                resolve({ latitude: null, longitude: null });
            },
            { enableHighAccuracy: false, timeout: 5000, maximumAge: 60000 }
        );
    });
}

export async function gatherPasskeyContext() {
    const userAgent = navigator.userAgent || "";
    const uaHighEntropy = await getHighEntropyUAData();
    const location = await getPosition();
    const sessionId = ensureSessionId();
    const browser = detectBrowser(userAgent, uaHighEntropy);
    const operatingSystem = detectOS(userAgent, uaHighEntropy);
    const device = detectDevice(userAgent, uaHighEntropy);

    return {
        user_agent: userAgent,
        session_id: sessionId,
        device,
        browser,
        operating_system: operatingSystem,
        location,
    };
}
