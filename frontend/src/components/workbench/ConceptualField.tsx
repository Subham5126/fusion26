// Presentation-only diagram. These marks are never supplied to analysis or a result.
const stars = Array.from({ length: 95 }, (_, index) => ({
  x: (index * 193 + 29) % 640, y: (index * 97 + 41) % 360,
  radius: index % 11 === 0 ? 1.4 : .6, opacity: .22 + (index % 5) * .12,
}));

export function ConceptualField() {
  return <svg className="conceptual-field" viewBox="0 0 640 360" role="img"
    aria-labelledby="concept-field-title concept-field-description">
    <title id="concept-field-title">Conceptual optical field illustration</title>
    <desc id="concept-field-description">Three illustrative solid observation markers and a separate hollow predicted marker. No telescope images or analysis results are loaded.</desc>
    <g className="concept-stars">{stars.map((star, index) => <circle key={index}
      cx={star.x} cy={star.y} r={star.radius} opacity={star.opacity} />)}</g>
    <path className="concept-observed" d="M218 226 282 192 346 158" />
    <path className="concept-predicted" d="m346 158 64-34" />
    {[{ x: 218, y: 226 }, { x: 282, y: 192 }, { x: 346, y: 158 }].map(point =>
      <circle className="concept-point" key={point.x} cx={point.x} cy={point.y} r="4" />)}
    <circle className="concept-predicted-point" cx="410" cy="124" r="5" />
  </svg>;
}
