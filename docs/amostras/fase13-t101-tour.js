/* F13-T101 — amostra do tour (Leo, 02/11/2026: "o tour não deve ser algo massante").
   Injetado no app de verdade só para a captura; nada disto é código do app.
   Opção 1 — o tour curto: 6 passos no primeiro acesso, tela escurecida com o
             recorte aceso, Próximo / Pular tour / ×.
   Opção 2 — a dica na hora: sem tour corrido; na primeira vez em cada tela, 1 ou 2
             balões sem escurecer nada, que somem com "Entendi" ou com qualquer clique.
   O balão veste a tela nas duas: pergaminho na loja, ferro na forja. */
(function () {
  const css = `
  .tr-veu { position: fixed; inset: 0; z-index: 9000; pointer-events: none; }
  .tr-furo { position: fixed; z-index: 9001; pointer-events: none; border-radius: 6px;
    box-shadow: 0 0 0 9999px rgba(8, 5, 3, .74); transition: all .3s ease; }
  .tr-furo.loja { box-shadow: 0 0 0 9999px rgba(20, 12, 5, .72), 0 0 0 2px var(--loja-latao-claro), 0 0 22px 4px rgba(213,179,90,.45); }
  .tr-furo.forja { box-shadow: 0 0 0 9999px rgba(6, 4, 3, .78), 0 0 0 2px var(--forja-brasa), 0 0 26px 6px var(--forja-brasa-glow); }
  .tr-anel { position: fixed; z-index: 9001; pointer-events: none; border-radius: 8px; }
  .tr-anel.loja { box-shadow: 0 0 0 2px var(--loja-latao-claro), 0 0 18px 3px rgba(213,179,90,.55); animation: tr-pulsa 1.8s ease-in-out infinite; }
  .tr-anel.forja { box-shadow: 0 0 0 2px var(--forja-brasa), 0 0 20px 4px var(--forja-brasa-glow); animation: tr-pulsa 1.8s ease-in-out infinite; }
  @keyframes tr-pulsa { 50% { opacity: .55; } }

  .tr-balao { position: fixed; z-index: 9002; width: 330px; padding: 16px 18px 14px; box-sizing: border-box; }
  .tr-balao.curta { width: 290px; padding: 12px 14px 11px; }
  .tr-balao .tr-x { position: absolute; top: 6px; right: 8px; width: 24px; height: 24px; border: 0; background: none;
    font-size: 18px; line-height: 1; cursor: pointer; }
  .tr-balao .tr-sec { font: 600 10.5px/1 var(--loja-gravado); letter-spacing: .14em; text-transform: uppercase; margin-bottom: 6px; }
  .tr-balao h3 { margin: 0 0 6px; font: 400 21px/1.15 var(--loja-titulos); }
  .tr-balao.curta h3 { font-size: 17px; }
  .tr-balao p { margin: 0; font: 400 14.5px/1.42 var(--loja-texto); }
  .tr-balao.curta p { font-size: 13.5px; }
  .tr-pe { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
  .tr-pontos { display: flex; gap: 5px; margin-right: auto; }
  .tr-pontos i { width: 7px; height: 7px; border-radius: 50%; }
  .tr-pe .tr-pular { border: 0; background: none; padding: 0; font: 400 13px var(--loja-texto); text-decoration: underline; cursor: pointer; }
  .tr-pe .tr-ok { padding: 6px 14px; font: 600 12px var(--loja-gravado); letter-spacing: .08em; text-transform: uppercase; cursor: pointer; border-radius: 3px; }
  .tr-seta { position: absolute; width: 14px; height: 14px; transform: rotate(45deg); }

  /* pergaminho da loja */
  .tr-balao.loja { background: var(--tex-02) center/cover, var(--loja-papel); color: var(--loja-tinta);
    border: 1px solid var(--loja-papel-borda); border-radius: 4px;
    box-shadow: 0 10px 28px rgba(0,0,0,.55), inset 0 0 26px rgba(120,80,30,.35); }
  .tr-balao.loja .tr-sec { color: var(--loja-cera); }
  .tr-balao.loja .tr-x { color: var(--loja-tinta-suave); }
  .tr-balao.loja .tr-pontos i { background: rgba(44,29,18,.25); }
  .tr-balao.loja .tr-pontos i.on { background: var(--loja-cera); box-shadow: 0 0 0 1px var(--loja-cera-borda); }
  .tr-balao.loja .tr-pular { color: var(--loja-tinta-suave); }
  .tr-balao.loja .tr-ok { color: var(--loja-cera-texto); background: linear-gradient(var(--loja-cera), var(--loja-cera-borda));
    border: 1px solid var(--loja-cera-sombra); box-shadow: 0 2px 0 var(--loja-cera-sombra); }
  .tr-balao.loja .tr-seta { background: var(--loja-papel); border: 1px solid var(--loja-papel-borda); }

  /* placa de ferro da forja */
  .tr-balao.forja { background: linear-gradient(160deg, var(--forja-placa-1), var(--forja-placa-2)); color: var(--forja-texto);
    border: 1px solid var(--forja-placa-borda); border-radius: 4px;
    box-shadow: 0 10px 28px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.05), inset 0 -2px 10px rgba(255,120,30,.10); }
  .tr-balao.forja::before, .tr-balao.forja::after { content: ""; position: absolute; top: 7px; width: 6px; height: 6px; border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #8a7a6c, var(--forja-rebite) 60%, #2a221d); }
  .tr-balao.forja::before { left: 7px; } .tr-balao.forja::after { right: 34px; }
  .tr-balao.forja .tr-sec { color: var(--forja-brasa); }
  .tr-balao.forja h3 { color: var(--forja-titulo); }
  .tr-balao.forja .tr-x { color: var(--forja-texto-suave); }
  .tr-balao.forja .tr-pontos i { background: #3a3029; }
  .tr-balao.forja .tr-pontos i.on { background: var(--forja-brasa); box-shadow: 0 0 6px var(--forja-brasa-glow); }
  .tr-balao.forja .tr-pular { color: var(--forja-texto-suave); }
  .tr-balao.forja .tr-ok { color: #1a0d04; background: linear-gradient(var(--forja-brasa-clara), var(--forja-brasa));
    border: 1px solid #a24a0c; box-shadow: 0 0 10px var(--forja-brasa-glow); }
  .tr-balao.forja .tr-seta { background: var(--forja-placa-1); border: 1px solid var(--forja-placa-borda); }
  `;
  if (!document.getElementById("tr-css")) {
    const st = document.createElement("style"); st.id = "tr-css"; st.textContent = css; document.head.appendChild(st);
  }

  window.amostraTourLimpa = function () {
    document.querySelectorAll(".tr-veu, .tr-furo, .tr-anel, .tr-balao").forEach(e => e.remove());
  };

  /* opcao: 1 (tour curto) ou 2 (dica na hora); tema: "loja" | "forja";
     alvo: seletor; d: { sec, titulo, texto, passo, total, lado } */
  window.amostraTour = function (opcao, tema, alvo, d) {
    amostraTourLimpa();
    const el = document.querySelector(alvo);
    if (!el) return "sem alvo: " + alvo;
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect(), m = 6;
    const caixa = document.createElement("div");
    caixa.className = (opcao === 1 ? "tr-furo " : "tr-anel ") + tema;
    Object.assign(caixa.style, { left: (r.left - m) + "px", top: (r.top - m) + "px", width: (r.width + 2 * m) + "px", height: (r.height + 2 * m) + "px" });
    document.body.appendChild(caixa);

    const b = document.createElement("div");
    b.className = "tr-balao " + tema + (opcao === 2 ? " curta" : "");
    const pontos = opcao === 1
      ? `<span class="tr-pontos">${Array.from({ length: d.total }, (_, i) => `<i class="${i === d.passo - 1 ? "on" : ""}"></i>`).join("")}</span>`
      : `<span class="tr-pontos" style="font:400 12px var(--loja-texto);opacity:.75">${d.passo} de ${d.total} nesta tela</span>`;
    const botoes = opcao === 1
      ? `<button class="tr-pular">Pular tour</button><button class="tr-ok">${d.passo === d.total ? "Pronto" : "Próximo"}</button>`
      : `<button class="tr-pular">Sem dicas</button><button class="tr-ok">Entendi</button>`;
    b.innerHTML = `<button class="tr-x" aria-label="Fechar">×</button>
      <div class="tr-sec">${d.sec}</div><h3>${d.titulo}</h3><p>${d.texto}</p>
      <div class="tr-pe">${pontos}${botoes}</div><i class="tr-seta"></i>`;
    document.body.appendChild(b);
    const bw = b.offsetWidth, bh = b.offsetHeight, gap = 18, seta = b.querySelector(".tr-seta");
    let x, y, lado = d.lado || "direita";
    if (lado === "direita") { x = r.right + m + gap; y = r.top + r.height / 2 - bh / 2; }
    if (lado === "esquerda") { x = r.left - m - gap - bw; y = r.top + r.height / 2 - bh / 2; }
    if (lado === "baixo") { x = r.left + r.width / 2 - bw / 2; y = r.bottom + m + gap; }
    x = Math.max(12, Math.min(innerWidth - bw - 12, x)); y = Math.max(12, Math.min(innerHeight - bh - 12, y));
    Object.assign(b.style, { left: x + "px", top: y + "px" });
    const cy = Math.max(14, Math.min(bh - 28, r.top + r.height / 2 - y - 7)), cx = Math.max(14, Math.min(bw - 28, r.left + r.width / 2 - x - 7));
    if (lado === "direita") Object.assign(seta.style, { left: "-8px", top: cy + "px", borderTop: "0", borderRight: "0" });
    if (lado === "esquerda") Object.assign(seta.style, { right: "-8px", top: cy + "px", borderBottom: "0", borderLeft: "0" });
    if (lado === "baixo") Object.assign(seta.style, { top: "-8px", left: cx + "px", borderBottom: "0", borderRight: "0" });
    return "ok";
  };
})();
