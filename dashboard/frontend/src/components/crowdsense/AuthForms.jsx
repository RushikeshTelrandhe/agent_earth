/*
 * AuthForms — Login/Signup for Crowdsense
 * Matches Agent Earth dark neon aesthetic.
 */
import { useState } from "react";

const API = "http://localhost:5000";

const REGIONS = [
    { id: 0, name: "Region 0" },
    { id: 1, name: "Region 1" },
    { id: 2, name: "Region 2" },
    { id: 3, name: "Region 3" },
    { id: 4, name: "Region 4" },
    { id: 5, name: "Region 5" },
];

export default function AuthForms({ onAuth }) {
    const [mode, setMode] = useState("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [regionId, setRegionId] = useState(0);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const url = mode === "login" ? `${API}/api/crowdsense/login` : `${API}/api/crowdsense/signup`;
            const body = mode === "login"
                ? { email, password }
                : { name, email, password, region_id: regionId };
            const resp = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const data = await resp.json();
            if (data.error) {
                setError(data.error);
            } else {
                localStorage.setItem("crowdsense_token", data.token);
                localStorage.setItem("crowdsense_user", JSON.stringify(data.user));
                onAuth(data.user, data.token);
            }
        } catch {
            setError("Connection failed. Is the backend running?");
        }
        setLoading(false);
    };

    return (
        <div className="cs-auth-container">
            <div className="cs-auth-card">
                <div className="cs-auth-header">
                    <span className="cs-auth-icon">CS</span>
                    <h3>Agent Earth Crowdsense</h3>
                    <span className="cs-pilot-badge">Pilot Program</span>
                </div>

                <div className="cs-auth-tabs">
                    <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Login</button>
                    <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>Sign Up</button>
                </div>

                <form onSubmit={handleSubmit} className="cs-auth-form">
                    {mode === "signup" && (
                        <input type="text" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} required />
                    )}
                    <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
                    <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />

                    {mode === "signup" && (
                        <div className="cs-region-select">
                            <label>Assigned Region</label>
                            <div className="cs-region-grid">
                                {REGIONS.map(r => (
                                    <button
                                        key={r.id}
                                        type="button"
                                        className={regionId === r.id ? "active" : ""}
                                        onClick={() => setRegionId(r.id)}
                                    >
                                        {r.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {error && <div className="cs-auth-error">{error}</div>}

                    <button type="submit" className="cs-auth-submit" disabled={loading}>
                        {loading ? "Processing..." : mode === "login" ? "Log In" : "Create Account"}
                    </button>
                </form>

                <div className="cs-auth-privacy">
                    🔒 Privacy-first: Only detection metadata is transmitted. No video storage.
                </div>
            </div>
        </div>
    );
}
