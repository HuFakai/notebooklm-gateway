import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import LiquidGlass from 'liquid-glass-react';

const PROFILES = {
  compact: {
    displacementScale: 34,
    blurAmount: 0.018,
    saturation: 155,
    aberrationIntensity: 1.4,
    elasticity: 0.06,
  },
  panel: {
    displacementScale: 46,
    blurAmount: 0.026,
    saturation: 148,
    aberrationIntensity: 1.8,
    elasticity: 0.045,
  },
};

function useSurfaceSize(host) {
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const rect = host.getBoundingClientRect();
        const next = {
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
        setSize(current => (
          current.width === next.width && current.height === next.height ? current : next
        ));
      });
    };
    const observer = new ResizeObserver(update);
    observer.observe(host);
    update();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [host]);

  return size;
}

function GlassSurface({ host, profileName }) {
  const size = useSurfaceSize(host);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const profile = PROFILES[profileName] || PROFILES.compact;
  const radius = useMemo(() => {
    const parsed = Number.parseFloat(getComputedStyle(host).borderRadius);
    return Number.isFinite(parsed) ? parsed : 20;
  }, [host, size.width, size.height]);

  if (size.width < 12 || size.height < 12) return null;

  return (
    <LiquidGlass
      key={`${size.width}x${size.height}`}
      {...profile}
      elasticity={reducedMotion ? 0 : profile.elasticity}
      cornerRadius={radius}
      padding="0"
      mode="standard"
      className="liquid-glass-engine"
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        width: `${size.width}px`,
        height: `${size.height}px`,
        pointerEvents: 'none',
      }}
    >
      <span
        aria-hidden="true"
        style={{ display: 'block', width: `${size.width}px`, height: `${size.height}px` }}
      />
    </LiquidGlass>
  );
}

function mountLiquidSurfaces() {
  if (!window.ResizeObserver || !CSS.supports('backdrop-filter', 'blur(2px)')) return;

  document.querySelectorAll('[data-liquid-glass]').forEach(host => {
    if (host.dataset.liquidGlassReady === 'true') return;
    const mount = document.createElement('div');
    mount.className = 'liquid-glass-host';
    mount.setAttribute('aria-hidden', 'true');
    host.prepend(mount);
    host.classList.add('liquid-surface');
    host.dataset.liquidGlassReady = 'true';
    createRoot(mount).render(
      <GlassSurface host={host} profileName={host.dataset.liquidGlass} />,
    );
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountLiquidSurfaces, { once: true });
} else {
  mountLiquidSurfaces();
}
