// Amostra F13-T80 — as notas de atualização (Leo, 17/10/2026: "um ícone que contém os nossos patch
// notes, para eu e os outros usuários saberem o que foi adicionado, ajustado ou removido"; 20/10/2026:
// "adicionar no Notas de atualização o roadmap atual de atualizações, para interessar os usuários").
// Só para a captura: injetada no app de verdade pelo docs/amostras_notas.py, que passa as notas
// (window.__NOTAS, tiradas dos commits F13-T…) e a opção (window.__OPCAO: "A" ou "B"). Não é código
// do app e não grava nada.
(function () {
  const N = window.__NOTAS || { datas: [], embreve: [] };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = `
  .notas-btn { position: relative; }
  .notas-btn svg { width: 18px; height: 18px; }
  .notas-btn .nb-num { position: absolute; right: -10px; bottom: -6px; padding: 0 4px; border-radius: 7px; font: 600 9.5px/14px var(--loja-texto);
    color: var(--loja-papel); background: var(--loja-cera); border: 1px solid rgba(0,0,0,.35); }
  /* A — o pergaminho (o mesmo modal da ficha do item) */
  .nt-head h2 { margin: 0; }
  .nt-sub { font-family: var(--loja-texto); font-style: italic; color: var(--loja-tinta-suave); margin-top: 2px; }
  .nt-abas { display: flex; gap: 6px; margin: 14px 0 10px; border-bottom: 1px solid var(--loja-papel-borda); }
  .nt-abas button { font: 600 12px var(--loja-texto); letter-spacing: .08em; text-transform: uppercase; padding: 6px 12px; background: none;
    border: 1px solid transparent; border-bottom: none; color: var(--loja-tinta-suave); cursor: pointer; }
  .nt-abas button.ativo { background: rgba(0,0,0,.05); border-color: var(--loja-papel-borda); color: var(--loja-cera); }
  .nt-data { font: 600 12px var(--loja-texto); letter-spacing: .1em; text-transform: uppercase; color: var(--loja-tinta-suave); margin: 14px 0 6px; }
  .nt-grupo { display: grid; grid-template-columns: 96px 1fr; gap: 2px 10px; margin: 4px 0 8px; font-family: var(--loja-texto); font-size: 13.5px; line-height: 1.45; color: var(--loja-tinta); }
  .nt-k { font-variant: small-caps; letter-spacing: .05em; padding-top: 1px; }
  .nt-k.add { color: #3f6b2a; } .nt-k.aj { color: #8a5a12; } .nt-k.rem { color: #6a6058; }
  .nt-grupo ul { margin: 0; padding-left: 16px; } .nt-grupo li { margin: 1px 0; }
  .nt-embreve li { margin: 4px 0; } .nt-embreve b { color: var(--loja-cera); }
  .nt-pe { margin-top: 14px; font: italic 12px var(--loja-texto); color: var(--loja-tinta-suave); }
  /* B — o mural da loja: um quadro de madeira com bilhetes pregados, deslizando da direita */
  .mural { position: fixed; top: 0; right: 0; bottom: 0; width: 460px; z-index: 80; padding: 18px 18px 24px; overflow: auto;
    background: linear-gradient(90deg, rgba(0,0,0,.35), rgba(0,0,0,0) 14px), repeating-linear-gradient(90deg, #5a3a22 0 46px, #4f331e 46px 92px), #4f331e;
    box-shadow: -10px 0 30px rgba(0,0,0,.6); border-left: 3px solid #2c1d12; }
  .mural h2 { font-family: var(--loja-titulo, Georgia); color: #f1dcae; margin: 0 0 2px; text-shadow: 0 2px 2px rgba(0,0,0,.6); }
  .mural .m-sub { font: italic 12.5px var(--loja-texto); color: #e2c793; margin-bottom: 12px; }
  .bilhete { position: relative; margin: 12px 4px 16px; padding: 14px 14px 10px; background: var(--loja-papel); color: var(--loja-tinta);
    box-shadow: 0 6px 12px rgba(0,0,0,.45); font-family: var(--loja-texto); font-size: 13px; line-height: 1.45; }
  .bilhete:nth-child(odd) { transform: rotate(-.6deg); } .bilhete:nth-child(even) { transform: rotate(.5deg); }
  .bilhete::before { content: ""; position: absolute; top: -6px; left: 50%; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #e6c27a, #7a5a26); box-shadow: 0 2px 2px rgba(0,0,0,.6); }
  .bilhete.embreve { background: #efe1bf; border: 1px dashed var(--loja-cera); }
  .bilhete h3 { margin: 0 0 6px; font: 600 12px var(--loja-texto); letter-spacing: .1em; text-transform: uppercase; color: var(--loja-cera); }
  .bilhete ul { margin: 0; padding-left: 16px; }
  .bilhete .m-k { font-variant: small-caps; letter-spacing: .05em; margin-right: 4px; }
  .bilhete .m-k.add { color: #3f6b2a; } .bilhete .m-k.aj { color: #8a5a12; } .bilhete .m-k.rem { color: #6a6058; }
  `;
  const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  // o ícone no topo, ao lado da Acessibilidade: um pergaminho com o número da atualização
  const ac = document.getElementById("acess-ctl");
  const btn = document.createElement("button");
  btn.type = "button"; btn.className = "som-btn notas-btn"; btn.id = "notas-btn"; btn.title = "Notas de atualização"; btn.setAttribute("aria-label", "Notas de atualização");
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 4h11a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4z"/><path d="M6 4a2 2 0 0 0-2 2v2h2M9 9h7M9 12h7M9 15h5"/></svg><span class="nb-num">${esc(window.ATUALIZACAO || "")}</span>`;
  ac.parentNode.insertBefore(btn, ac);

  const ROT = { add: "Adicionado", aj: "Ajustado", rem: "Removido" };
  const grupos = (d) => ["add", "aj", "rem"].filter(k => (d[k] || []).length);

  function opcaoA(aba) {
    const corpo = aba === "embreve"
      ? `<ul class="nt-embreve">${N.embreve.map(x => `<li><b>${esc(x[0])}</b> — ${esc(x[1])}</li>`).join("")}</ul><p class="nt-pe">Sem data prometida: a ordem pode mudar, e a lista muda junto.</p>`
      : N.datas.map(d => `<div class="nt-data">${esc(d.data)}</div>${grupos(d).map(k => `<div class="nt-grupo"><span class="nt-k ${k}">${ROT[k]}</span><ul>${d[k].map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>`).join("")}`).join("");
    const modal = document.getElementById("modal"), overlay = document.getElementById("overlay");
    modal.innerHTML = `<button class="modal-close" aria-label="Fechar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
      <div class="nt-head"><h2>Notas de atualização</h2><div class="nt-sub">Atualização ${esc(window.ATUALIZACAO || "")} · patch ${esc(CATALOG.meta.patch)}</div></div>
      <div class="nt-abas"><button class="${aba !== "embreve" ? "ativo" : ""}">Novidades</button><button class="${aba === "embreve" ? "ativo" : ""}">O que vem por aí</button></div>${corpo}`;
    overlay.classList.add("show");
  }
  function opcaoB() {
    const m = document.createElement("aside");
    m.className = "mural";
    m.innerHTML = `<h2>Mural da loja</h2><div class="m-sub">Atualização ${esc(window.ATUALIZACAO || "")} · patch ${esc(CATALOG.meta.patch)}</div>
      <div class="bilhete embreve"><h3>Em breve na loja</h3><ul>${N.embreve.map(x => `<li><b>${esc(x[0])}</b> — ${esc(x[1])}</li>`).join("")}</ul></div>
      ${N.datas.map(d => `<div class="bilhete"><h3>${esc(d.data)}</h3><ul>${grupos(d).flatMap(k => d[k].map(x => `<li><span class="m-k ${k}">${ROT[k]}</span>${esc(x)}</li>`)).join("")}</ul></div>`).join("")}`;
    document.body.appendChild(m);
  }
  window.__notasAmostra = { opcaoA, opcaoB };
})();
