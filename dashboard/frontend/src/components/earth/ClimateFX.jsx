/*
 * ClimateFX - Visual climate effects on the globe
 * STABLE: Pre-computed positions, shared geometry, React.memo, max 3 effects.
 */
import { useRef, useMemo, memo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { REGION_COORDS, latLonToVec3, EARTH_RADIUS } from './RegionNodes';

// Pre-compute all possible positions at module level
const FX_POSITIONS = REGION_COORDS.map(c => {
    const v = latLonToVec3(c.lat, c.lon, EARTH_RADIUS * 1.1);
    return [v.x, v.y, v.z];
});

// Shared geometries
const RING_GEO = new THREE.RingGeometry(0.6, 0.8, 16);
const SMALL_SPHERE_GEO = new THREE.SphereGeometry(0.12, 6, 6);
const OCTA_GEO = new THREE.OctahedronGeometry(0.1, 0);

const FloodRipple = memo(function FloodRipple({ regionId }) {
    const ref = useRef();
    const pos = FX_POSITIONS[regionId % FX_POSITIONS.length];

    useFrame((state) => {
        if (!ref.current) return;
        const t = (state.clock.elapsedTime * 0.8) % 2;
        ref.current.scale.setScalar(0.1 + t * 0.25);
        ref.current.material.opacity = Math.max(0, 0.4 - t * 0.2);
    });

    return (
        <mesh ref={ref} position={pos} geometry={RING_GEO}>
            <meshBasicMaterial color="#3b82f6" transparent opacity={0.4} side={THREE.DoubleSide} />
        </mesh>
    );
});

const DroughtFlicker = memo(function DroughtFlicker({ regionId }) {
    const ref = useRef();
    const pos = FX_POSITIONS[regionId % FX_POSITIONS.length];

    useFrame((state) => {
        if (!ref.current) return;
        ref.current.material.opacity = 0.15 + 0.2 * Math.abs(Math.sin(state.clock.elapsedTime * 5 + regionId));
    });

    return (
        <mesh ref={ref} position={pos} geometry={SMALL_SPHERE_GEO}>
            <meshBasicMaterial color="#f59e0b" transparent opacity={0.2} />
        </mesh>
    );
});

const EnergyCrisis = memo(function EnergyCrisis({ regionId }) {
    const ref = useRef();
    const pos = FX_POSITIONS[regionId % FX_POSITIONS.length];

    useFrame((state) => {
        if (!ref.current) return;
        ref.current.material.opacity = 0.08 + 0.1 * Math.sin(state.clock.elapsedTime * 2);
    });

    return (
        <mesh ref={ref} position={pos} geometry={OCTA_GEO}>
            <meshBasicMaterial color="#ef4444" transparent opacity={0.15} wireframe />
        </mesh>
    );
});

const MAX_FX = 3;

function ClimateFXInner({ events = [], regions = [] }) {
    // Memoize the effect list to prevent recreation each render
    const effects = useMemo(() => {
        const result = [];
        const seen = new Set();
        for (const evt of events) {
            if (result.length >= MAX_FX) break;
            for (let i = 0; i < regions.length; i++) {
                if (regions[i].collapsed || seen.has(evt + i)) continue;
                seen.add(evt + i);
                if (evt === 'flood') { result.push(<FloodRipple key={`f${i}`} regionId={i} />); break; }
                if (evt === 'drought') { result.push(<DroughtFlicker key={`d${i}`} regionId={i} />); break; }
                if (evt === 'energy_crisis') { result.push(<EnergyCrisis key={`e${i}`} regionId={i} />); break; }
            }
        }
        return result;
    }, [events, regions]);

    return <group>{effects}</group>;
}

const ClimateFX = memo(ClimateFXInner);
export default ClimateFX;
