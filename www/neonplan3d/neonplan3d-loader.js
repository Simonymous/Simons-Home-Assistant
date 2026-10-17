// NeonPlan 3D: loads the dashboard card. Written by the integration; changes here are overwritten.
// While Home Assistant is still starting, the card's script is not served yet: then it tries again (#461).
const url = "/neonplan3d_static/neonplan3d.js?v=1.20.0-234d2b66a9";
const tag = "neonplan3d-card";
const load = async (n) => {
  try {
    await import(n ? `${url}&retry=${n}` : url);
  } catch (err) {
    // not there yet
  }
};
await load(0);
(async () => {
  for (let n = 1; n <= 180 && !customElements.get(tag); n++) {
    await new Promise((done) => setTimeout(done, 5000));
    if (!customElements.get(tag)) await load(n);
  }
})();
