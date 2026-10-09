import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export function HeroCanvas3D() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Scene setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030712, 0.0018);

    const camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 140);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Group for all celestial objects that tilt with mouse
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // 1. Central Celestial Wireframe Sphere (Earth / Reference Frame)
    const sphereGeo = new THREE.IcosahedronGeometry(24, 2);
    const sphereMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.12,
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    worldGroup.add(sphere);

    // Inner glowing core
    const coreGeo = new THREE.SphereGeometry(14, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x3b82f6,
      transparent: true,
      opacity: 0.08,
    });
    const core = new THREE.Mesh(coreGeo, coreMat);
    worldGroup.add(core);

    // 2. Orbital Rings (LEO, MEO, GEO track rings)
    const ringGroup = new THREE.Group();
    worldGroup.add(ringGroup);

    const createOrbitRing = (radius: number, tube: number, color: number, opacity: number, rotX: number, rotY: number) => {
      const ringGeo = new THREE.TorusGeometry(radius, tube, 3, 80);
      const ringMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity,
        wireframe: true,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = rotX;
      ring.rotation.y = rotY;
      ringGroup.add(ring);
      return ring;
    };

    const ring1 = createOrbitRing(42, 0.35, 0x00f0ff, 0.45, Math.PI / 3, 0.2);
    const ring2 = createOrbitRing(58, 0.35, 0xa855f7, 0.4, -Math.PI / 4, 0.5);
    const ring3 = createOrbitRing(72, 0.3, 0x38bdf8, 0.3, Math.PI / 6, -0.4);

    // 3. Floating Space Debris & Star Dust Particles
    const particleCount = 1400;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);

    const palette = [
      new THREE.Color('#00f0ff'), // cyan
      new THREE.Color('#38bdf8'), // sky blue
      new THREE.Color('#a855f7'), // purple
      new THREE.Color('#6366f1'), // indigo
      new THREE.Color('#ffffff'), // pure white
    ];

    for (let i = 0; i < particleCount; i++) {
      // Disperse in spherical shell around center
      const radius = 30 + Math.random() * 110;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      const chosenColor = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = chosenColor.r;
      colors[i * 3 + 1] = chosenColor.g;
      colors[i * 3 + 2] = chosenColor.b;

      sizes[i] = Math.random() * 2.5 + 0.8;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Particle Material with round point drawing
    const canvas = document.createElement('canvas');
    canvas.width = 16;
    canvas.height = 16;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      const grad = ctx.createRadialGradient(8, 8, 0, 8, 8, 8);
      grad.addColorStop(0, 'rgba(255,255,255,1)');
      grad.addColorStop(0.3, 'rgba(255,255,255,0.7)');
      grad.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(8, 8, 8, 0, Math.PI * 2);
      ctx.fill();
    }
    const circleTexture = new THREE.CanvasTexture(canvas);

    const particleMat = new THREE.PointsMaterial({
      size: 1.8,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      map: circleTexture,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    worldGroup.add(particles);

    // 4. Moving Candidate Trajectory Indicators (Tracked Debris Nodes)
    const candidateGroup = new THREE.Group();
    worldGroup.add(candidateGroup);

    const candidates = [
      { radius: 42, speed: 0.018, angle: 0, rotX: Math.PI / 3, rotY: 0.2, color: 0x00f0ff },
      { radius: 58, speed: -0.012, angle: 2, rotX: -Math.PI / 4, rotY: 0.5, color: 0xa855f7 },
      { radius: 72, speed: 0.009, angle: 4, rotX: Math.PI / 6, rotY: -0.4, color: 0x38bdf8 },
    ];

    const candidateMeshes = candidates.map(c => {
      const meshGeo = new THREE.SphereGeometry(1.4, 12, 12);
      const meshMat = new THREE.MeshBasicMaterial({ color: c.color });
      const mesh = new THREE.Mesh(meshGeo, meshMat);
      candidateGroup.add(mesh);
      return { ...c, mesh };
    });

    // Mouse Tracking with smooth lerp
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handlePointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetX = x * 0.45;
      targetY = y * 0.45;
    };

    window.addEventListener('mousemove', handlePointerMove, { passive: true });

    // Resize handling
    const handleResize = () => {
      if (!container) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Animation loop & Visibility control
    let isVisible = true;
    const visibilityObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
    });
    visibilityObserver.observe(container);

    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isVisible || document.hidden) return;

      const delta = prefersReducedMotion ? 0 : 0.005;

      // Rotate celestial structures gently
      worldGroup.rotation.y += delta * 0.5;
      sphere.rotation.x += delta * 0.2;
      sphere.rotation.y += delta * 0.3;
      ring1.rotation.z += delta * 0.8;
      ring2.rotation.z -= delta * 0.6;
      ring3.rotation.z += delta * 0.4;
      particles.rotation.y += delta * 0.2;

      // Update candidate markers along their orbits
      candidateMeshes.forEach(c => {
        c.angle += c.speed * (prefersReducedMotion ? 0 : 1);
        const x = Math.cos(c.angle) * c.radius;
        const y = Math.sin(c.angle) * c.radius;
        // Transform along the ring's orientation
        const pos = new THREE.Vector3(x, y, 0);
        pos.applyEuler(new THREE.Euler(c.rotX, c.rotY, 0));
        c.mesh.position.copy(pos);
      });

      // Smooth mouse reaction interpolation
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;

      worldGroup.rotation.x = currentY * 0.6;
      worldGroup.rotation.z = -currentX * 0.3;
      camera.position.x = currentX * 35;
      camera.position.y = currentY * 35;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handlePointerMove);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      // Dispose Three.js resources
      sphereGeo.dispose();
      sphereMat.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      circleTexture.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="hero-3d-canvas-wrap"
      aria-hidden="true"
    />
  );
}
