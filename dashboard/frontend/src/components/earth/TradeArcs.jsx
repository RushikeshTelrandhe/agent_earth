/*
 * TradeArcs - Curved arcs between trading regions
 * STABLE: Max 6 arcs, shared geometry, pooled particles, ref-only updates.
 */
import { useRef, useMemo, memo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { REGION_COORDS, latLonToVec3, EARTH_RADIUS } from './RegionNodes';

const RES_COLORS = { water: '#3b82f6', food: '#22c55e', energy: '#f59e0b', land: '#a855f7' };
const MAX_ARCS = 6;
const ARC_POINTS = 20;

// Shared particle geometry
const PARTICLE_GEO = new THREE.SphereGeometry(0.022, 4, 4);

// Pre-compute arc curve and buffer once per arc config
function buildArc(from, to, volume) {
    const fc = REGION_COORDS[from % REGION_COORDS.length];
    const tc = REGION_COORDS[to % REGION_COORDS.length];
    const start = latLonToVec3(fc.lat, fc.lon, EARTH_RADIUS * 1.08);
    const end = latLonToVec3(tc.lat, tc.lon, EARTH_RADIUS * 1.08);
    const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)
        .normalize().multiplyScalar(EARTH_RADIUS * 1.35 + Math.min(volume, 15) * 0.008);
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    const pts = curve.getPoints(ARC_POINTS);
    const arr = new Float32Array(pts.length * 3);
    for (let i = 0; i < pts.length; i++) {
        arr[i * 3] = pts[i].x; arr[i * 3 + 1] = pts[i].y; arr[i * 3 + 2] = pts[i].z;
    }
    return { positions: arr, curve };
}

function TradeArcInner({ from, to, volume, resource }) {
    const lineRef = useRef();
    const particleRef = useRef();
    const tempVec = useMemo(() => new THREE.Vector3(), []);

    const { positions, curve, color } = useMemo(() => {
        const arc = buildArc(from, to, volume);
        return { ...arc, color: RES_COLORS[resource] || '#6366f1' };
    }, [from, to, volume, resource]);

    const offset = useMemo(() => (from * 0.23 + to * 0.17) % 1, [from, to]);

    useFrame((state) => {
        if (lineRef.current?.material) lineRef.current.material.dashOffset -= 0.01;
        if (particleRef.current) {
            const t = ((state.clock.elapsedTime * 0.2 + offset) % 1);
            curve.getPoint(t, tempVec);
            particleRef.current.position.copy(tempVec);
        }
    });

    return (
        <group>
            <line ref={lineRef}>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
                </bufferGeometry>
                <lineDashedMaterial color={color} transparent opacity={0.5} dashSize={0.1} gapSize={0.05} linewidth={1} />
            </line>
            <mesh ref={particleRef} geometry={PARTICLE_GEO}>
                <meshBasicMaterial color={color} transparent opacity={0.8} />
            </mesh>
        </group>
    );
}

const TradeArc = memo(TradeArcInner);

function TradeArcsInner({ trades = [] }) {
    const arcData = useMemo(() => {
        const map = {};
        for (const t of trades) {
            if (t.accepted === false) continue;
            const key = `${t.from}-${t.to}`;
            if (!map[key]) map[key] = { from: t.from, to: t.to, volume: 0, resource: t.resource };
            map[key].volume += t.amount || 0;
        }
        return Object.values(map).sort((a, b) => b.volume - a.volume).slice(0, MAX_ARCS);
    }, [trades]);

    return (
        <group>
            {arcData.map(a => <TradeArc key={`${a.from}-${a.to}`} {...a} />)}
        </group>
    );
}

const TradeArcs = memo(TradeArcsInner);
export default TradeArcs;
