(() => {
  const script = document.currentScript;
  const dataUrl = new URL("data/brasileirao_2026_insights.json", script?.src?.replace(/brasileirao\.js(?:\?.*)?$/, "") || document.baseURI);
  let insightsPromise;

  const loadInsights = () => insightsPromise ||= fetch(dataUrl).then(response => {
    if (!response.ok) throw new Error("Não foi possível carregar os dados do campeonato.");
    return response.json();
  });

  const slugify = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  function standingsRows(rows) {
    return rows.map(row => {
      const zone = row.position <= 4 ? "g4" : row.position >= 17 ? "z4" : "";
      return `<tr class="${zone}"><td><span class="br-pos ${zone}">${row.position}</span></td><th scope="row"><a href="times/${slugify(row.team)}.html">${row.team}</a></th><td>${row.points}</td><td>${row.played}</td><td>${row.wins}</td><td>${row.draws}</td><td>${row.losses}</td><td>${row.gd > 0 ? "+" : ""}${row.gd}</td></tr>`;
    }).join("");
  }

  function multiChart(rows, snapshots, round) {
    const selected = rows.slice(0, 8);
    const width = 760, height = 430, left = 48, right = 30, top = 32, bottom = 56;
    const colors = ["#dfff00", "#ff654d", "#71c7ff", "#f4aeff", "#ffffff", "#ffc857", "#79e6b0", "#a99cff"];
    const pointsFor = team => snapshots.slice(0, round).map((snapshot, index) => {
      const row = snapshot.table.find(item => item.team === team);
      const x = left + index * (width - left - right) / Math.max(round - 1, 1);
      const y = top + (row.position - 1) * (height - top - bottom) / 19;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    const lines = selected.map((row, index) => `<polyline points="${pointsFor(row.team)}" stroke="${colors[index]}"/><text x="${width - right + 4}" y="${top + (row.position - 1) * (height - top - bottom) / 19 + 4}" fill="${colors[index]}">${row.position}</text>`).join("");
    const guides = [1, 5, 10, 15, 20].map(position => {
      const y = top + (position - 1) * (height - top - bottom) / 19;
      return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"/><text x="8" y="${y + 4}">${position}º</text>`;
    }).join("");
    const legend = selected.map((row, index) => `<li><i style="--legend:${colors[index]}"></i>${row.team}</li>`).join("");
    return `<svg class="br-multi-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Evolução dos oito primeiros times até a rodada ${round}">${guides}${lines}</svg><ul class="br-chart-legend">${legend}</ul>`;
  }

  const roundSelect = document.querySelector("[data-round-select]");
  if (roundSelect) {
    loadInsights().then(data => {
      const table = document.querySelector("[data-standings-table] tbody");
      const chart = document.querySelector("[data-multi-chart]");
      const update = () => {
        const round = Number(roundSelect.value);
        const snapshot = data.snapshots.find(item => item.round === round);
        table.innerHTML = standingsRows(snapshot.table);
        chart.innerHTML = multiChart(snapshot.table, data.snapshots, round);
      };
      roundSelect.addEventListener("change", update);
      update();
    }).catch(error => document.querySelector("[data-multi-chart]").textContent = error.message);
  }

  function scorerChart(ranking) {
    const top = ranking.slice(0, 10);
    const max = Math.max(...top.map(item => item.goals), 1);
    return `<ol class="br-goal-bars">${top.map((row, index) => `<li><span>${index + 1}</span><div><strong>${row.name}</strong><small>${row.team}</small><i style="width:${(row.goals / max) * 100}%"></i></div><b>${row.goals}</b></li>`).join("")}</ol>`;
  }

  const scorerSelect = document.querySelector("[data-scorer-round-select]");
  if (scorerSelect) {
    loadInsights().then(data => {
      const table = document.querySelector("[data-scorer-table] tbody");
      const chart = document.querySelector("[data-scorer-chart]");
      const update = () => {
        const snapshot = data.scorers.find(item => item.round === Number(scorerSelect.value));
        table.innerHTML = snapshot.ranking.map((row, index) => `<tr><td>${index + 1}</td><th scope="row">${row.name}</th><td>${row.team}</td><td><strong>${row.goals}</strong></td></tr>`).join("");
        chart.innerHTML = scorerChart(snapshot.ranking);
      };
      scorerSelect.addEventListener("change", update);
      update();
    }).catch(error => document.querySelector("[data-scorer-chart]").textContent = error.message);
  }


  const comparisonRoot = document.querySelector("[data-comparison]");
  if (comparisonRoot) {
    const teamASelect = comparisonRoot.querySelector("[data-team-a]");
    const teamBSelect = comparisonRoot.querySelector("[data-team-b]");
    const summary = comparisonRoot.querySelector("[data-compare-summary]");
    const chart = comparisonRoot.querySelector("[data-compare-chart]");
    const stats = comparisonRoot.querySelector("[data-compare-stats]");
    const error = comparisonRoot.querySelector("[data-compare-error]");
    const status = comparisonRoot.querySelector("[data-compare-status]");
    const safe = value => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));

    function duelChart(profileA, profileB) {
      const width = 820, height = 430, left = 48, right = 28, top = 34, bottom = 46;
      const xFor = (index, length) => left + index * (width - left - right) / Math.max(length - 1, 1);
      const yFor = position => top + (position - 1) * (height - top - bottom) / 19;
      const line = profile => profile.history.map((row, index) => `${xFor(index, profile.history.length).toFixed(1)},${yFor(row.position).toFixed(1)}`).join(" ");
      const guides = [1, 5, 10, 15, 20].map(position => {
        const y = yFor(position);
        return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"/><text x="8" y="${y + 4}">${position}º</text>`;
      }).join("");
      return `<svg class="br-multi-chart br-duel-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Comparação da evolução de ${safe(profileA.team)} e ${safe(profileB.team)}">${guides}<polyline class="team-a" points="${line(profileA)}"/><polyline class="team-b" points="${line(profileB)}"/></svg><ul class="br-duel-legend"><li><i></i>${safe(profileA.team)}</li><li><i></i>${safe(profileB.team)}</li></ul>`;
    }

    function metricRow(label, valueA, valueB, lowerIsBetter = false, suffix = "") {
      const aWins = lowerIsBetter ? valueA < valueB : valueA > valueB;
      const bWins = lowerIsBetter ? valueB < valueA : valueB > valueA;
      return `<div><strong class="${aWins ? "is-best" : ""}">${valueA}${suffix}</strong><span>${label}</span><strong class="${bWins ? "is-best" : ""}">${valueB}${suffix}</strong></div>`;
    }

    loadInsights().then(data => {
      const params = new URLSearchParams(location.search);
      if (data.team_profiles[params.get("a")]) teamASelect.value = params.get("a");
      if (data.team_profiles[params.get("b")]) teamBSelect.value = params.get("b");

      const render = () => {
        const slugA = teamASelect.value;
        const slugB = teamBSelect.value;
        if (slugA === slugB) {
          error.textContent = "Escolha dois times diferentes.";
          summary.innerHTML = "";
          chart.innerHTML = "";
          stats.innerHTML = "";
          return;
        }
        error.textContent = "";
        const profileA = data.team_profiles[slugA];
        const profileB = data.team_profiles[slugB];
        const a = profileA.current;
        const b = profileB.current;
        const rateA = a.played ? Math.round(a.points / (a.played * 3) * 100) : 0;
        const rateB = b.played ? Math.round(b.points / (b.played * 3) * 100) : 0;
        const leader = a.position < b.position ? profileA : profileB;
        const trailer = leader === profileA ? profileB : profileA;
        const positionGap = Math.abs(a.position - b.position);
        const pointGap = Math.abs(a.points - b.points);

        summary.innerHTML = `<article><span>${a.position}º</span><h2>${safe(profileA.team)}</h2><p>${a.points} pontos · ${rateA}% de aproveitamento</p></article><div><strong>${safe(leader.team)}</strong><p>está ${positionGap} ${positionGap === 1 ? "posição" : "posições"} e ${pointGap} ${pointGap === 1 ? "ponto" : "pontos"} à frente de ${safe(trailer.team)}.</p></div><article><span>${b.position}º</span><h2>${safe(profileB.team)}</h2><p>${b.points} pontos · ${rateB}% de aproveitamento</p></article>`;
        chart.innerHTML = duelChart(profileA, profileB);
        stats.innerHTML = `<h2>Números atuais</h2>${metricRow("Posição", a.position, b.position, true, "º")}${metricRow("Pontos", a.points, b.points)}${metricRow("Vitórias", a.wins, b.wins)}${metricRow("Saldo de gols", a.gd, b.gd)}${metricRow("Gols marcados", a.gf, b.gf)}${metricRow("Aproveitamento", rateA, rateB, false, "%")}`;
        const url = new URL(location.href);
        url.searchParams.set("a", slugA);
        url.searchParams.set("b", slugB);
        history.replaceState(null, "", url);
        status.textContent = "";
      };

      teamASelect.addEventListener("change", render);
      teamBSelect.addEventListener("change", render);
      render();

      comparisonRoot.querySelector("[data-copy-comparison]")?.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(location.href);
          status.textContent = "Link copiado.";
        } catch {
          status.textContent = "Não foi possível copiar automaticamente.";
        }
      });
      comparisonRoot.querySelector("[data-share-comparison]")?.addEventListener("click", async () => {
        const shareData = { title: "Comparador de times do Brasileirão 2026", text: `${teamASelect.options[teamASelect.selectedIndex].text} × ${teamBSelect.options[teamBSelect.selectedIndex].text}`, url: location.href };
        if (navigator.share) {
          try {
            await navigator.share(shareData);
            status.textContent = "Comparação compartilhada.";
          } catch (shareError) {
            if (shareError.name !== "AbortError") status.textContent = "Não foi possível compartilhar.";
          }
        } else {
          try {
            await navigator.clipboard.writeText(location.href);
            status.textContent = "Link copiado.";
          } catch {
            status.textContent = "Use “Copiar link”.";
          }
        }
      });
    }).catch(loadError => error.textContent = loadError.message);
  }

  function drawCard(canvas) {
    const context = canvas.getContext("2d");
    const team = canvas.dataset.team;
    const position = Number(canvas.dataset.position);
    const points = Number(canvas.dataset.points);
    const round = Number(canvas.dataset.round);
    const history = JSON.parse(canvas.dataset.history);
    const width = canvas.width, height = canvas.height;
    context.fillStyle = "#101714";
    context.fillRect(0, 0, width, height);
    context.fillStyle = "#dfff00";
    context.fillRect(0, 0, width, 34);
    context.fillRect(72, 112, 104, 104);
    context.fillStyle = "#101714";
    context.font = "900 30px system-ui";
    context.textAlign = "center";
    context.fillText("R/R", 124, 178);
    context.textAlign = "left";
    context.fillStyle = "#f6f4ec";
    context.font = "800 28px system-ui";
    context.fillText("BRASILEIRÃO 2026", 206, 162);
    context.fillStyle = "#8f9b94";
    context.font = "700 22px system-ui";
    context.fillText(`EVOLUÇÃO ATÉ A RODADA ${round}`, 206, 198);
    context.fillStyle = "#f6f4ec";
    context.font = "900 82px system-ui";
    const words = team.split(" ");
    let line = "", y = 390;
    words.forEach(word => {
      const next = `${line} ${word}`.trim();
      if (context.measureText(next).width > width - 144 && line) { context.fillText(line, 72, y); line = word; y += 92; } else line = next;
    });
    context.fillText(line, 72, y);
    const chartTop = 650, chartBottom = 1370, chartLeft = 84, chartRight = width - 84;
    context.strokeStyle = "#35413b";
    context.lineWidth = 2;
    [1, 5, 10, 15, 20].forEach(value => {
      const guideY = chartTop + (value - 1) * (chartBottom - chartTop) / 19;
      context.beginPath(); context.moveTo(chartLeft, guideY); context.lineTo(chartRight, guideY); context.stroke();
      context.fillStyle = "#7c8982"; context.font = "700 20px system-ui"; context.fillText(`${value}º`, chartLeft, guideY - 10);
    });
    context.strokeStyle = "#dfff00";
    context.lineWidth = 12;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.beginPath();
    history.forEach((row, index) => {
      const x = chartLeft + index * (chartRight - chartLeft) / Math.max(history.length - 1, 1);
      const pointY = chartTop + (row.position - 1) * (chartBottom - chartTop) / 19;
      if (index) context.lineTo(x, pointY); else context.moveTo(x, pointY);
    });
    context.stroke();
    context.fillStyle = "#dfff00";
    context.beginPath();
    const lastY = chartTop + (position - 1) * (chartBottom - chartTop) / 19;
    context.arc(chartRight, lastY, 20, 0, Math.PI * 2); context.fill();
    context.fillStyle = "#f6f4ec";
    context.font = "900 104px system-ui";
    context.fillText(`${position}º`, 72, 1580);
    context.fillStyle = "#dfff00";
    context.font = "900 104px system-ui";
    context.fillText(`${points}`, 610, 1580);
    context.fillStyle = "#8f9b94";
    context.font = "800 24px system-ui";
    context.fillText("POSIÇÃO ATUAL", 76, 1630);
    context.fillText("PONTOS", 614, 1630);
    context.fillStyle = "#f6f4ec";
    context.font = "700 26px system-ui";
    context.fillText("felandim.github.io", 72, 1815);
    context.textAlign = "right";
    context.fillStyle = "#8f9b94";
    context.fillText("A TABELA TEM MEMÓRIA.", width - 72, 1815);
  }

  const card = document.querySelector("[data-evolution-card]");
  if (card) {
    drawCard(card);
    const status = document.querySelector("[data-card-status]");
    const filename = `evolucao-${slugify(card.dataset.team)}-brasileirao-2026.png`;
    const blob = () => new Promise(resolve => card.toBlob(resolve, "image/png"));
    document.querySelector("[data-download-card]")?.addEventListener("click", async () => {
      const url = URL.createObjectURL(await blob());
      const link = document.createElement("a"); link.href = url; link.download = filename; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = "Card baixado em PNG.";
    });
    document.querySelector("[data-share-card]")?.addEventListener("click", async () => {
      const file = new File([await blob()], filename, { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: `Evolução do ${card.dataset.team}` });
        status.textContent = "Card compartilhado.";
      } else {
        status.textContent = "O compartilhamento direto não está disponível neste navegador. Use “Baixar card”.";
      }
    });
  }
})();
