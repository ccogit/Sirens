// Bild der Spielwiese: drei Wellenbänder wie im Logo, die mit Bass, Mitten und Höhen des Songs gehen.

const BAND = [["#b2a9f5", 0.9], ["#8f8df0", 1.25], ["#6f7cff", 1.7]]; // Farbe, Wellenzahl
const WARM = "#ffb37a";

// Bass, Mitten, Höhen (je 0…1) aus dem Frequenzbild des Tonwerks.
export function baender(messer, frequenzen) {
  messer.getByteFrequencyData(frequenzen);
  const mittel = (von, bis) => {
    let summe = 0;
    for (let i = von; i < bis; i += 1) summe += frequenzen[i];
    return summe / (bis - von) / 255;
  };
  return [mittel(1, 9), mittel(9, 80), mittel(80, 360)];
}

// Zustand zwischen zwei Bildern: geglättete Bänder und die Ringe, die ein Bassschlag auslöst.
export function bildZustand() {
  return { glatt: [0, 0, 0], bassVorher: 0, ringe: [] };
}

// Ein Bild der Bühne. `kraft`: [Bass, Mitten, Höhen]; `welle`: Schwingung (Uint8Array) oder null; `zeiger`: {x, y} 0…1 oder null.
export function buehneMalen(stift, w, h, zeit, z, kraft, welle, zeiger) {
  stift.fillStyle = "rgba(12, 18, 38, 0.3)"; // nicht ganz löschen: die Bänder ziehen eine Spur
  stift.fillRect(0, 0, w, h);
  for (let i = 0; i < 3; i += 1) z.glatt[i] += (kraft[i] - z.glatt[i]) * 0.25;
  if (kraft[0] - z.bassVorher > 0.09 && z.ringe.length < 6) {
    z.ringe.push({ x: zeiger ? zeiger.x * w : w / 2, y: zeiger ? (1 - zeiger.y) * h : h / 2, r: 6, kraft: 1 });
  }
  z.bassVorher = kraft[0];

  stift.lineWidth = 2;
  for (const ring of z.ringe) {
    stift.strokeStyle = `rgba(255, 179, 122, ${ring.kraft * 0.5})`;
    stift.beginPath(); stift.arc(ring.x, ring.y, ring.r, 0, Math.PI * 2); stift.stroke();
    ring.r += h * 0.018; ring.kraft *= 0.94;
  }
  z.ringe = z.ringe.filter((ring) => ring.kraft > 0.04);

  const schritt = Math.max(3, Math.floor(w / 220));
  BAND.forEach(([farbe, wellen], i) => {
    const ausschlag = h * (0.05 + 0.3 * z.glatt[i]);
    const mitte = h / 2 + (i - 1) * h * 0.15;
    stift.beginPath();
    for (let x = 0; x <= w; x += schritt) {
      const zittern = welle ? ((welle[Math.floor((x / w) * (welle.length - 1))] - 128) / 128) * h * 0.1 * (1 + i * 0.5) : 0;
      const y = mitte + ausschlag * Math.sin((x / w) * Math.PI * 2 * wellen + zeit * (0.5 + i * 0.3)) + zittern;
      if (x === 0) stift.moveTo(x, y); else stift.lineTo(x, y);
    }
    stift.strokeStyle = farbe; stift.globalAlpha = 0.22; stift.lineWidth = 9 + z.glatt[i] * 14; stift.stroke();
    stift.globalAlpha = 1; stift.lineWidth = 2.4; stift.stroke();
  });

  if (zeiger) {
    const [x, y] = [zeiger.x * w, (1 - zeiger.y) * h];
    stift.strokeStyle = "rgba(255, 255, 255, 0.18)"; stift.lineWidth = 1;
    stift.beginPath(); stift.moveTo(x, 0); stift.lineTo(x, h); stift.moveTo(0, y); stift.lineTo(w, y); stift.stroke();
    stift.fillStyle = WARM; stift.beginPath(); stift.arc(x, y, 9, 0, Math.PI * 2); stift.fill();
  }
}

// Übersicht über das ganze Stück: Ausschläge als Balken, der gespielte Teil hell.
export function uebersichtMalen(stift, w, h, huelle, anteil) {
  stift.clearRect(0, 0, w, h);
  if (!huelle) return;
  const breite = w / huelle.length;
  const hoechster = Math.max(0.05, ...huelle);
  huelle.forEach((wert, i) => {
    const hoehe = Math.max(2, (wert / hoechster) * (h - 4));
    stift.fillStyle = i / huelle.length < anteil ? "#a9b4ff" : "rgba(169, 180, 255, 0.3)";
    stift.fillRect(i * breite, (h - hoehe) / 2, Math.max(1, breite - 1), hoehe);
  });
  stift.fillStyle = WARM;
  stift.fillRect(Math.min(w - 2, anteil * w), 0, 2, h);
}
