const competitionSelect = document.querySelector('[data-competition]');
const teamSelect = document.querySelector('[data-team]');
const canvas = document.querySelector('[data-story-canvas]');
const statusNode = document.querySelector('[data-generator-status]');
const downloadButton = document.querySelector('[data-download]');
const shareButton = document.querySelector('[data-share]');
const themeInputs = [...document.querySelectorAll('input[name="theme"]')];
const context = canvas?.getContext('2d');

const competitions = {
  worldcup: {
    label: 'Copa do Mundo 2026',
    shortLabel: 'COPA DO MUNDO 2026',
    dataUrl: 'data/worldcup_2026.json',
    pageUrl: 'docs/worldcup_2026/index.html'
  },
  'serie-a': {
    label: 'Brasileirão Série A 2026',
    shortLabel: 'BRASILEIRÃO SÉRIE A 2026',
    dataUrl: 'data/serie_a_2026.json',
    pageUrl: 'docs/serie_a_2026/index.html'
  },
  'serie-b': {
    label: 'Brasileirão Série B 2026',
    shortLabel: 'BRASILEIRÃO SÉRIE B 2026',
    dataUrl: 'data/serie_b_2026.json',
    pageUrl: 'docs/serie_b_2026/index.html'
  }
};

const themes = {
  night: { background: '#0e1b31', surface: '#192b49', accent: '#72e0d1', text: '#ffffff', muted: '#b5c3d7' },
  energy: { background: '#ff5b35', surface: '#ffffff', accent: '#ffe45c', text: '#172033', muted: '#596273' },
  classic: { background: '#f2efe7', surface: '#ffffff', accent: '#224f94', text: '#172033', muted: '#687080' }
};

const teamTranslations = {
  Algeria: 'Argélia', Australia: 'Austrália', Austria: 'Áustria', Belgium: 'Bélgica',
  'Bosnia & Herzegovina': 'Bósnia e Herzegovina', Brazil: 'Brasil', Canada: 'Canadá',
  'Cape Verde': 'Cabo Verde', Colombia: 'Colômbia', Croatia: 'Croácia',
  'Czech Republic': 'República Tcheca', 'DR Congo': 'RD Congo', Ecuador: 'Equador',
  Egypt: 'Egito', England: 'Inglaterra', France: 'França', Germany: 'Alemanha',
  Iran: 'Irã', Iraq: 'Iraque', 'Ivory Coast': 'Costa do Marfim', Japan: 'Japão',
  Jordan: 'Jordânia', Mexico: 'México', Morocco: 'Marrocos', Netherlands: 'Holanda',
  'New Zealand': 'Nova Zelândia', Norway: 'Noruega', Panama: 'Panamá', Paraguay: 'Paraguai',
  Qatar: 'Catar', 'Saudi Arabia': 'Arábia Saudita', Scotland: 'Escócia',
  'South Africa': 'África do Sul', 'South Korea': 'Coreia do Sul', Spain: 'Espanha',
  Sweden: 'Suécia', Switzerland: 'Suíça', Tunisia: 'Tunísia', Turkey: 'Turquia',
  USA: 'Estados Unidos', Uruguay: 'Uruguai', Uzbekistan: 'Uzbequistão'
};

let normalizedMatches = [];
let cardMode = 'Próximos jogos';
let renderReady = false;

function parseBrazilianDate(value, time = '00:00') {
  const [day, month, year] = value.split('/').map(Number);
  const [hour, minute] = time.split(':').map(Number);
  return new Date(year, month - 1, day, hour || 0, minute || 0);
}

function normalizeData(key, payload) {
  const matches = payload.matches || [];
  if (key === 'worldcup') {
    return matches.map((match) => ({
      home: displayTeam(match.team1),
      away: displayTeam(match.team2),
      date: new Date(`${match.date_sp || match.date}T${match.time_sp || '00:00'}:00`),
      dateLabel: match.date_sp || match.date,
      time: match.time_sp || match.time,
      score: match.score_display || '-',
      stadium: match.ground || '',
      round: match.stage || match.round || ''
    }));
  }
  return matches.map((match) => ({
    home: match.home,
    away: match.away,
    date: parseBrazilianDate(match.date, match.time),
    dateLabel: match.date,
    time: match.time,
    score: match.score || '-',
    stadium: match.stadium || '',
    round: `${match.round}ª rodada`
  }));
}

