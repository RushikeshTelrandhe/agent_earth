/*
 * rendererSingleton — ensures only ONE WebGLRenderer exists globally.
 *
 * Why: React re-renders, Vite HMR, and tab switches can all cause
 * <Canvas> to remount, which normally creates a new WebGLRenderer
 * each time. Browsers cap active WebGL contexts at ~8-16, so leaked
 * renderers cause black screens.
 *
 * This module creates one renderer and reuses it across mounts.
 * On HMR disposal it properly tears down the old context.
 */
import * as THREE from 'three';

let _renderer = null;
let _mountCount = 0;

/**
 * Get or create the singleton WebGLRenderer.
 * @param {HTMLCanvasElement} canvas - The canvas element to bind to.
 * @param {object} opts - Extra WebGLRenderer options.
 * @returns {THREE.WebGLRenderer}
 */
export function getOrCreateRenderer(canvas, opts = {}) {
    if (_renderer) {
        // Re-bind to the new canvas if the old one was removed from DOM
        if (_renderer.domElement !== canvas) {
            // The old renderer's canvas is stale — dispose and recreate
            try { _renderer.dispose(); } catch { /* ok */ }
            _renderer = null;
        } else {
            _mountCount++;
            return _renderer;
        }
    }

    _renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: opts.antialias ?? false,
        alpha: opts.alpha ?? false,
        powerPreference: opts.powerPreference ?? 'default',
        failIfMajorPerformanceCaveat: false,
        preserveDrawingBuffer: false,
        stencil: false,
        depth: true,
        ...opts,
    });

    _mountCount = 1;

    // Cap pixel ratio to avoid GPU overload
    _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

    return _renderer;
}

/**
 * Signal that a component using the renderer has unmounted.
 * Only actually disposes when the last user unmounts.
 */
export function releaseRenderer() {
    _mountCount = Math.max(0, _mountCount - 1);
    // Don't dispose on unmount — the singleton persists for the next mount.
    // Disposal only happens on full page teardown or HMR.
}

/**
 * Force-dispose the renderer entirely (used by HMR cleanup).
 */
export function disposeRenderer() {
    if (!_renderer) return;
    try {
        _renderer.renderLists?.dispose();
        _renderer.dispose();
        const ctx = _renderer.getContext();
        const ext = ctx?.getExtension('WEBGL_lose_context');
        if (ext) ext.loseContext();
    } catch (e) {
        console.warn('[rendererSingleton] dispose error:', e.message);
    }
    _renderer = null;
    _mountCount = 0;
}

/** Check if a renderer currently exists. */
export function hasRenderer() {
    return _renderer !== null;
}

/** Get the current renderer (may be null). */
export function getRenderer() {
    return _renderer;
}

/*
 * Vite HMR: when THIS module is hot-replaced, dispose the old renderer
 * so the new module starts with a clean state.
 */
if (import.meta.hot) {
    import.meta.hot.dispose(() => {
        console.log('[rendererSingleton] HMR dispose');
        disposeRenderer();
    });
}
