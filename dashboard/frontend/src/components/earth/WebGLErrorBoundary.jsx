/*
 * WebGLErrorBoundary — catches WebGL / Three.js errors and shows a
 * graceful fallback instead of crashing the entire dashboard.
 */
import { Component } from 'react';

export default class WebGLErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, info) {
        console.error('[WebGLErrorBoundary]', error, info.componentStack);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    width: '100%', height: this.props.height || 600,
                    borderRadius: 20, overflow: 'hidden',
                    background: '#030712', position: 'relative',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexDirection: 'column', gap: 14,
                    fontFamily: 'Inter, sans-serif', color: '#94a3b8',
                }}>
                    <div style={{ fontSize: 40 }}>⚠️</div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>
                        3D Engine Error
                    </div>
                    <div style={{ fontSize: 12, maxWidth: 380, textAlign: 'center', lineHeight: 1.5 }}>
                        The WebGL renderer encountered an error. This can happen when GPU resources are exhausted.
                    </div>
                    <button
                        onClick={this.handleRetry}
                        style={{
                            marginTop: 8, padding: '8px 24px', fontSize: 13,
                            borderRadius: 10, border: '1px solid rgba(99,102,241,0.4)',
                            background: 'rgba(99,102,241,0.15)', color: '#a5b4fc',
                            cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                        }}
                    >
                        Retry
                    </button>
                    {this.props.onFallback && (
                        <button
                            onClick={this.props.onFallback}
                            style={{
                                padding: '6px 18px', fontSize: 11,
                                borderRadius: 8, border: '1px solid rgba(148,163,184,0.2)',
                                background: 'transparent', color: '#64748b',
                                cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                            }}
                        >
                            Switch to Analytics
                        </button>
                    )}
                </div>
            );
        }
        return this.props.children;
    }
}