function displayTeam(team) {
  if (/^[LW]\d+$/.test(team || '')) return 'A definir';
  return teamTranslations[team] || team;
}

function listTeams(matches) {
  return [...new Set(matches.flatMap((match) => [match.home, match.away]))]
    .filter((team) => team && team !== 'A definir')
    .sort((a, b) => a.localeCompare(b, 'pt-BR'));
}

function getSelectedMatches(team) {
  const teamMatches = normalizedMatches
    .filter((match) => match.home === team || match.away === team)
    .sort((a, b) => a.date - b.date);
  const upcoming = teamMatches.filter((match) => match.date >= new Date());
  if (upcoming.length) {
    cardMode = 'Próximos jogos';
    return upcoming.slice(0, 3);
  }
  cardMode = 'Últimos jogos';
  return teamMatches.slice(-3).reverse();
}

function selectedTheme() {
  return themes[themeInputs.find((input) => input.checked)?.value || 'night'];
}

function roundedRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function fitText(ctx, text, maxWidth, initialSize, weight = 800) {
  let size = initialSize;
  do {
    ctx.font = `${weight} ${size}px Arial, sans-serif`;
    if (ctx.measureText(text).width <= maxWidth) return size;
    size -= 2;
  } while (size > 38);
  return size;
}

function formatDate(date) {
  return new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' })
    .format(date)
    .replace('.', '')
    .toUpperCase();
}

