/*
 * RegionNodes - Floating nodes on the globe
 * STABLE: Uses shared geometry/material, updates via refs only.
 * No new Three.js objects created per timestep.
 */
import { useRef, useMemo, memo, useState, useCallback } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';

const EARTH_RADIUS = 2;

const REGION_COORDS = [
    { lat: 40, lon: -100, label: 'N. America' },
    { lat: -15, lon: -60, label: 'S. America' },
    { lat: 50, lon: 15, label: 'Europe' },
    { lat: 5, lon: 25, label: 'Africa' },
    { lat: 35, lon: 105, label: 'Asia' },
    { lat: -25, lon: 135, label: 'Oceania' },
];

const STRATEGY_COLORS = {
    trade: '#22c55e', conserve: '#3b82f6', hoard: '#ef4444',
    invest_growth: '#f59e0b', expand_pop: '#a855f7', none: '#6366f1',
};

function latLonToVec3(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    return new THREE.Vector3(
        -radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta)
    );
}

// Pre-compute positions at module level (never changes)
const NODE_POSITIONS = REGION_COORDS.map(c => {
    const v = latLonToVec3(c.lat, c.lon, EARTH_RADIUS * 1.08);
    return [v.x, v.y, v.z];
});

// Shared geometry - created ONCE for all nodes
const SHARED_SPHERE_GEO = new THREE.SphereGeometry(1, 10, 10);

function RegionNodeInner({ region, index }) {
    const meshRef = useRef();
    const glowRef = useRef();
    const matRef = useRef();
    const glowMatRef = useRef();
    const [hovered, setHovered] = useState(false);

    const position = NODE_POSITIONS[index % NODE_POSITIONS.length];
    const coords = REGION_COORDS[index % REGION_COORDS.length];

    // Cache color object to avoid string->Color conversion each frame
    const colorObj = useMemo(() => new THREE.Color(
        STRATEGY_COLORS[region.last_action] || STRATEGY_COLORS.none
    ), [region.last_action]);

    const colorHex = STRATEGY_COLORS[region.last_action] || STRATEGY_COLORS.none;
    const isCollapsed = region.collapsed;
    const sustainability = region.sustainability || 0;
    const baseScale = isCollapsed ? 0.04 : 0.08 + Math.min(region.population, 500) / 500 * 0.25;

    // Update material color via ref (no new material created)
    useMemo(() => {
        if (matRef.current) matRef.current.color.copy(colorObj);
        if (glowMatRef.current) glowMatRef.current.color.copy(colorObj);
    }, [colorObj]);

    useFrame((state) => {
        if (!meshRef.current) return;
        const pulse = isCollapsed ? 0 : 0.015 * Math.sin(state.clock.elapsedTime * 1.5 + index);
        meshRef.current.scale.setScalar(baseScale + pulse);
        if (matRef.current) matRef.current.opacity = isCollapsed ? 0.15 : 0.85;
        if (glowRef.current) {
            glowRef.current.scale.setScalar((baseScale + pulse) * 2.5);
            if (glowMatRef.current) glowMatRef.current.opacity = isCollapsed ? 0.03 : 0.15 + sustainability * 0.3;
        }
    });

    const onOver = useCallback(() => setHovered(true), []);
    const onOut = useCallback(() => setHovered(false), []);

    return (
        <group position={position}>
            <mesh ref={meshRef} geometry={SHARED_SPHERE_GEO} onPointerOver={onOver} onPointerOut={onOut}>
                <meshBasicMaterial ref={matRef} color={colorHex} transparent opacity={0.85} />
            </mesh>

            <mesh ref={glowRef} geometry={SHARED_SPHERE_GEO}>
                <meshBasicMaterial ref={glowMatRef} color={colorHex} transparent opacity={0.2} side={THREE.BackSide} />
            </mesh>

            {hovered && (
                <Html distanceFactor={8} style={{ pointerEvents: 'none' }}>
                    <div style={{
                        background: 'rgba(10,15,30,0.92)', border: '1px solid rgba(99,102,241,0.4)',
                        borderRadius: 10, padding: '8px 12px', color: '#e2e8f0', fontSize: 11,
                        fontFamily: 'Inter,sans-serif', minWidth: 140,
                        boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
                    }}>
                        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
                            {isCollapsed ? '💀' : '🌐'} R{region.id} <span style={{ opacity: 0.5 }}>({coords.label})</span>
                        </div>
                        <div>Pop: <b>{region.population}</b> | <b style={{ color: colorHex }}>{region.last_action}</b></div>
                        <div>Sust: {(sustainability * 100).toFixed(0)}%</div>
                        <div style={{ fontSize: 10, color: '#64748b' }}>
                            W:{region.water} F:{region.food} E:{region.energy} L:{region.land}
                        </div>
                    </div>
                </Html>
            )}
        </group>
    );
}

const RegionNode = memo(RegionNodeInner);

function RegionNodesInner({ regions = [] }) {
    return (
        <group>
            {regions.map((r, i) => <RegionNode key={r.id} region={r} index={i} />)}
        </group>
    );
}

const RegionNodes = memo(RegionNodesInner);
export default RegionNodes;
export { REGION_COORDS, latLonToVec3, EARTH_RADIUS };
