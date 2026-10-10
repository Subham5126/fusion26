// T08 palette: stable by opaque track ID, independent of array order or frame.
const observed = ['#36e6ff', '#b5ff45', '#ff68dd', '#ffad45', '#fff06a'];
const predicted = ['#dd87ff', '#dd87ff', '#b1a0ff', '#dd87ff', '#dd87ff'];
export function trackColors(id: string) {
  let hash = 0;
  for (const character of id) hash = (Math.imul(hash, 31) + character.charCodeAt(0)) >>> 0;
  const index = hash % observed.length;
  return { observed: observed[index], forecast: predicted[index] };
}
