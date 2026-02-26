/*
 * GlobeScene - Master 3D scene controller
 * 
 * STABILITY ARCHITECTURE:
 * - Singleton WebGLRenderer via rendererSingleton.js (prevents context leaks)
 * - Canvas is NEVER unmounted on tab switch (parent uses display:none)
 * - SafeBloom uses useFrame readiness check instead of setTimeout
 * - RendererCleanup disposes scene objects only (not the renderer itself)
 * - Context loss/restore handlers with proper cleanup
 * - AnimationLoop: 24 FPS cap with single RAF
 * - Adaptive quality: auto-reduces effects when steps > threshold
 * - Debug overlay with draw call + memory tracking
 * - Trade aggregation throttled to every 5 slider steps
 * - React.memo on SceneContent to prevent re-renders from unrelated state
 * - HMR cleanup via rendererSingleton's import.meta.hot.dispose
 */
import { Suspense, useMemo, useRef, useEffect, useState, useCallback, memo } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';

import EarthMesh from './EarthMesh';
import RegionNodes from './RegionNodes';
import TradeArcs from './TradeArcs';
import ClimateFX from './ClimateFX';
import { disposeRenderer } from './rendererSingleton';

/* ═══════════════════════════════════════════ */
/*  SAFE BLOOM - useFrame-based readiness     */
/* ═══════════════════════════════════════════ */
function SafeBloom({ lowQuality }) {
    const { gl } = useThree();
    const [ready, setReady] = useState(false);
    const checkedRef = useRef(false);

    // Check renderer readiness on the next actual frame (not a timer)
    useFrame(() => {
        if (checkedRef.current || ready) return;
        try {
            const ctx = gl?.getContext();
            if (ctx && !ctx.isContextLost()) {
                checkedRef.current = true;
                setReady(true);
            }
        } catch {
            // Not ready yet — will retry next frame
        }
    });

    if (!ready) return null;

    return (
        <EffectComposer multisampling={0} enabled={!lowQuality}>
            <Bloom
                luminanceThreshold={0.4}
                luminanceSmoothing={0.95}
                intensity={lowQuality ? 0.3 : 0.6}
                mipmapBlur
                levels={lowQuality ? 2 : 4}
            />
        </EffectComposer>
    );
}

/* ═══════════════════════════════════════════ */
/*  CLEANUP - disposes scene objects on       */
/*  unmount (NOT the renderer — singleton     */
/*  manages that)                             */
/* ═══════════════════════════════════════════ */
function SceneCleanup() {
    const { scene } = useThree();
    useEffect(() => {
        return () => {
            try {
                if (scene) {
                    scene.traverse((obj) => {
                        if (obj.geometry && !obj.geometry._shared) obj.geometry.dispose();
                        if (obj.material) {
                            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
                            mats.forEach(m => {
                                if (m.map) m.map.dispose();
                                m.dispose();
                            });
                        }
                    });
                }
            } catch (e) {
                console.warn('[SceneCleanup]', e.message);
            }
        };
    }, [scene]);
    return null;
}

/* ═══════════════════════════════════════════ */
/*  ANIMATION LOOP - capped at 24 FPS        */
/* ═══════════════════════════════════════════ */
function AnimationLoop() {
    const { invalidate, gl } = useThree();
    useEffect(() => {
        let id;
        let last = 0;
        const interval = 1000 / 24;
        const tick = (now) => {
            id = requestAnimationFrame(tick);
            if (now - last >= interval) {
                last = now;
                // Guard: skip if context is lost
                try {
                    const ctx = gl?.getContext();
                    if (ctx && !ctx.isContextLost()) {
                        invalidate();
                    }
                } catch { /* context lost, skip */ }
            }
        };
        id = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(id);
    }, [invalidate, gl]);
    return null;
}

/* ═══════════════════════════════════════════ */
/*  DEBUG OVERLAY - tracks draw calls & mesh  */
/* ═══════════════════════════════════════════ */
function DebugTracker({ onStats }) {
    const { gl } = useThree();
    const frameCount = useRef(0);

    useFrame(() => {
        frameCount.current++;
        // Report every 60 frames (~2.5s at 24fps)
        if (frameCount.current % 60 === 0 && onStats) {
            const info = gl.info;
            onStats({
                drawCalls: info.render?.calls || 0,
                triangles: info.render?.triangles || 0,
                geometries: info.memory?.geometries || 0,
                textures: info.memory?.textures || 0,
            });
        }
    });
    return null;
}

