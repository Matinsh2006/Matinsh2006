// Endless marquee whose speed and direction follow the scroll velocity.
export function initMarquees({ lenis } = {}) {
  const marquees = [...document.querySelectorAll("[data-marquee]")].map((element) => ({
    element,
    track: element.querySelector("[data-marquee-track]"),
    x: 0,
    base: parseFloat(element.dataset.speed || "40"),
    visible: false,
  }));
  if (!marquees.length) return;
  const observer = new IntersectionObserver((entries) =>
    entries.forEach((entry) => {
      const item = marquees.find((m) => m.element === entry.target);
      if (item) item.visible = entry.isIntersecting;
    })
  );
  marquees.forEach((m) => observer.observe(m.element));

  let direction = 1;
  let boost = 0;
  let last = performance.now();
  const frame = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const velocity = lenis ? lenis.velocity : 0;
    if (Math.abs(velocity) > 0.5) direction = velocity > 0 ? 1 : -1;
    boost += (Math.min(Math.abs(velocity) * 12, 600) - boost) * Math.min(1, dt * 4);
    for (const m of marquees) {
      if (!m.visible || !m.track) continue;
      // The template repeats the same group several times; one group is the period.
      const period = m.track.querySelector("[data-marquee-group]")?.offsetWidth || m.track.scrollWidth / 2;
      m.x += (m.base + boost) * dt * direction;
      if (m.x > period) m.x -= period;
      if (m.x < 0) m.x += period;
      m.track.style.transform = `translate3d(${m.x.toFixed(2)}px, 0, 0)`;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}
