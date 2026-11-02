/* F13-T106 — amostra: onde o mapa mora na build (item 9 do roteiro). Injetado no app de verdade só para
   a captura; nada disto é código do app.
   Opção A — a mesa de guerra: uma seção da forja, entre a barra da build e as caixas, com as abas
             Visão · Selva · Farm e as ferramentas ao lado.
   Opção B — o mapa aberto sobre a bigorna: o botão "Mapa" da forja abre o mapa grande por cima, preso
             por grampos de ferro, com as ferramentas à direita; o Esc fecha.
   A névoa já é a de verdade: cada célula do data/mapa.js dentro do raio da sentinela é vista só se a linha
   até ela não cruza parede, e arbusto só se vê de dentro dele. As sentinelas, as marcas e a rota da selva
   são anotações de exemplo (o que a pessoa poria). */
(function () {
  const G = window.MAPA;
  const T = G.celula, LX = G.nx * T, LZ = G.nz * T;
  const bit = (b64) => { const s = atob(b64); return (i) => (s.charCodeAt(i >> 3) >> (i & 7)) & 1; };
  const parede = bit(G.paredes), arbusto = bit(G.arbustos);
  const IMG = "https://ddragon.leagueoflegends.com/cdn/" + (CATALOG.meta.patch || "16.21.1") + "/img/map/map11.png";

  // quais células uma sentinela em (x, z) vê, até o raio r (unidades do jogo)
  function visao(x, z, r) {
    const cx = Math.floor((x - G.min[0]) / T), cz = Math.floor((z - G.min[1]) / T), n = Math.ceil(r / T);
    const naMoita = arbusto(cz * G.nx + cx), vistos = [];
    for (let dz = -n; dz <= n; dz++) for (let dx = -n; dx <= n; dx++) {
      if ((dx * dx + dz * dz) * T * T > r * r) continue;
      const k = cx + dx, w = cz + dz;
      if (k < 0 || w < 0 || k >= G.nx || w >= G.nz) continue;
      const i = w * G.nx + k;
      if (arbusto(i) && !naMoita) continue;
      let ok = true;
      const passos = Math.max(Math.abs(dx), Math.abs(dz));
      for (let s = 1; s < passos && ok; s++) {
        const a = Math.round(cx + dx * s / passos), b = Math.round(cz + dz * s / passos);
        if (parede(b * G.nx + a)) ok = false;
      }
      if (ok && !parede(i)) vistos.push([k, w]);
    }
    return vistos;
  }

  // o mapa desenhado num quadro de lado L: a imagem, a névoa expulsa pelas sentinelas, os anéis ciano, as marcas
  function desenhar(L, coisas) {
    const caixa = document.createElement("div");
    caixa.style.cssText = "position:relative;width:" + L + "px;height:" + L + "px";
    const img = new Image(); img.src = IMG; img.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
    const nevoa = document.createElement("canvas"); nevoa.width = nevoa.height = L;
    nevoa.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
    const px = (x) => (x - G.min[0]) / LX * L, pz = (z) => L - (z - G.min[1]) / LZ * L;
    const c = nevoa.getContext("2d");
    const furo = document.createElement("canvas"); furo.width = furo.height = L;
    const f = furo.getContext("2d"); f.fillStyle = "#fff";
    const cel = T / LX * L;
    coisas.sentinelas.forEach((s) => visao(s.x, s.z, s.r).forEach(([k, w]) => {
      f.beginPath(); f.arc((k + .5) * cel, L - (w + .5) * cel, cel * .95, 0, 7); f.fill();
    }));
    // a névoa: a arte de névoa do próprio jogo (o fogofwaroverlay do Community Dragon) por cima de um véu
    // escuro, e a visão das sentinelas recortada com a borda esfumada
    const veu = new Image();
    veu.onload = () => {
      c.fillStyle = "rgba(8,12,22,.5)"; c.fillRect(0, 0, L, L);
      c.globalAlpha = .9; c.drawImage(veu, 0, 0, L, L); c.globalAlpha = 1;
      c.save(); c.globalCompositeOperation = "destination-out"; c.filter = "blur(" + Math.max(1.5, cel * .6) + "px)";
      c.drawImage(furo, 0, 0); c.restore();
    };
    veu.src = "https://raw.communitydragon.org/latest/game/assets/maps/info/map11/fogofwaroverlay.png";
    caixa.append(img, nevoa);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + L + " " + L); svg.style.cssText = "position:absolute;inset:0;width:100%;height:100%;overflow:visible";
    let h = "";
    coisas.sentinelas.forEach((s) => {
      h += '<circle cx="' + px(s.x) + '" cy="' + pz(s.z) + '" r="' + (s.r / LX * L) + '" fill="none" stroke="#3ee8ff" stroke-width="1.5" stroke-dasharray="5 4" opacity=".9"/>';
      h += '<g transform="translate(' + px(s.x) + ',' + pz(s.z) + ')"><circle r="7" fill="' + (s.controle ? "#d8434b" : "#e8c35a") + '" stroke="#1a0d04" stroke-width="1.5"/><path d="M0 -4 L3 3 L-3 3Z" fill="#1a0d04"/></g>';
    });
    if (coisas.rota) {
      const pts = coisas.rota.map((p) => px(p[0]) + "," + pz(p[1])).join(" ");
      h += '<polyline points="' + pts + '" fill="none" stroke="#ffb257" stroke-width="2.5" stroke-dasharray="7 5" opacity=".95"/>';
      coisas.rota.forEach((p, i) => { h += '<g transform="translate(' + px(p[0]) + ',' + pz(p[1]) + ')"><circle r="10" fill="#2a1a0f" stroke="#ffb257" stroke-width="2"/><text text-anchor="middle" dy="4" font-family="Cinzel,Georgia,serif" font-size="11" font-weight="700" fill="#ffd27a">' + (i + 1) + "</text></g>"; });
    }
    svg.innerHTML = h; caixa.append(svg);
    return caixa;
  }

  // as posições do exemplo escorregam para o chão mais próximo (posta numa parede, a sentinela não vê nada)
  function noChao(s) {
    const cx = Math.floor((s.x - G.min[0]) / T), cz = Math.floor((s.z - G.min[1]) / T);
    for (let d = 0; d < 12; d++) for (let dz = -d; dz <= d; dz++) for (let dx = -d; dx <= d; dx++) {
      const i = (cz + dz) * G.nx + cx + dx;
      if (!parede(i) && !arbusto(i)) return Object.assign({}, s, { x: G.min[0] + (cx + dx + .5) * T, z: G.min[1] + (cz + dz + .5) * T });
    }
    return s;
  }
  const EXEMPLO = {
    sentinelas: [{ x: 9000, z: 5300, r: 900 }, { x: 5950, z: 9100, r: 900, controle: true }, { x: 10400, z: 3150, r: 900 }].map(noChao),
    rota: [[3800, 7900], [3700, 6450], [6900, 5400], [7850, 4000], [8350, 2650], [9850, 4400]]
  };
  const ferramentas = (tema) => {
    const b = (t, on) => '<button type="button" style="display:flex;align-items:center;gap:8px;width:100%;padding:8px 10px;margin-bottom:6px;border-radius:3px;cursor:pointer;font:600 11px var(--loja-gravado);letter-spacing:.1em;text-transform:uppercase;'
      + (on ? "background:linear-gradient(var(--forja-brasa-clara),var(--forja-brasa));color:#1a0d04;border:1px solid #a24a0c" : "background:var(--forja-molde-2);color:var(--forja-texto);border:1px solid var(--forja-placa-borda)") + '">' + t + "</button>";
    return '<div style="width:190px;flex:none">'
      + '<div style="font:600 10.5px var(--loja-gravado);letter-spacing:.14em;text-transform:uppercase;color:var(--forja-brasa);margin:2px 0 8px">Pôr no mapa</div>'
      + b('<i style="width:10px;height:10px;border-radius:50%;background:#e8c35a"></i>Sentinela', true) + b('<i style="width:10px;height:10px;border-radius:50%;background:#d8434b"></i>Sent. de Controle') + b("① Marca numerada")
      + '<div style="font:600 10.5px var(--loja-gravado);letter-spacing:.14em;text-transform:uppercase;color:var(--forja-brasa);margin:14px 0 8px">Mostrar</div>'
      + '<label style="display:flex;gap:8px;align-items:center;color:var(--forja-texto);font:13px var(--loja-texto);margin-bottom:6px"><input type="checkbox" checked> Névoa de guerra</label>'
      + '<label style="display:flex;gap:8px;align-items:center;color:var(--forja-texto);font:13px var(--loja-texto);margin-bottom:6px"><input type="checkbox" checked> Raio em ciano</label>'
      + '<label style="display:flex;gap:8px;align-items:center;color:var(--forja-texto);font:13px var(--loja-texto)"><input type="checkbox"> Alcance das torres</label>'
      + '<p style="color:var(--forja-texto-suave);font:italic 12px var(--loja-texto);margin-top:14px">Clique para pôr; clique de novo para tirar. A roda aproxima.</p></div>';
  };
  const abas = (ativa) => '<div style="display:flex;gap:6px;margin-bottom:10px">' + ["Visão", "Selva", "Farm"].map((a) =>
    '<span style="padding:6px 14px;font:600 11px var(--loja-gravado);letter-spacing:.12em;text-transform:uppercase;border-radius:3px 3px 0 0;'
    + (a === ativa ? "background:var(--forja-placa-1);color:var(--forja-titulo);border:1px solid var(--forja-brasa);border-bottom:0" : "color:var(--forja-texto-suave);border:1px solid var(--forja-placa-borda);border-bottom:0") + '">' + a + "</span>").join("") + "</div>";

  window.amostraMapaLimpa = function () { document.querySelectorAll(".am-mapa").forEach((e) => e.remove()); };

  window.amostraMapa = function (opcao) {
    amostraMapaLimpa();
    if (opcao === "A") {
      const sec = document.createElement("section");
      sec.className = "am-mapa";
      sec.style.cssText = "margin:14px 0;padding:14px 16px 16px;background:linear-gradient(160deg,var(--forja-placa-1),var(--forja-placa-2));border:1px solid var(--forja-placa-borda);border-radius:4px;box-shadow:0 8px 22px rgba(0,0,0,.5),inset 0 -2px 10px rgba(255,120,30,.08)";
      sec.innerHTML = '<div style="display:flex;align-items:baseline;gap:14px;margin-bottom:8px"><h3 style="margin:0;font:400 20px var(--loja-titulos);color:var(--forja-titulo)">A mesa de guerra</h3><span style="color:var(--forja-texto-suave);font:italic 13px var(--loja-texto)">o mapa da build — visão, a primeira volta da selva e o farm</span><span style="margin-left:auto;color:var(--forja-texto-suave);font:12px var(--loja-texto)">recolher ▴</span></div>'
        + abas("Visão") + '<div class="am-corpo" style="display:flex;gap:16px;align-items:flex-start"></div>';
      const corpo = sec.querySelector(".am-corpo");
      const moldura = document.createElement("div");
      moldura.style.cssText = "padding:6px;background:#0c0907;border:1px solid var(--forja-placa-borda);border-radius:3px;box-shadow:inset 0 0 0 1px #000";
      moldura.append(desenhar(470, EXEMPLO));
      corpo.innerHTML = ferramentas("forja");
      corpo.prepend(moldura);
      const ref = document.getElementById("build-totals");
      ref.parentNode.insertBefore(sec, ref);
      sec.scrollIntoView({ block: "start" });
      window.scrollBy(0, -12);
      return "ok";
    }
    // B: o mapa aberto sobre a bigorna
    const veu = document.createElement("div");
    veu.className = "am-mapa";
    veu.style.cssText = "position:fixed;inset:0;z-index:950;background:rgba(6,4,3,.72);display:flex;align-items:center;justify-content:center";
    const mesa = document.createElement("div");
    mesa.style.cssText = "position:relative;display:flex;gap:18px;padding:22px 22px 20px;background:var(--tex-02) center/cover,var(--loja-papel);border:1px solid var(--loja-papel-borda);border-radius:4px;box-shadow:0 18px 50px rgba(0,0,0,.7),inset 0 0 40px rgba(120,80,30,.4)";
    const grampo = (lado) => '<i style="position:absolute;top:-10px;' + lado + ':40px;width:46px;height:20px;background:linear-gradient(#5a4d42,#2a221d);border:1px solid #1a1512;border-radius:3px;box-shadow:0 3px 6px rgba(0,0,0,.6)"></i>';
    mesa.innerHTML = grampo("left") + grampo("right")
      + '<button type="button" style="position:absolute;top:8px;right:12px;border:0;background:none;font-size:22px;color:var(--loja-tinta-suave);cursor:pointer">×</button>';
    const esq = document.createElement("div");
    esq.innerHTML = '<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:8px"><h3 style="margin:0;font:400 22px var(--loja-titulos);color:var(--loja-tinta)">O mapa de ' + (build.name || "Build") + '</h3><span style="color:var(--loja-cera);font:600 10.5px var(--loja-gravado);letter-spacing:.14em;text-transform:uppercase">Visão</span></div>';
    const moldura = document.createElement("div");
    moldura.style.cssText = "padding:5px;background:#1c120b;border-radius:2px;box-shadow:0 2px 8px rgba(0,0,0,.5)";
    moldura.append(desenhar(Math.min(700, innerHeight - 170), EXEMPLO));
    esq.append(moldura);
    const dir = document.createElement("div");
    dir.style.cssText = "padding:14px;background:linear-gradient(160deg,var(--forja-placa-1),var(--forja-placa-2));border:1px solid var(--forja-placa-borda);border-radius:3px;align-self:stretch";
    dir.innerHTML = abas("Visão") + ferramentas("forja");
    mesa.append(esq, dir);
    veu.append(mesa);
    document.body.append(veu);
    return "ok";
  };
})();
