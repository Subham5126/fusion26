import { useEffect, useRef } from 'react';
import * as THREE from 'three';

// Procedural Equirectangular Earth Texture Generator
function createEarthTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 2048;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new THREE.CanvasTexture(canvas);

  const w = canvas.width;
  const h = canvas.height;

  // 1. Deep Ocean Background with Bathymetric Gradients
  const oceanGrad = ctx.createLinearGradient(0, 0, 0, h);
  oceanGrad.addColorStop(0, '#020b18');
  oceanGrad.addColorStop(0.3, '#04162e');
  oceanGrad.addColorStop(0.5, '#062042');
  oceanGrad.addColorStop(0.7, '#04162e');
  oceanGrad.addColorStop(1, '#020b18');
  ctx.fillStyle = oceanGrad;
  ctx.fillRect(0, 0, w, h);

  // Helper: Convert [lon, lat] degrees to canvas [x, y]
  const toXY = (lon: number, lat: number): [number, number] => {
    const x = ((lon + 180) / 360) * w;
    const y = ((90 - lat) / 180) * h;
    return [x, y];
  };

  // Helper: Draw polygon landmass
  const drawLandmass = (coords: [number, number][], fillColor = '#0f273d', strokeColor = 'rgba(0, 240, 255, 0.35)') => {
    if (coords.length === 0) return;
    ctx.beginPath();
    const [startX, startY] = toXY(coords[0][0], coords[0][1]);
    ctx.moveTo(startX, startY);
    for (let i = 1; i < coords.length; i++) {
      const [px, py] = toXY(coords[i][0], coords[i][1]);
      ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();
    if (strokeColor) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  };

  // 2. Continental Landmass Definitions
  // North America
  drawLandmass([
    [-168, 65], [-140, 70], [-120, 72], [-95, 74], [-60, 60], [-65, 45],
    [-75, 25], [-81, 25], [-97, 26], [-105, 20], [-100, 18], [-85, 12],
    [-77, 8], [-83, 10], [-95, 16], [-105, 22], [-115, 30], [-124, 48],
    [-132, 56], [-160, 58], [-168, 65],
  ]);

  // Greenland
  drawLandmass([
    [-55, 60], [-38, 60], [-20, 70], [-25, 82], [-50, 83], [-60, 76], [-55, 60],
  ], '#123048');

  // South America
  drawLandmass([
    [-77, 8], [-60, 10], [-50, 0], [-35, -6], [-38, -15], [-42, -23],
    [-50, -32], [-58, -42], [-66, -55], [-74, -52], [-74, -40], [-80, -20],
    [-81, -5], [-77, 8],
  ]);

  // Europe & Scandinavia
  drawLandmass([
    [-9, 38], [-9, 43], [2, 50], [8, 55], [15, 58], [25, 71], [31, 70],
    [28, 60], [20, 54], [14, 46], [0, 44], [-9, 38],
  ], '#122c42');

  // British Isles
  drawLandmass([[-5, 50], [0, 52], [-1, 58], [-6, 56], [-5, 50]]);

  // Africa
  drawLandmass([
    [-17, 15], [-17, 22], [-5, 36], [10, 37], [25, 32], [35, 30], [43, 12],
    [51, 10], [44, -12], [32, -28], [20, -35], [17, -33], [12, -18],
    [9, 4], [-10, 6], [-17, 15],
  ]);

  // Eurasia (Russia / Central Asia / China)
  drawLandmass([
    [30, 70], [60, 68], [100, 76], [140, 72], [170, 66], [180, 65],
    [160, 52], [140, 48], [130, 35], [120, 30], [108, 18], [100, 12],
    [80, 15], [75, 24], [60, 25], [50, 30], [35, 32], [30, 42], [30, 70],
  ]);

  // India
  drawLandmass([[68, 24], [72, 19], [77, 8], [82, 10], [88, 22], [80, 26], [68, 24]]);

  // Japan
  drawLandmass([[130, 32], [136, 35], [141, 44], [140, 38], [130, 32]]);

  // Southeast Asia / Indonesia archipelago
  drawLandmass([[96, 5], [104, 1], [108, 6], [101, 12], [96, 5]]);
  drawLandmass([[105, -7], [115, -8], [114, -6], [105, -7]]);
  drawLandmass([[110, 0], [118, 4], [116, -3], [110, 0]]);

  // Australia & New Zealand
  drawLandmass([
    [114, -22], [122, -14], [135, -12], [146, -15], [153, -28], [150, -36],
    [138, -38], [128, -32], [115, -34], [114, -22],
  ]);
  drawLandmass([[168, -46], [176, -38], [174, -42], [168, -46]]);

  // Antarctica
  drawLandmass([
    [-180, -70], [180, -70], [180, -90], [-180, -90],
  ], '#163552', 'rgba(0, 240, 255, 0.2)');

  // 3. Dense Night-Side City Lights (Golden & Cyan Pixels on Continents)
  const rng = (seed: number) => {
    const x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
  };

  const cityClusters = [
    [-74, 40], [-118, 34], [-87, 41], [-95, 29], [-122, 37], // US
    [2, 48], [13, 52], [0, 51], [37, 55], [12, 41], // Europe
    [77, 28], [72, 19], [88, 22], // India
    [116, 39], [121, 31], [113, 23], // China
    [139, 35], [135, 34], // Japan
    [-46, -23], [-58, -34], // South America
    [151, -33], [144, -37], // Australia
    [31, 30], [28, -26], // Africa
  ];

  cityClusters.forEach(([clon, clat], clusterIdx) => {
    const [cx, cy] = toXY(clon, clat);
    for (let i = 0; i < 45; i++) {
      const rx = cx + (rng(clusterIdx * 100 + i) - 0.5) * 38;
      const ry = cy + (rng(clusterIdx * 200 + i) - 0.5) * 28;
      const isCyan = i % 3 === 0;
      ctx.fillStyle = isCyan ? 'rgba(56, 189, 248, 0.85)' : 'rgba(253, 224, 71, 0.85)';
      ctx.beginPath();
      ctx.arc(rx, ry, rng(i) > 0.7 ? 1.6 : 0.9, 0, Math.PI * 2);
      ctx.fill();
    }
  });

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

// Procedural Clouds Texture Generator
function createCloudTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new THREE.CanvasTexture(canvas);

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Soft atmospheric cloud swirls across latitudes
  for (let y = 60; y < 450; y += 40) {
    for (let x = 0; x < canvas.width; x += 65) {
      const radius = 25 + Math.random() * 45;
      const alpha = 0.08 + Math.random() * 0.16;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
      grad.addColorStop(0, `rgba(255, 255, 255, ${alpha})`);
      grad.addColorStop(0.5, `rgba(186, 230, 253, ${alpha * 0.5})`);
      grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

export function HeroCanvas3D() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Scene & Camera Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030712, 0.0016);

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

    // 2. Lighting Setup
    const sunLight = new THREE.DirectionalLight(0xffffff, 2.2);
    sunLight.position.set(-80, 50, 100);
    scene.add(sunLight);

    const rimLight = new THREE.DirectionalLight(0x00f0ff, 1.4);
    rimLight.position.set(80, -40, -40);
    scene.add(rimLight);

    const ambientLight = new THREE.AmbientLight(0x091b36, 0.85);
    scene.add(ambientLight);

    // 3. World Group (positioned at the location of Earth)
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // Responsive position calculation:
    // On desktop, position shifted to the right & lower half (where the Earth horizon sits).
    // On mobile, positioned center-bottom.
    const updateWorldPlacement = () => {
      const width = window.innerWidth;
      if (width < 640) {
        worldGroup.position.set(0, -26, -10);
        worldGroup.scale.setScalar(0.72);
      } else if (width < 1024) {
        worldGroup.position.set(30, -14, 0);
        worldGroup.scale.setScalar(0.85);
      } else {
        worldGroup.position.set(40, -14, 0);
        worldGroup.scale.setScalar(1.0);
      }
    };
    updateWorldPlacement();

    // 4. Earth Globe
    const earthRadius = 23;
    const earthGeo = new THREE.SphereGeometry(earthRadius, 64, 64);
    const earthTex = createEarthTexture();

    const earthMat = new THREE.MeshStandardMaterial({
      map: earthTex,
      roughness: 0.6,
      metalness: 0.15,
      emissive: new THREE.Color(0x031326),
      emissiveIntensity: 0.45,
    });

    const earthMesh = new THREE.Mesh(earthGeo, earthMat);
    // Axial tilt (approx 23.5 degrees)
    earthMesh.rotation.z = 0.41;
    worldGroup.add(earthMesh);

    // 5. Cloud Layer Sphere
    const cloudGeo = new THREE.SphereGeometry(earthRadius + 0.5, 48, 48);
    const cloudTex = createCloudTexture();
    const cloudMat = new THREE.MeshStandardMaterial({
      map: cloudTex,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const cloudMesh = new THREE.Mesh(cloudGeo, cloudMat);
    cloudMesh.rotation.z = 0.41;
    worldGroup.add(cloudMesh);

    // 6. Atmospheric Fresnel Halo (Glow Rim around Earth)
    const atmosphereGeo = new THREE.SphereGeometry(earthRadius + 2.2, 48, 48);
    const atmosphereMat = new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        void main() {
          vec3 viewDir = normalize(-vPosition);
          float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 2.8);
          vec3 atmosphereColor = mix(vec3(0.0, 0.94, 1.0), vec3(0.66, 0.33, 0.97), 0.25);
          gl_FragColor = vec4(atmosphereColor, fresnel * 0.95);
        }
      `,
      blending: THREE.AdditiveBlending,
      transparent: true,
      side: THREE.BackSide,
      depthWrite: false,
    });
    const atmosphereMesh = new THREE.Mesh(atmosphereGeo, atmosphereMat);
    worldGroup.add(atmosphereMesh);

    // 7. Wireframe Coordinate Geodesic Grid (Subtle OrbitTrace Scope)
    const gridGeo = new THREE.IcosahedronGeometry(earthRadius + 1.2, 2);
    const gridMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.09,
    });
    const gridMesh = new THREE.Mesh(gridGeo, gridMat);
    worldGroup.add(gridMesh);

    // 8. Orbital Rings around the Earth (LEO, MEO, GEO)
    const ringGroup = new THREE.Group();
    worldGroup.add(ringGroup);

    const createOrbitRing = (radius: number, tube: number, color: number, opacity: number, rotX: number, rotY: number) => {
      const ringGeo = new THREE.TorusGeometry(radius, tube, 3, 90);
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

    const ring1 = createOrbitRing(36, 0.32, 0x00f0ff, 0.55, Math.PI / 3.2, 0.25); // LEO
    const ring2 = createOrbitRing(50, 0.35, 0xa855f7, 0.45, -Math.PI / 3.8, 0.55); // MEO
    const ring3 = createOrbitRing(65, 0.3, 0x38bdf8, 0.35, Math.PI / 5.5, -0.42); // GEO

    // 9. Floating Space Debris & Star Dust Particles around the Earth
    const particleCount = 1200;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const palette = [
      new THREE.Color('#00f0ff'),
      new THREE.Color('#38bdf8'),
      new THREE.Color('#a855f7'),
      new THREE.Color('#6366f1'),
      new THREE.Color('#ffffff'),
    ];

    for (let i = 0; i < particleCount; i++) {
      const radius = 28 + Math.random() * 85;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      const chosenColor = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = chosenColor.r;
      colors[i * 3 + 1] = chosenColor.g;
      colors[i * 3 + 2] = chosenColor.b;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Round particle sprite
    const pCanvas = document.createElement('canvas');
    pCanvas.width = 16;
    pCanvas.height = 16;
    const pCtx = pCanvas.getContext('2d');
    if (pCtx) {
      const grad = pCtx.createRadialGradient(8, 8, 0, 8, 8, 8);
      grad.addColorStop(0, 'rgba(255,255,255,1)');
      grad.addColorStop(0.3, 'rgba(255,255,255,0.7)');
      grad.addColorStop(1, 'rgba(255,255,255,0)');
      pCtx.fillStyle = grad;
      pCtx.beginPath();
      pCtx.arc(8, 8, 8, 0, Math.PI * 2);
      pCtx.fill();
    }
    const circleTexture = new THREE.CanvasTexture(pCanvas);

    const particleMat = new THREE.PointsMaterial({
      size: 1.6,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      map: circleTexture,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    worldGroup.add(particles);

    // 10. Candidate Tracked Targets Orbiting the Earth
    const candidateGroup = new THREE.Group();
    worldGroup.add(candidateGroup);

    const candidates = [
      { radius: 36, speed: 0.016, angle: 0.2, rotX: Math.PI / 3.2, rotY: 0.25, color: 0x00f0ff },
      { radius: 50, speed: -0.011, angle: 2.4, rotX: -Math.PI / 3.8, rotY: 0.55, color: 0xa855f7 },
      { radius: 65, speed: 0.008, angle: 4.6, rotX: Math.PI / 5.5, rotY: -0.42, color: 0x38bdf8 },
    ];

    const candidateMeshes = candidates.map(c => {
      const meshGeo = new THREE.SphereGeometry(1.3, 12, 12);
      const meshMat = new THREE.MeshBasicMaterial({ color: c.color });
      const mesh = new THREE.Mesh(meshGeo, meshMat);
      candidateGroup.add(mesh);
      return { ...c, mesh };
    });

    // 11. Mouse Movement Interaction (Parallax Tilt)
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handlePointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetX = x * 0.35;
      targetY = y * 0.35;
    };

    window.addEventListener('mousemove', handlePointerMove, { passive: true });

    const handleResize = () => {
      if (!container) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      updateWorldPlacement();
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    let isVisible = true;
    const visibilityObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
    });
    visibilityObserver.observe(container);

    let animationFrameId: number;

    // 12. Animation Loop
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isVisible || document.hidden) return;

      const delta = prefersReducedMotion ? 0 : 0.004;

      // Rotate Earth on its axis
      earthMesh.rotation.y += delta * 0.6;
      // Clouds rotate slightly faster for realistic atmospheric drift
      cloudMesh.rotation.y += delta * 0.85;
      gridMesh.rotation.y += delta * 0.3;

      // Orbit rings rotate around Earth
      ring1.rotation.z += delta * 0.9;
      ring2.rotation.z -= delta * 0.6;
      ring3.rotation.z += delta * 0.45;
      particles.rotation.y += delta * 0.2;

      // Tracked candidate motion along orbits
      candidateMeshes.forEach(c => {
        c.angle += c.speed * (prefersReducedMotion ? 0 : 1);
        const x = Math.cos(c.angle) * c.radius;
        const y = Math.sin(c.angle) * c.radius;
        const pos = new THREE.Vector3(x, y, 0);
        pos.applyEuler(new THREE.Euler(c.rotX, c.rotY, 0));
        c.mesh.position.copy(pos);
      });

      // Smooth mouse lerp
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;

      worldGroup.rotation.x = currentY * 0.45;
      worldGroup.rotation.y = currentX * 0.45;
      camera.position.x = currentX * 20;
      camera.position.y = currentY * 20;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handlePointerMove);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      earthGeo.dispose();
      earthMat.dispose();
      earthTex.dispose();
      cloudGeo.dispose();
      cloudMat.dispose();
      cloudTex.dispose();
      atmosphereGeo.dispose();
      atmosphereMat.dispose();
      gridGeo.dispose();
      gridMat.dispose();
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
