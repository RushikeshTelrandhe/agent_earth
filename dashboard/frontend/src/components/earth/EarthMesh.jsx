/*
 * EarthMesh - Holographic wireframe Earth
 * STABLE: All geometry/material created once via useMemo, never recreated.
 * Only uniforms (color, opacity) update per frame.
 */
import { useRef, useMemo, memo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const DOT_COUNT = 800;
const EARTH_RADIUS = 2;

// Pre-compute dot positions ONCE (module-level, not per-render)
const DOT_POSITIONS = (() => {
    const arr = new Float32Array(DOT_COUNT * 3);
    const gr = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < DOT_COUNT; i++) {
        const theta = 2 * Math.PI * i / gr;
        const phi = Math.acos(1 - 2 * (i + 0.5) / DOT_COUNT);
        arr[i * 3] = EARTH_RADIUS * Math.cos(theta) * Math.sin(phi);
        arr[i * 3 + 1] = EARTH_RADIUS * Math.cos(phi);
        arr[i * 3 + 2] = EARTH_RADIUS * Math.sin(theta) * Math.sin(phi);
    }
    return arr;
})();

function EarthMeshInner({ crisisLevel = 0 }) {
    const groupRef = useRef();
    const atmoRef = useRef();
    const wireMatRef = useRef();
    const dotMatRef = useRef();
    const atmoMatRef = useRef();

    // Compute color once per crisisLevel change (not per frame)
    const baseColor = useMemo(() => {
        const c = new THREE.Color(0x4488ff).lerp(new THREE.Color(0xff3344), Math.min(1, crisisLevel));
        return '#' + c.getHexString();
    }, [crisisLevel]);

    useFrame((state) => {
        if (groupRef.current) groupRef.current.rotation.y += 0.0006;
        if (atmoRef.current) {
            atmoRef.current.material.opacity = 0.08 + 0.02 * Math.sin(state.clock.elapsedTime * 0.6);
        }
    });

    // Update material colors when crisisLevel changes (no new objects)
    useMemo(() => {
        if (wireMatRef.current) wireMatRef.current.color.set(baseColor);
        if (dotMatRef.current) dotMatRef.current.color.set(baseColor);
        if (atmoMatRef.current) atmoMatRef.current.color.set(baseColor);
    }, [baseColor]);

    return (
        <group ref={groupRef}>
            {/* Wireframe */}
            <mesh>
                <icosahedronGeometry args={[EARTH_RADIUS, 2]} />
                <meshBasicMaterial ref={wireMatRef} wireframe color={baseColor} transparent opacity={0.12} />
            </mesh>

            {/* Inner dark core */}
            <mesh>
                <sphereGeometry args={[EARTH_RADIUS * 0.96, 16, 16]} />
                <meshBasicMaterial color="#050a18" transparent opacity={0.9} />
            </mesh>

            {/* Surface dots */}
            <points>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" count={DOT_COUNT} array={DOT_POSITIONS} itemSize={3} />
                </bufferGeometry>
                <pointsMaterial ref={dotMatRef} size={0.015} color={baseColor} transparent opacity={0.45} sizeAttenuation />
            </points>

            {/* Atmosphere */}
            <mesh ref={atmoRef} scale={1.1}>
                <sphereGeometry args={[EARTH_RADIUS, 24, 24]} />
                <meshBasicMaterial ref={atmoMatRef} color={baseColor} transparent opacity={0.08} side={THREE.BackSide} />
            </mesh>
        </group>
    );
}

const EarthMesh = memo(EarthMeshInner);
export default EarthMesh;
