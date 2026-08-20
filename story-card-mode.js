const cardModeSelect = document.querySelector('[data-card-mode]');

function completedMatch(match) {
  return Boolean(match.score && match.score !== '-');
}

getSelectedMatches = function getSelectedMatchesByMode(team) {
  const teamMatches = normalizedMatches
    .filter((match) => match.home === team || match.away === team)
    .sort((a, b) => a.date - b.date);

  if (cardModeSelect?.value === 'recent') {
    cardMode = 'Últimos jogos';
    return teamMatches.filter(completedMatch).slice(-3).reverse();
  }

  const upcoming = teamMatches.filter(
    (match) => !completedMatch(match) && match.date >= new Date()
  );
  if (upcoming.length) {
    cardMode = 'Próximos jogos';
    return upcoming.slice(0, 3);
  }

  // Mantém o comportamento anterior quando a competição não tem mais jogos futuros.
  cardMode = 'Últimos jogos';
  return teamMatches.filter(completedMatch).slice(-3).reverse();
};

updatePageUrl = function updatePageUrlWithMode() {
  const params = new URLSearchParams();
  params.set('campeonato', competitionSelect.value);
  if (teamSelect.value) params.set('time', teamSelect.value);
  if (cardModeSelect?.value) params.set('modo', cardModeSelect.value);
  const theme = themeInputs.find((input) => input.checked)?.value;
  if (theme) params.set('estilo', theme);
  history.replaceState(null, '', `${location.pathname}?${params}`);
};

fileName = function fileNameWithMode() {
  const team = teamSelect.value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
  const mode = cardModeSelect?.value === 'recent' ? 'ultimos-jogos' : 'proximos-jogos';
  return `${mode}-${team || 'futebol'}.png`;
};

const modeParams = new URLSearchParams(location.search);
const initialMode = modeParams.get('modo');
if (cardModeSelect && ['upcoming', 'recent'].includes(initialMode)) {
  cardModeSelect.value = initialMode;
}

cardModeSelect?.addEventListener('change', () => {
  drawCard();
  updatePageUrl();
});
