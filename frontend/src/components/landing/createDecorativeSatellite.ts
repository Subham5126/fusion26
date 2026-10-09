import * as THREE from 'three';

/** Small, locally built spacecraft for the decorative hero, not observation data. */
export function createDecorativeSatellite(accent: number) {
  const group = new THREE.Group();
  group.name = 'Decorative satellite';
  group.scale.setScalar(0.9);

  const aluminum = new THREE.MeshPhongMaterial({
    color: 0xc5d2df, specular: 0x718596, shininess: 85,
  });
  const foil = new THREE.MeshPhongMaterial({
    color: 0xb39859, specular: 0x6e5c35, shininess: 35,
  });
  const lensMaterial = new THREE.MeshPhongMaterial({
    color: 0x142b46, specular: 0x8dbbdf, shininess: 100,
  });
  const accentMaterial = new THREE.MeshBasicMaterial({ color: accent });

  const solarCanvas = document.createElement('canvas');
  solarCanvas.width = 256;
  solarCanvas.height = 160;
  const context = solarCanvas.getContext('2d');
  if (context) {
    context.fillStyle = '#7390af';
    context.fillRect(0, 0, 256, 160);
    for (let row = 0; row < 5; row++) {
      for (let column = 0; column < 10; column++) {
        const shade = (row + column) % 3 === 0 ? '#214780' : '#173668';
        context.fillStyle = shade;
        context.fillRect(column * 25.6 + 1, row * 32 + 1, 23.6, 30);
        context.fillStyle = 'rgba(168, 200, 235, 0.3)';
        context.fillRect(column * 25.6 + 12, row * 32 + 2, 1, 28);
      }
    }
  }
  const solarTexture = new THREE.CanvasTexture(solarCanvas);
  solarTexture.colorSpace = THREE.SRGBColorSpace;
  const solarMaterial = new THREE.MeshPhongMaterial({
    map: solarTexture, specular: 0x304b7e, shininess: 45,
    side: THREE.DoubleSide,
  });

  const addMesh = (
    geometry: THREE.BufferGeometry, material: THREE.Material,
    position: [number, number, number], parent: THREE.Group = group,
  ) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...position);
    parent.add(mesh);
    return mesh;
  };

  // Insulated bus, instrument face and an optical aperture.
  addMesh(new THREE.BoxGeometry(2.9, 2.7, 2.3), foil, [0, 0, 0]);
  addMesh(new THREE.BoxGeometry(2.5, 2.2, 0.16), aluminum, [0, 0, 1.23]);
  const aperture = addMesh(new THREE.CylinderGeometry(0.64, 0.64, 0.25, 16), lensMaterial, [0, 0, 1.42]);
  aperture.rotation.x = Math.PI / 2;
  addMesh(new THREE.BoxGeometry(1.7, 0.12, 0.14), accentMaterial, [0, 0.88, 1.36]);

  // Framed solar wings with individual cell detail, visible on both sides.
  for (const side of [-1, 1]) {
    const wing = new THREE.Group();
    wing.position.set(side * 4.9, 0, 0);
    wing.rotation.y = side * 0.12;
    group.add(wing);
    addMesh(new THREE.BoxGeometry(6.2, 3.6, 0.2), aluminum, [0, 0, 0], wing);
    const cells = new THREE.PlaneGeometry(6, 3.4);
    addMesh(cells, solarMaterial, [0, 0, 0.12], wing);
    const back = addMesh(cells, solarMaterial, [0, 0, -0.12], wing);
    back.rotation.y = Math.PI;
    const hinge = addMesh(new THREE.CylinderGeometry(0.13, 0.13, 1.4, 8), aluminum, [side * 1.95, 0, 0]);
    hinge.rotation.z = Math.PI / 2;
  }

  // Dish, feed and antenna provide a recognizable spacecraft silhouette.
  const dish = addMesh(
    new THREE.SphereGeometry(0.9, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2),
    aluminum, [-0.65, 1.7, 0.9],
  );
  dish.rotation.x = Math.PI / 2;
  addMesh(new THREE.CylinderGeometry(0.045, 0.045, 2.1, 6), aluminum, [0.8, 2.25, -0.25]);
  addMesh(new THREE.CylinderGeometry(0.04, 0.04, 0.8, 6), aluminum, [-0.65, 1.7, 1.6]).rotation.x = Math.PI / 2;

  const dispose = () => {
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    group.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return;
      geometries.add(object.geometry);
      const ownedMaterials = Array.isArray(object.material) ? object.material : [object.material];
      ownedMaterials.forEach(material => materials.add(material));
    });
    geometries.forEach(geometry => geometry.dispose());
    materials.forEach(material => material.dispose());
    solarTexture.dispose();
  };

  return { group, dispose };
}
