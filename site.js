document.querySelectorAll('[data-current-year]').forEach((node) => {
  node.textContent = new Date().getFullYear();
});

const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

if (location.hostname === 'felandim.github.io' && !document.querySelector('script[data-domain="felandim.github.io"]')) {
  const analytics = document.createElement('script');
  analytics.defer = true;
  analytics.dataset.domain = 'felandim.github.io';
  analytics.src = 'https://plausible.io/js/script.js';
  document.head.append(analytics);
}

const filterButtons = document.querySelectorAll('[data-project-filter]');
const filterCards = document.querySelectorAll('[data-project-category]');

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const category = button.dataset.projectFilter;
    filterButtons.forEach((item) => item.classList.remove('active'));
    button.classList.add('active');
    filterCards.forEach((card) => {
      card.hidden = category !== 'todos' && card.dataset.projectCategory !== category;
    });
  });
});

(() => {
  const canvas = document.querySelector('[data-evolution-card]');
  const shareSection = document.querySelector('.br-share-section');
  if (!canvas || !shareSection || document.querySelector('.team-details')) return;

  const stylesheetHref = '../../brasileirao-team-pages.css';
  if (!document.querySelector(`link[href="${stylesheetHref}"]`)) {
    const stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = stylesheetHref;
    document.head.append(stylesheet);
  }

  let history = [];
  try {
    history = JSON.parse(canvas.dataset.history || '[]');
  } catch {
    return;
  }
  if (!history.length) return;

  const totals = [...document.querySelectorAll('.br-split-stats article')].reduce(
    (result, article) => {
      const text = article.textContent.replace(/\s+/g, ' ');
      const form = text.match(/(\d+)V\s*·\s*(\d+)E\s*·\s*(\d+)D/);
      const goals = text.match(/(\d+)\s+gols feitos\s*·\s*(\d+)\s+sofridos/);
      if (form) result.played += Number(form[1]) + Number(form[2]) + Number(form[3]);
      if (goals) {
        result.gf += Number(goals[1]);
        result.ga += Number(goals[2]);
      }
      return result;
    },
    { played: 0, gf: 0, ga: 0 },
  );

  const team = canvas.dataset.team;
  const points = Number(canvas.dataset.points || 0);
  const best = Math.min(...history.map((item) => Number(item.position)));
  const worst = Math.max(...history.map((item) => Number(item.position)));
  const percentage = totals.played ? `${((points / (totals.played * 3)) * 100).toFixed(1).replace('.', ',')}%` : '0,0%';
  const average = (value) => (totals.played ? (value / totals.played).toFixed(2) : '0');

  const teams = [
    ['Athletico-PR', 'athletico-pr'], ['Atlético-MG', 'atletico-mg'], ['Bahia', 'bahia'],
    ['Botafogo', 'botafogo'], ['Bragantino', 'bragantino'], ['Chapecoense', 'chapecoense'],
    ['Corinthians', 'corinthians'], ['Coritiba', 'coritiba'], ['Cruzeiro', 'cruzeiro'],
    ['Flamengo', 'flamengo'], ['Fluminense', 'fluminense'], ['Grêmio', 'gremio'],
    ['Internacional', 'internacional'], ['Mirassol', 'mirassol'], ['Palmeiras', 'palmeiras'],
    ['Remo', 'remo'], ['Santos', 'santos'], ['São Paulo', 'sao-paulo'], ['Vasco', 'vasco'],
    ['Vitória', 'vitoria'],
  ];
  const teamIndex = teams.findIndex(([name]) => name === team);
  const previous = teams[(teamIndex - 1 + teams.length) % teams.length];
  const next = teams[(teamIndex + 1) % teams.length];

  let previousPosition = null;
  let previousPoints = 0;
  const rows = history.map((item) => {
    const position = Number(item.position);
    const currentPoints = Number(item.points);
    const delta = previousPosition === null ? 0 : previousPosition - position;
    const movement = delta > 0 ? `▲ ${delta}` : delta < 0 ? `▼ ${Math.abs(delta)}` : '—';
    const movementClass = delta > 0 ? ' up' : delta < 0 ? ' down' : '';
    const row = `<tr><td>${item.round}</td><td><strong>${position}º</strong></td><td class="movement${movementClass}">${movement}</td><td>${currentPoints}</td><td>+${currentPoints - previousPoints}</td></tr>`;
    previousPosition = position;
    previousPoints = currentPoints;
    return row;
  }).join('');

  const section = document.createElement('section');
  section.className = 'br-section team-details';
  section.innerHTML = `<div class="br-shell"><header><div><p class="br-kicker">Raio-x da campanha</p><h2>${escapeHtml(team)} em números</h2><p>Desempenho consolidado após ${totals.played} partidas.</p></div><a href="../classificacao-rodada-a-rodada.html">Ver classificação completa →</a></header><div class="team-kpis"><article><span>Aproveitamento</span><strong>${percentage}</strong><small>${totals.played} jogos</small></article><article><span>Gols marcados</span><strong>${totals.gf}</strong><small>${average(totals.gf)} por jogo</small></article><article><span>Gols sofridos</span><strong>${totals.ga}</strong><small>${average(totals.ga)} por jogo</small></article><article><span>Melhor posição</span><strong>${best}º</strong><small>Pior posição: ${worst}º</small></article></div><div class="team-history"><p class="br-kicker">Histórico completo</p><h2>Posição e pontos após cada rodada</h2><p>A variação compara a posição com a rodada anterior.</p><div class="br-table-wrap"><table class="br-table"><thead><tr><th>Rodada</th><th>Posição</th><th>Variação</th><th>Pontos</th><th>Na rodada</th></tr></thead><tbody>${rows}</tbody></table></div></div><nav class="team-page-nav" aria-label="Navegar entre times"><a href="${previous[1]}.html">← ${previous[0]}</a><a href="../index.html#times">Todos os times</a><a href="${next[1]}.html">${next[0]} →</a></nav></div>`;
  shareSection.before(section);
})();

(() => {
  document.querySelectorAll('.br-nav nav').forEach((nav) => {
    if (nav.querySelector('[data-create-card-link]')) return;
    const link = document.createElement('a');
    link.href = `${location.pathname.includes('/brasileirao/times/') || location.pathname.includes('/brasileirao/rodadas/') ? '../../' : location.pathname.includes('/brasileirao/') ? '../' : ''}gerador-card-futebol.html?campeonato=serie-a`;
    link.textContent = 'Criar card';
    link.dataset.createCardLink = '';
    nav.append(link);
  });

  const canvas = document.querySelector('[data-evolution-card]');
  const shareSection = document.querySelector('.br-share-section');
  if (!canvas || !shareSection || document.querySelector('[data-team-game-cards]')) return;

  const team = canvas.dataset.team;
  const encodedTeam = encodeURIComponent(team);
  const section = document.createElement('section');
  section.className = 'br-section br-section-soft';
  section.dataset.teamGameCards = '';
  section.innerHTML = `<div class="br-shell"><p class="br-kicker">Cards de jogos</p><h2>Compartilhe os jogos do ${escapeHtml(team)}</h2><p>Gere um card vertical pronto para Instagram com três partidas.</p><div class="br-actions"><a class="br-button br-button-hot" href="../../gerador-card-futebol.html?campeonato=serie-a&time=${encodedTeam}&modo=upcoming">Próximos 3 jogos</a><a class="br-button" href="../../gerador-card-futebol.html?campeonato=serie-a&time=${encodedTeam}&modo=recent">Últimos 3 jogos</a></div></div>`;
  shareSection.before(section);
})();