/* ═══════════════════════════════════════════ */
/*  SCENE - memoized, only updates via props  */
/* ═══════════════════════════════════════════ */
const SceneContent = memo(function SceneContent({ regions, trades, events, crisisLevel, lowQuality, safeMode, onStats }) {
    return (
        <>
            <ambientLight intensity={0.12} />
            <pointLight position={[10, 10, 10]} intensity={0.2} color="#4488ff" />

            {!lowQuality && !safeMode && <Stars radius={60} depth={30} count={1000} factor={2.5} saturation={0} fade speed={0.2} />}

            <EarthMesh crisisLevel={crisisLevel} />
            <RegionNodes regions={regions} />
            <TradeArcs trades={trades} />
            {!lowQuality && !safeMode && <ClimateFX events={events} regions={regions} />}

            {!safeMode && <SafeBloom lowQuality={lowQuality} />}
            <SceneCleanup />
            <AnimationLoop />
            <DebugTracker onStats={onStats} />

            <OrbitControls
                enablePan={false}
                enableZoom
                enableRotate
                autoRotate
                autoRotateSpeed={0.25}
                minDistance={3.5}
                maxDistance={10}
                dampingFactor={0.05}
                enableDamping
            />
        </>
    );
});

/* ═══════════════════════════════════════════ */
/*  GLOBE SCENE - main export                 */
/* ═══════════════════════════════════════════ */
export default function GlobeScene({ stepData = {}, allSteps = [], replayStep = 0, safeMode = false }) {
    const regions = stepData?.regions || [];
    const events = stepData?.events || [];
    const collapsedCount = regions.filter(r => r.collapsed).length;
    const crisisLevel = regions.length > 0 ? collapsedCount / regions.length : 0;

    const [contextLost, setContextLost] = useState(false);
    const [debugStats, setDebugStats] = useState(null);
    const canvasContainerRef = useRef(null);
    const contextHandlersRef = useRef({ onLost: null, onRestored: null });

    // Adaptive quality: lower quality if > 200 steps of data
    const lowQuality = safeMode || allSteps.length > 200;

    // Throttle trade aggregation: recalc every 5 slider steps
    const throttledStep = Math.floor(replayStep / 5);
    const aggregatedTrades = useMemo(() => {
        if (!allSteps.length) return [];
        const window = Math.min(8, allSteps.length);
        const idx = Math.min(replayStep, allSteps.length - 1);
        const start = Math.max(0, idx - window);
        const end = idx + 1;
        const all = [];
        for (let s = start; s < end; s++) {
            const t = allSteps[s]?.trades;
            if (t) all.push(...t);
        }
        return all;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [allSteps, throttledStep]);

    // Context loss/restore handlers — registered once on canvas mount
    const onCreated = useCallback(({ gl }) => {
        const canvas = gl.domElement;

        // Cleanup any previous listeners (safety)
        if (contextHandlersRef.current.onLost) {
            canvas.removeEventListener('webglcontextlost', contextHandlersRef.current.onLost);
            canvas.removeEventListener('webglcontextrestored', contextHandlersRef.current.onRestored);
        }

        const onLost = (e) => {
            e.preventDefault();
            setContextLost(true);
            console.warn('[GlobeScene] WebGL context lost');
        };
        const onRestored = () => {
            setContextLost(false);
            console.log('[GlobeScene] WebGL context restored');
        };

        canvas.addEventListener('webglcontextlost', onLost);
        canvas.addEventListener('webglcontextrestored', onRestored);
        contextHandlersRef.current = { onLost, onRestored };

        gl.setPixelRatio(Math.min(window.devicePixelRatio, safeMode ? 1 : 1.5));
    }, [safeMode]);

    // Cleanup context listeners on unmount
    useEffect(() => {
        return () => {
            const container = canvasContainerRef.current;
            if (container) {
                const canvas = container.querySelector('canvas');
                if (canvas && contextHandlersRef.current.onLost) {
                    canvas.removeEventListener('webglcontextlost', contextHandlersRef.current.onLost);
                    canvas.removeEventListener('webglcontextrestored', contextHandlersRef.current.onRestored);
                }
            }
        };
    }, []);

    const onDebugStats = useCallback((stats) => setDebugStats(stats), []);

    return (
        <div ref={canvasContainerRef} style={{
            width: '100%', height: '600px',
            borderRadius: 20, overflow: 'hidden',
            background: '#030712', position: 'relative',
        }}>
            {/* Context lost fallback */}
            {contextLost && (
                <div style={{
                    position: 'absolute', inset: 0, zIndex: 10,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
                    background: 'rgba(3,7,18,0.95)', color: '#94a3b8',
                    fontFamily: 'Inter,sans-serif', fontSize: 14,
                }}>
                    <div style={{ fontSize: 32, marginBottom: 12 }}>⚡</div>
                    <div>Performance mode — WebGL context recovering</div>
                    <div style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>Auto-restoring in a moment...</div>
                </div>
            )}

            <Canvas
                camera={{ position: [0, 1.5, 6], fov: 45 }}
                dpr={[1, safeMode ? 1 : (lowQuality ? 1 : 1.5)]}
                gl={{
                    antialias: !lowQuality && !safeMode,
                    alpha: false,
                    powerPreference: safeMode ? 'low-power' : 'default',
                    failIfMajorPerformanceCaveat: false,
                    preserveDrawingBuffer: false,
                    stencil: false,
                    depth: true,
                }}
                onCreated={onCreated}
                frameloop="demand"
            >
                <Suspense fallback={null}>
                    <SceneContent
                        regions={regions}
                        trades={aggregatedTrades}
                        events={events}
                        crisisLevel={crisisLevel}
                        lowQuality={lowQuality}
                        safeMode={safeMode}
                        onStats={onDebugStats}
                    />
                </Suspense>
            </Canvas>

            {/* ── Step indicator ── */}
            <div style={{
                position: 'absolute', top: 14, left: 18,
                color: 'rgba(148,163,184,0.6)', fontSize: 11,
                fontFamily: 'Inter,sans-serif', zIndex: 2,
            }}>
                Step {stepData?.step || replayStep} | {regions.filter(r => !r.collapsed).length}/{regions.length} active
                {lowQuality && <span style={{ color: '#f59e0b', marginLeft: 8 }}>⚡ perf mode</span>}
                {safeMode && <span style={{ color: '#22c55e', marginLeft: 8 }}>🛡️ safe</span>}
            </div>

            {/* ── Debug info ── */}
            {debugStats && (
                <div style={{
                    position: 'absolute', top: 14, right: 18,
                    color: 'rgba(100,116,139,0.5)', fontSize: 9,
                    fontFamily: 'monospace', zIndex: 2,
                }}>
                    draw:{debugStats.drawCalls} tri:{debugStats.triangles} geo:{debugStats.geometries} tex:{debugStats.textures}
                </div>
            )}

            {/* ── Legend ── */}
            <div style={{
                position: 'absolute', bottom: 14, right: 18,
                display: 'flex', gap: 10, fontSize: 9,
                fontFamily: 'Inter,sans-serif',
                color: 'rgba(148,163,184,0.6)', zIndex: 2,
            }}>
                <span><span style={{ color: '#22c55e' }}>●</span> Trade</span>
                <span><span style={{ color: '#ef4444' }}>●</span> Hoard</span>
                <span><span style={{ color: '#3b82f6' }}>●</span> Conserve</span>
                <span><span style={{ color: '#f59e0b' }}>●</span> Invest</span>
            </div>
        </div>
    );
}

/*
 * HMR: when GlobeScene module is hot-replaced, dispose the renderer
 * so we don't leak WebGL contexts during development.
 */
if (import.meta.hot) {
    import.meta.hot.dispose(() => {
        console.log('[GlobeScene] HMR dispose — cleaning up renderer');
        disposeRenderer();
    });
}
