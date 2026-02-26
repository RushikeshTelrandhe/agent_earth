/*
 * YoloDetector — Browser-side COCO-SSD object detection
 * Privacy-first: frames never leave the browser.
 * Only detection metadata (class + confidence) is transmitted.
 */
import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://localhost:5000";

// Lazy-load TF.js + COCO-SSD
let cocoPromise = null;
async function loadModel() {
    if (!cocoPromise) {
        cocoPromise = (async () => {
            const tf = await import("@tensorflow/tfjs");
            const cocoSsd = await import("@tensorflow-models/coco-ssd");
            await tf.ready();
            return cocoSsd.load();
        })();
    }
    return cocoPromise;
}

export default function YoloDetector({ user, token }) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const [model, setModel] = useState(null);
    const [detections, setDetections] = useState([]);
    const [fps, setFps] = useState(0);
    const [active, setActive] = useState(false);
    const [status, setStatus] = useState("idle"); // idle | loading | running | error
    const [sent, setSent] = useState(0);
    const frameCount = useRef(0);
    const lastTime = useRef(Date.now());
    const rafId = useRef(null);

    const startCamera = useCallback(async () => {
        setStatus("loading");
        try {
            const mdl = await loadModel();
            setModel(mdl);

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: "environment" },
            });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();
            }
            setActive(true);
            setStatus("running");
        } catch (err) {
            console.error("Camera/Model error:", err);
            setStatus("error");
        }
    }, []);

    const stopCamera = useCallback(() => {
        setActive(false);
        setStatus("idle");
        if (rafId.current) cancelAnimationFrame(rafId.current);
        if (videoRef.current?.srcObject) {
            videoRef.current.srcObject.getTracks().forEach(t => t.stop());
            videoRef.current.srcObject = null;
        }
    }, []);

    // Detection loop
    useEffect(() => {
        if (!active || !model || !videoRef.current) return;

        let running = true;

        const detect = async () => {
            if (!running || !videoRef.current) return;

            try {
                const results = await model.detect(videoRef.current);
                setDetections(results);

                // Draw bounding boxes
                const canvas = canvasRef.current;
                if (canvas && videoRef.current) {
                    canvas.width = videoRef.current.videoWidth || 640;
                    canvas.height = videoRef.current.videoHeight || 480;
                    const ctx = canvas.getContext("2d");
                    ctx.clearRect(0, 0, canvas.width, canvas.height);

                    results.forEach(det => {
                        const [x, y, w, h] = det.bbox;
                        ctx.strokeStyle = "#7B5CFF";
                        ctx.lineWidth = 2;
                        ctx.strokeRect(x, y, w, h);

                        ctx.fillStyle = "rgba(123, 92, 255, 0.75)";
                        const label = `${det.class} ${(det.score * 100).toFixed(0)}%`;
                        const tw = ctx.measureText(label).width;
                        ctx.fillRect(x, y - 18, tw + 8, 18);
                        ctx.fillStyle = "#fff";
                        ctx.font = "12px Inter, sans-serif";
                        ctx.fillText(label, x + 4, y - 4);
                    });
                }

                // FPS
                frameCount.current++;
                const now = Date.now();
                if (now - lastTime.current >= 1000) {
                    setFps(frameCount.current);
                    frameCount.current = 0;
                    lastTime.current = now;

                    // Send metadata to API (1 per second max)
                    if (results.length > 0 && token) {
                        try {
                            await fetch(`${API}/api/crowdsense/detections`, {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                    Authorization: `Bearer ${token}`,
                                },
                                body: JSON.stringify({
                                    detected_objects: results.map(r => ({
                                        class: r.class,
                                        confidence: r.score,
                                    })),
                                    frame_object_count: results.length,
                                }),
                            });
                            setSent(s => s + 1);
                        } catch { /* silently fail */ }
                    }
                }
            } catch { /* skip frame */ }

            if (running) rafId.current = requestAnimationFrame(detect);
        };

        detect();
        return () => { running = false; if (rafId.current) cancelAnimationFrame(rafId.current); };
    }, [active, model, token]);

    // Cleanup on unmount
    useEffect(() => () => stopCamera(), [stopCamera]);

    const classCounts = {};
    detections.forEach(d => { classCounts[d.class] = (classCounts[d.class] || 0) + 1; });

    return (
        <div className="cs-detector">
            <div className="cs-detector-header">
                <h4>
                    <span className="cs-live-dot" style={{ background: active ? "#22c55e" : "#5A6380" }} />
                    Live Detection
                </h4>
                <div className="cs-detector-meta">
                    {active && <span className="cs-fps">{fps} FPS</span>}
                    <span className="cs-sent">{sent} sent</span>
                    <button
                        className={`cs-toggle-btn ${active ? "active" : ""}`}
                        onClick={active ? stopCamera : startCamera}
                    >
                        {status === "loading" ? "Loading..." : active ? "Stop" : "Start Camera"}
                    </button>
                </div>
            </div>

            <div className="cs-detector-viewport">
                <video ref={videoRef} playsInline muted style={{ width: "100%", borderRadius: 12, display: active ? "block" : "none" }} />
                <canvas ref={canvasRef} className="cs-detector-canvas" style={{ display: active ? "block" : "none" }} />

                {!active && (
                    <div className="cs-detector-placeholder">
                        <div className="cs-detector-icon">📡</div>
                        <p>Click <strong>Start Camera</strong> to begin detection</p>
                        <p className="cs-privacy-note">Privacy-first: Only detection summaries are transmitted. No video storage.</p>
                    </div>
                )}
            </div>

            {active && Object.keys(classCounts).length > 0 && (
                <div className="cs-class-list">
                    {Object.entries(classCounts).map(([cls, count]) => (
                        <span key={cls} className="cs-class-tag">
                            {cls} <strong>×{count}</strong>
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}