function drawBackground(ctx, theme) {
  ctx.fillStyle = theme.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.globalAlpha = .13;
  ctx.fillStyle = theme.accent;
  ctx.beginPath();
  ctx.arc(1030, 160, 330, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(10, 1800, 360, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
}

function drawMatch(ctx, match, index, theme) {
  const x = 70;
  const y = 690 + index * 330;
  const width = 940;
  const height = 270;
  roundedRect(ctx, x, y, width, height, 34);
  ctx.fillStyle = theme.surface;
  ctx.fill();

  ctx.fillStyle = theme.accent;
  ctx.fillRect(x, y, 14, height);
  ctx.fillStyle = theme.muted;
  ctx.font = '700 28px Arial, sans-serif';
  ctx.fillText(`${formatDate(match.date)}  •  ${match.round.toUpperCase()}`, x + 50, y + 58);

  const homeSize = fitText(ctx, match.home, 570, 52, 800);
  ctx.fillStyle = theme.text;
  ctx.font = `800 ${homeSize}px Arial, sans-serif`;
  ctx.fillText(match.home, x + 50, y + 130);
  const awaySize = fitText(ctx, match.away, 570, 52, 800);
  ctx.font = `800 ${awaySize}px Arial, sans-serif`;
  ctx.fillText(match.away, x + 50, y + 198);

  ctx.fillStyle = theme.muted;
  ctx.font = '600 25px Arial, sans-serif';
  const stadium = match.stadium.length > 38 ? `${match.stadium.slice(0, 35)}…` : match.stadium;
  ctx.fillText(stadium, x + 50, y + 240);

  const hasScore = match.score && match.score !== '-';
  ctx.textAlign = 'right';
  ctx.fillStyle = theme.text;
  ctx.font = '800 58px Arial, sans-serif';
  const score = match.score.replace(/\s*\(.*/, '');
  ctx.fillText(hasScore ? score : match.time, x + width - 48, y + 145);
  ctx.fillStyle = theme.muted;
  ctx.font = '700 23px Arial, sans-serif';
  ctx.fillText(hasScore ? 'PLACAR' : 'HORÁRIO', x + width - 48, y + 185);
  ctx.textAlign = 'left';
}

function drawCard() {
  if (!context || !teamSelect?.value || !normalizedMatches.length) return;
  const team = teamSelect.value;
  const matches = getSelectedMatches(team);
  const theme = selectedTheme();
  const competition = competitions[competitionSelect.value];
  drawBackground(context, theme);

  context.fillStyle = theme.accent;
  context.font = '800 28px Arial, sans-serif';
  context.fillText(competition.shortLabel, 70, 115);
  context.fillStyle = theme.muted;
  context.font = '700 30px Arial, sans-serif';
  context.fillText(cardMode.toUpperCase(), 70, 210);
  const titleSize = fitText(context, team, 920, 108, 800);
  context.fillStyle = theme.text;
  context.font = `800 ${titleSize}px Arial, sans-serif`;
  context.fillText(team, 70, 325);

  context.strokeStyle = theme.accent;
  context.lineWidth = 8;
  context.beginPath();
  context.moveTo(70, 385);
  context.lineTo(1010, 385);
  context.stroke();

  context.fillStyle = theme.muted;
  context.font = '500 32px Arial, sans-serif';
  context.fillText('Agenda pronta para compartilhar', 70, 450);

  if (!matches.length) {
    context.fillStyle = theme.text;
    context.font = '700 48px Arial, sans-serif';
    context.fillText('Nenhum jogo encontrado.', 70, 760);
  } else {
    matches.forEach((match, index) => drawMatch(context, match, index, theme));
  }

  context.fillStyle = theme.muted;
  context.font = '600 26px Arial, sans-serif';
  context.fillText('Dados atualizados automaticamente', 70, 1790);
  context.fillStyle = theme.text;
  context.font = '800 34px Arial, sans-serif';
  context.fillText('felandim.github.io', 70, 1845);

  renderReady = matches.length > 0;
  downloadButton.disabled = !renderReady;
  shareButton.disabled = !renderReady;
  statusNode.textContent = matches.length
    ? `${cardMode}: ${matches.length} ${matches.length === 1 ? 'partida' : 'partidas'} no card.`
    : 'Nenhum jogo encontrado para este time.';
}

function updatePageUrl() {
  const params = new URLSearchParams();
  params.set('campeonato', competitionSelect.value);
  if (teamSelect.value) params.set('time', teamSelect.value);
  const theme = themeInputs.find((input) => input.checked)?.value;
  if (theme) params.set('estilo', theme);
  history.replaceState(null, '', `${location.pathname}?${params}`);
}

async function loadCompetition(preferredTeam = '') {
  const key = competitionSelect.value;
  const competition = competitions[key];
  teamSelect.disabled = true;
  downloadButton.disabled = true;
  shareButton.disabled = true;
  statusNode.textContent = `Carregando ${competition.label}…`;
  try {
    const response = await fetch(competition.dataUrl);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    normalizedMatches = normalizeData(key, await response.json());
    const teams = listTeams(normalizedMatches);
    teamSelect.replaceChildren(...teams.map((team) => new Option(team, team)));
    const defaultTeam = key === 'worldcup' && teams.includes('Brasil') ? 'Brasil' : teams[0];
    teamSelect.value = preferredTeam && teams.includes(preferredTeam) ? preferredTeam : defaultTeam;
    teamSelect.disabled = false;
    drawCard();
    updatePageUrl();
  } catch (error) {
    normalizedMatches = [];
    teamSelect.replaceChildren(new Option('Não foi possível carregar', ''));
    statusNode.textContent = 'Não foi possível carregar os jogos. Tente novamente.';
    console.error(error);
  }
}

function fileName() {
  const team = teamSelect.value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
  return `jogos-${team || 'futebol'}.png`;
}

function canvasBlob() {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png', 1));
}

downloadButton?.addEventListener('click', async () => {
  if (!renderReady) return;
  const blob = await canvasBlob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName();
  link.click();
  URL.revokeObjectURL(url);
});

shareButton?.addEventListener('click', async () => {
  if (!renderReady) return;
  const blob = await canvasBlob();
  const file = new File([blob], fileName(), { type: 'image/png' });
  const shareData = {
    title: `${teamSelect.value}: ${cardMode.toLowerCase()}`,
    text: `Veja a agenda de ${teamSelect.value}: ${location.href}`,
    files: [file]
  };
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share(shareData);
      return;
    } catch (error) {
      if (error.name === 'AbortError') return;
    }
  }
  downloadButton.click();
  statusNode.textContent = 'O compartilhamento direto não está disponível. O PNG foi baixado.';
});

competitionSelect?.addEventListener('change', () => loadCompetition());
teamSelect?.addEventListener('change', () => { drawCard(); updatePageUrl(); });
themeInputs.forEach((input) => input.addEventListener('change', () => { drawCard(); updatePageUrl(); }));

const initialParams = new URLSearchParams(location.search);
const initialCompetition = initialParams.get('campeonato');
const initialTheme = initialParams.get('estilo');
if (initialCompetition && competitions[initialCompetition]) competitionSelect.value = initialCompetition;
if (initialTheme && themes[initialTheme]) {
  const input = themeInputs.find((item) => item.value === initialTheme);
  if (input) input.checked = true;
}
loadCompetition(initialParams.get('time') || '');
