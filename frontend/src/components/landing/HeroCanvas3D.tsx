import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { createDecorativeSatellite } from './createDecorativeSatellite';

export function HeroCanvas3D() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check prefers-reduced-motion
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let prefersReducedMotion = motionPreference.matches;
    let requestRender = () => {};
    const updateMotionPreference = () => { prefersReducedMotion = motionPreference.matches; requestRender(); };

    // Scene setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x020c11, 0.0018);

    const camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 140);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'default' });
    } catch {
      // The landing copy, links and background remain usable without WebGL.
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);
    motionPreference.addEventListener('change', updateMotionPreference);

    // Group for all celestial objects that tilt with mouse
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // Decorative Earth shares the existing rings' center. Texture is served locally.
    // NASA Blue Marble attribution is in earth-blue-marble.provenance.json.
    const earthGroup = new THREE.Group();
    earthGroup.rotation.z = THREE.MathUtils.degToRad(23.4);
    worldGroup.add(earthGroup);
    const earthGeo = new THREE.SphereGeometry(24, 64, 48);
    const earthMat = new THREE.MeshPhongMaterial({
      color: 0x2d6192, specular: 0x244363, shininess: 16,
      emissive: 0x071a35, emissiveIntensity: 0.35,
    });
    const earth = new THREE.Mesh(earthGeo, earthMat);
    earth.rotation.y = -Math.PI / 2;
    earthGroup.add(earth);
    const textureLoader = new THREE.TextureLoader();
    let disposed = false;
    const earthTexture = textureLoader.load('/assets/earth-blue-marble.webp', texture => {
      if (disposed) { texture.dispose(); return; }
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
      earthMat.map = texture;
      earthMat.color.set(0xc3ddff);
      earthMat.needsUpdate = true;
      requestRender();
    });

    // Match the background's cool palette and upper-right sunlight.
    const sun = new THREE.DirectionalLight(0xd6ebff, 2.8);
    sun.position.set(65, 40, 100);
    scene.add(sun);
    scene.add(new THREE.AmbientLight(0x87b4e3, 1.6));

    // Clouds sit on the surface; no atmosphere shell or outline around Earth.
    const cloudGeo = new THREE.SphereGeometry(24.08, 64, 48);
    const cloudMat = new THREE.MeshPhongMaterial({
      color: 0xe5f2ff, transparent: true, opacity: 0.88,
      depthWrite: false, specular: 0x102232, shininess: 5,
    });
    const clouds = new THREE.Mesh(cloudGeo, cloudMat);
    clouds.rotation.y = earth.rotation.y;
    clouds.visible = false;
    earthGroup.add(clouds);
    const cloudTexture = textureLoader.load('/assets/earth-clouds.jpg', texture => {
      if (disposed) { texture.dispose(); return; }
      texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
      cloudMat.alphaMap = texture;
      cloudMat.needsUpdate = true;
      clouds.visible = true;
      requestRender();
    });

    // 2. Decorative orbital rings
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

    const ring1 = createOrbitRing(42, 0.35, 0x12d6aa, 0.45, Math.PI / 3, 0.2);
    const ring2 = createOrbitRing(58, 0.35, 0x39e6c7, 0.4, -Math.PI / 4, 0.5);
    const ring3 = createOrbitRing(72, 0.3, 0x86d9f1, 0.3, Math.PI / 6, -0.4);

    // 3. Floating Space Debris & Star Dust Particles
    const particleCount = 1400;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);

    const palette = [
      new THREE.Color('#12d6aa'), // emerald
      new THREE.Color('#39e6c7'), // neon mint
      new THREE.Color('#86d9f1'), // ice blue
      new THREE.Color('#a5b9c4'), // cool silver gray
      new THREE.Color('#f4f8fa'), // soft white
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
      opacity: 0.68,
      map: circleTexture,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    worldGroup.add(particles);

    // 4. One locally modeled satellite per ring, attached to its exact plane.
    const satelliteOrbits = [
      { ring: ring1, radius: 42, speed: 0.006, angle: 0, color: 0x12d6aa },
      { ring: ring2, radius: 58, speed: -0.004, angle: 2, color: 0x39e6c7 },
      { ring: ring3, radius: 72, speed: 0.003, angle: 4, color: 0x86d9f1 },
    ];

    const satellites = satelliteOrbits.map(orbit => {
      const model = createDecorativeSatellite(orbit.color);
      orbit.ring.add(model.group);
      return { ...orbit, model };
    });

    // Mouse Tracking with smooth lerp
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handlePointerMove = (e: MouseEvent) => {
      if (prefersReducedMotion || window.matchMedia('(pointer: coarse)').matches) return;
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetX = Math.max(-1, Math.min(1, x)) * 0.2;
      targetY = Math.max(-1, Math.min(1, y)) * 0.2;
    };

    window.addEventListener('mousemove', handlePointerMove, { passive: true });

    // Resize handling
    const handleResize = () => {
      if (!container) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      if (!width || !height) return;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      requestRender();
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Animation loop & Visibility control
    let isVisible = true;
    const visibilityObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
      requestRender();
    });
    visibilityObserver.observe(container);

    let animationFrameId = 0;

    const animate = () => {
      animationFrameId = 0;
      if (!isVisible || document.hidden) return;

      const delta = prefersReducedMotion ? 0 : 0.005;

      // Rotate celestial structures gently
      worldGroup.rotation.y += delta * 0.5;
      earth.rotation.y += delta * 0.3;
      clouds.rotation.y += delta * 0.32;
      ring1.rotation.z += delta * 0.8;
      ring2.rotation.z -= delta * 0.6;
      ring3.rotation.z += delta * 0.4;
      particles.rotation.y += delta * 0.2;

      // Parenting retains alignment while the rings rotate and the view tilts.
      satellites.forEach(satellite => {
        satellite.angle += satellite.speed * (prefersReducedMotion ? 0 : 1);
        satellite.model.group.position.set(
          Math.cos(satellite.angle) * satellite.radius,
          Math.sin(satellite.angle) * satellite.radius,
          0,
        );
        satellite.model.group.rotation.set(-0.25, 0.2, satellite.angle + Math.PI / 2);
      });

      // Smooth mouse reaction interpolation
      currentX = prefersReducedMotion ? 0 : currentX + (targetX - currentX) * 0.05;
      currentY = prefersReducedMotion ? 0 : currentY + (targetY - currentY) * 0.05;

      worldGroup.rotation.x = currentY * 0.6;
      worldGroup.rotation.z = -currentX * 0.3;
      camera.position.x = currentX * 35;
      camera.position.y = currentY * 35;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
      if (!prefersReducedMotion) animationFrameId = requestAnimationFrame(animate);
    };
    requestRender = () => {
      if (!isVisible || document.hidden) { cancelAnimationFrame(animationFrameId); animationFrameId = 0; }
      else if (!animationFrameId) animationFrameId = requestAnimationFrame(animate);
    };
    document.addEventListener('visibilitychange', requestRender);
    requestRender();

    // Cleanup on unmount
    return () => {
      motionPreference.removeEventListener('change', updateMotionPreference);
      document.removeEventListener('visibilitychange', requestRender);
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handlePointerMove);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      // Dispose Three.js resources
      disposed = true;
      earthGeo.dispose();
      earthMat.dispose();
      earthTexture.dispose();
      cloudGeo.dispose();
      cloudMat.dispose();
      cloudTexture.dispose();
      satellites.forEach(satellite => satellite.model.dispose());
      [ring1, ring2, ring3].forEach(ring => {
        ring.geometry.dispose();
        (ring.material as THREE.Material).dispose();
      });
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
