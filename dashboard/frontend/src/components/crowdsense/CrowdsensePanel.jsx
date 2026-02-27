/*
 * CrowdsensePanel — Main container for the Crowdsense pilot layer.
 * Contains auth gate, YOLO detector, and region signals.
 */
import { useState, useEffect } from "react";
import AuthForms from "./AuthForms";
import YoloDetector from "./YoloDetector";
import RegionSignals from "./RegionSignals";

export default function CrowdsensePanel() {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);

    // Restore session from localStorage
    useEffect(() => {
        const savedToken = localStorage.getItem("crowdsense_token");
        const savedUser = localStorage.getItem("crowdsense_user");
        if (savedToken && savedUser) {
            try {
                setUser(JSON.parse(savedUser));
                setToken(savedToken);
            } catch { /* bad JSON, ignore */ }
        }
    }, []);

    const handleAuth = (u, t) => {
        setUser(u);
        setToken(t);
    };

    const handleLogout = () => {
        setUser(null);
        setToken(null);
        localStorage.removeItem("crowdsense_token");
        localStorage.removeItem("crowdsense_user");
    };

    // Not logged in → show auth
    if (!user || !token) {
        return <AuthForms onAuth={handleAuth} />;
    }

    return (
        <div className="cs-panel">
            {/* Pilot Badge */}
            <div className="cs-pilot-banner">
                <span className="cs-pilot-icon">CS</span>
                <span>Pilot Deployment — Regional Crowdsensing Layer</span>
                <span className="cs-pilot-tag">RESEARCH PROTOTYPE</span>
            </div>

            {/* User Bar */}
            <div className="cs-user-bar">
                <div className="cs-user-info">
                    <span className="cs-user-dot" />
                    <strong>{user.name}</strong>
                    <span className="cs-user-region">Region {user.region_id} — {user.region_name}</span>
                </div>
                <button className="cs-logout-btn" onClick={handleLogout}>Logout</button>
            </div>

            {/* Main Content */}
            <div className="cs-content-grid">
                <div className="cs-content-left">
                    <YoloDetector user={user} token={token} />
                </div>
                <div className="cs-content-right">
                    <RegionSignals activeRegion={user.region_id} />
                </div>
            </div>

            {/* Privacy & Ethics */}
            <div className="cs-privacy-panel">
                <h5>Privacy Guarantees</h5>
                <ul>
                    <li>No video storage — all processing is on-device</li>
                    <li>Metadata-only ingestion — class labels and confidence scores</li>
                    <li>User-controlled participation — stop anytime</li>
                    <li>Simulation interpretation only — not real-world monitoring</li>
                </ul>
            </div>
        </div>
    );
}
