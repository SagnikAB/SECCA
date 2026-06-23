import * as THREE from "three";
import "./style.css";

const examples = {
  risky: `Master Services Agreement: VendorX will provide analytics services.
The contract sets a liability cap of $75,000 and payment of EUR 120,000.
This agreement contains a data protection clause but no termination for cause language.`,
  safe: `Services Agreement: VendorA will provide analytics services.
The liability cap is $40,000. Payment is EUR 20,000.
This agreement includes data protection and termination for cause clauses.`,
};

document.querySelector("#app").innerHTML = `
  <div class="shell">
    <aside>
      <div class="brand"><span class="brand-mark">S</span><div><b>Contract Sentinel</b><small>Secure review workspace</small></div></div>
      <h2>Start with a sample</h2>
      <div class="choices"><button class="sample active" data-sample="risky">Risky example</button><button class="sample" data-sample="safe">Compliant example</button></div>
      <div class="security"><h2>Security status</h2><strong><i></i>Security gate active</strong><p>Prompt injection and path traversal are blocked before analysis begins.</p></div>
    </aside>
    <main>
      <section class="hero"><div><span class="eyebrow">Contract intelligence</span><h1>Know what needs attention<br>before you sign.</h1><p>Run an auditable review across policy requirements and financial exposure, with a security gate protecting every analysis.</p></div><div class="orb" aria-hidden="true"><canvas id="security-orb"></canvas></div></section>
      <div class="steps"><b>01</b> Add contract text <span>•</span> <b>02</b> Run assessment <span>•</span> <b>03</b> Review decision</div>
      <label class="label" for="contract">Contract content</label><textarea id="contract" aria-label="Contract content"></textarea><button id="analyze" class="primary">Run secure assessment</button>
      <div id="error" class="error hidden" role="alert"></div><div id="hint" class="hint"><b>Ready when you are.</b><br>Choose a sample or paste a contract, then run the assessment to see a structured decision.</div>
      <section id="result" class="hidden" aria-live="polite"></section>
    </main>
  </div>`;

const editor = document.querySelector("#contract");
const result = document.querySelector("#result");
const error = document.querySelector("#error");
const hint = document.querySelector("#hint");
const action = document.querySelector("#analyze");
editor.value = examples.risky;

document.querySelectorAll(".sample").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".sample").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    editor.value = examples[button.dataset.sample];
  });
});

const element = (tag, text, className) => {
  const item = document.createElement(tag);
  if (text !== undefined) item.textContent = text;
  if (className) item.className = className;
  return item;
};

function makeCard(title) {
  const card = element("div", undefined, "card");
  card.append(element("div", title, "label"));
  return card;
}

function renderReport(data) {
  const { report, events } = data;
  const exposure = report.financial_exposure || {};
  const rejected = report.final_verdict.startsWith("REJECTED");
  const conditional = report.final_verdict.startsWith("CONDITIONAL");
  result.replaceChildren();
  result.append(element("div", "Assessment outcome", "label"));
  result.append(element("div", report.final_verdict, `verdict ${rejected ? "rejected" : conditional ? "conditional" : "approved"}`));

  const metrics = element("div", undefined, "metrics");
  [["Policy findings", report.compliance_flags.length], ["Blocking issues", report.compliance_flags.filter((flag) => flag.startsWith("BLOCKER")).length], ["Detected currency", exposure.source_currency || "—"]].forEach(([title, value]) => {
    const metric = element("div", undefined, "metric");
    metric.append(element("small", title), element("strong", String(value)));
    metrics.append(metric);
  });
  result.append(metrics);

  const columns = element("div", undefined, "columns");
  const findings = makeCard("Compliance findings");
  if (report.compliance_flags.length) {
    report.compliance_flags.forEach((flag) => {
      const blocker = flag.startsWith("BLOCKER");
      const row = element("div", undefined, `finding ${blocker ? "" : "review"}`);
      row.append(element("span", blocker ? "Blocker" : "Needs review", "tag"), document.createTextNode(flag.split(": ").slice(1).join(": ")));
      findings.append(row);
    });
  } else findings.append(element("p", "No configured policy violations were detected."));

  const finance = makeCard("Financial exposure");
  if (exposure.status === "not_applicable") finance.append(element("p", exposure.reason));
  else {
    finance.append(element("div", `$${Number(exposure.usd_exposure).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, "exposure"));
    [["Source amount", `${exposure.source_currency} ${exposure.source_amount}`], ["Applied FX rate", `${exposure.usd_rate} USD`], ["Rate date", exposure.rate_as_of]].forEach(([title, value]) => {
      const line = element("p");
      line.append(element("strong", title), document.createElement("br"), document.createTextNode(value));
      finance.append(line);
    });
  }
  columns.append(findings, finance);
  result.append(columns);
  const audit = element("details", undefined, "audit");
  audit.append(element("summary", "View execution events"), element("pre", JSON.stringify(events, null, 2)));
  result.append(audit);
  result.classList.remove("hidden");
}

action.addEventListener("click", async () => {
  error.classList.add("hidden");
  action.disabled = true;
  action.textContent = "Reviewing policy requirements and financial exposure…";
  try {
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ contract_text: editor.value }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "Assessment failed.");
    renderReport(data);
    hint.classList.add("hidden");
  } catch (exception) {
    error.textContent = exception.message;
    error.classList.remove("hidden");
  } finally {
    action.disabled = false;
    action.textContent = "Run secure assessment";
  }
});

function startOrb() {
  const canvas = document.querySelector("#security-orb");
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
  camera.position.z = 5;
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  const group = new THREE.Group();
  scene.add(group);
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.72, 2), new THREE.MeshBasicMaterial({ color: 0x315efb, wireframe: true, transparent: true, opacity: 0.9 }));
  group.add(core);
  [[1.12, 0.012, 0x7d9aff], [1.42, 0.008, 0xadc0ff], [1.72, 0.005, 0xd8e2ff]].forEach(([radius, tube, color], index) => {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, 12, 96), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.85 }));
    ring.rotation.set(index * 0.8, index * 0.45, index * 0.35);
    group.add(ring);
  });
  const resize = () => { const size = canvas.clientWidth || 240; renderer.setSize(size, size, false); camera.aspect = 1; camera.updateProjectionMatrix(); };
  resize(); window.addEventListener("resize", resize);
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const animate = (time = 0) => { group.rotation.y = time * 0.00035; core.rotation.x = time * 0.0006; renderer.render(scene, camera); if (!reduceMotion) requestAnimationFrame(animate); };
  animate();
}

startOrb();
