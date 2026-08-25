const teamPalettes = {
  // Brasileirão Série A 2026
  'Athletico-PR': { background: '#111111', surface: '#25171a', accent: '#d71920', text: '#ffffff', muted: '#d9c8cb' },
  'Atlético-MG': { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#cfcfcf' },
  Bahia: { background: '#003a78', surface: '#0a2b57', accent: '#e3222f', text: '#ffffff', muted: '#c8d8eb' },
  Botafogo: { background: '#090909', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#cfcfcf' },
  Bragantino: { background: '#171717', surface: '#292929', accent: '#e31b23', text: '#ffffff', muted: '#d4d4d4' },
  Chapecoense: { background: '#075b35', surface: '#0d7042', accent: '#ffffff', text: '#ffffff', muted: '#cce6d8' },
  Corinthians: { background: '#111111', surface: '#262626', accent: '#d71920', text: '#ffffff', muted: '#d1d1d1' },
  Coritiba: { background: '#075c34', surface: '#0b7542', accent: '#ffffff', text: '#ffffff', muted: '#c9e6d7' },
  Cruzeiro: { background: '#003b83', surface: '#0a4e9b', accent: '#ffffff', text: '#ffffff', muted: '#c8d9ef' },
  Flamengo: { background: '#141414', surface: '#2a1818', accent: '#d71920', text: '#ffffff', muted: '#ddcaca' },
  Fluminense: { background: '#5b1530', surface: '#294d3a', accent: '#ffffff', text: '#ffffff', muted: '#e2d0d7' },
  Grêmio: { background: '#0a2338', surface: '#123b5c', accent: '#59b6e8', text: '#ffffff', muted: '#c7dae7' },
  Internacional: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  Mirassol: { background: '#07552f', surface: '#0d6a3b', accent: '#f5d328', text: '#ffffff', muted: '#d5e6da' },
  Palmeiras: { background: '#06472d', surface: '#0b5d38', accent: '#ffffff', text: '#ffffff', muted: '#c9dfd3' },
  Remo: { background: '#062d63', surface: '#0b4387', accent: '#ffffff', text: '#ffffff', muted: '#c7d7ea' },
  Santos: { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#d0d0d0' },
  'São Paulo': { background: '#111111', surface: '#272727', accent: '#e3222f', text: '#ffffff', muted: '#d3d3d3' },
  Vasco: { background: '#0b0b0b', surface: '#252525', accent: '#d71920', text: '#ffffff', muted: '#d0d0d0' },
  Vitória: { background: '#151515', surface: '#2b1919', accent: '#d71920', text: '#ffffff', muted: '#dbcaca' },

  // Clubes que aparecem na Série B / bases do projeto
  'América-MG': { background: '#064c2d', surface: '#0a6538', accent: '#ffffff', text: '#ffffff', muted: '#c8dfd2' },
  'Athletic Club': { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#d0d0d0' },
  'Atlético-GO': { background: '#151515', surface: '#2b1919', accent: '#d71920', text: '#ffffff', muted: '#dbcaca' },
  Amazonas: { background: '#171717', surface: '#292929', accent: '#f5c518', text: '#ffffff', muted: '#d5d5d5' },
  Avaí: { background: '#063f77', surface: '#0b579c', accent: '#ffffff', text: '#ffffff', muted: '#c9dced' },
  'Botafogo-SP': { background: '#151515', surface: '#2a2020', accent: '#d71920', text: '#ffffff', muted: '#dacccc' },
  Ceará: { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#d0d0d0' },
  CRB: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  Criciúma: { background: '#171717', surface: '#292929', accent: '#f3c51d', text: '#ffffff', muted: '#d4d4d4' },
  Cuiabá: { background: '#07552f', surface: '#0d6a3b', accent: '#f6d51f', text: '#ffffff', muted: '#d5e6da' },
  Fortaleza: { background: '#053a78', surface: '#0a4e99', accent: '#e3222f', text: '#ffffff', muted: '#c8d9ec' },
  Goiás: { background: '#075b35', surface: '#0d7042', accent: '#ffffff', text: '#ffffff', muted: '#cce6d8' },
  Juventude: { background: '#075b35', surface: '#0d7042', accent: '#ffffff', text: '#ffffff', muted: '#cce6d8' },
  Náutico: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  Novorizontino: { background: '#171717', surface: '#292929', accent: '#f3c51d', text: '#ffffff', muted: '#d4d4d4' },
  'Operário-PR': { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#d0d0d0' },
  Paysandu: { background: '#063f77', surface: '#0b579c', accent: '#ffffff', text: '#ffffff', muted: '#c9dced' },
  'Ponte Preta': { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#d0d0d0' },
  Sport: { background: '#151515', surface: '#2b1919', accent: '#d71920', text: '#ffffff', muted: '#dbcaca' },
  'Vila Nova': { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },

  // Seleções — nomes já traduzidos pelo gerador
  Argélia: { background: '#075b35', surface: '#0d7042', accent: '#ffffff', text: '#ffffff', muted: '#cce6d8' },
  Austrália: { background: '#06472d', surface: '#0b5d38', accent: '#f5c518', text: '#ffffff', muted: '#c9dfd3' },
  Áustria: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  Bélgica: { background: '#111111', surface: '#292018', accent: '#f5c518', text: '#ffffff', muted: '#d8d0c8' },
  'Bósnia e Herzegovina': { background: '#0a3d7c', surface: '#0d519f', accent: '#f5c518', text: '#ffffff', muted: '#c9daec' },
  Brasil: { background: '#063b73', surface: '#075b35', accent: '#f5c518', text: '#ffffff', muted: '#d2e0d8' },
  Canadá: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  'Cabo Verde': { background: '#063f77', surface: '#0b579c', accent: '#ffffff', text: '#ffffff', muted: '#c9dced' },
  Colômbia: { background: '#083b78', surface: '#0b4b91', accent: '#f5c518', text: '#ffffff', muted: '#cbd9e9' },
  Croácia: { background: '#113563', surface: '#18497f', accent: '#e3222f', text: '#ffffff', muted: '#ccd7e4' },
  'República Tcheca': { background: '#063f77', surface: '#0b579c', accent: '#e3222f', text: '#ffffff', muted: '#c9dced' },
  'RD Congo': { background: '#0a5ba8', surface: '#126ebc', accent: '#f5c518', text: '#ffffff', muted: '#d1e1ef' },
  Equador: { background: '#083b78', surface: '#0b4b91', accent: '#f5c518', text: '#ffffff', muted: '#cbd9e9' },
  Egito: { background: '#111111', surface: '#292020', accent: '#e3222f', text: '#ffffff', muted: '#d8cccc' },
  Inglaterra: { background: '#102a4e', surface: '#173b6d', accent: '#ffffff', text: '#ffffff', muted: '#cbd6e3' },
  França: { background: '#082b59', surface: '#0b3f7f', accent: '#e3222f', text: '#ffffff', muted: '#c7d6e7' },
  Alemanha: { background: '#111111', surface: '#282828', accent: '#f5c518', text: '#ffffff', muted: '#d1d1d1' },
  Irã: { background: '#075b35', surface: '#0d7042', accent: '#e3222f', text: '#ffffff', muted: '#cce6d8' },
  Iraque: { background: '#075b35', surface: '#0d7042', accent: '#ffffff', text: '#ffffff', muted: '#cce6d8' },
  'Costa do Marfim': { background: '#075b35', surface: '#0d7042', accent: '#f28c28', text: '#ffffff', muted: '#cce6d8' },
  Japão: { background: '#063f77', surface: '#0b579c', accent: '#e3222f', text: '#ffffff', muted: '#c9dced' },
  Jordânia: { background: '#111111', surface: '#283226', accent: '#d71920', text: '#ffffff', muted: '#d0d8cf' },
  México: { background: '#075b35', surface: '#0d7042', accent: '#e3222f', text: '#ffffff', muted: '#cce6d8' },
  Marrocos: { background: '#8f0c13', surface: '#b5121b', accent: '#0b7a3b', text: '#ffffff', muted: '#f0cfd1' },
  Holanda: { background: '#102a4e', surface: '#173b6d', accent: '#f47b20', text: '#ffffff', muted: '#cbd6e3' },
  'Nova Zelândia': { background: '#0b0b0b', surface: '#242424', accent: '#ffffff', text: '#ffffff', muted: '#d0d0d0' },
  Noruega: { background: '#102a4e', surface: '#173b6d', accent: '#e3222f', text: '#ffffff', muted: '#cbd6e3' },
  Panamá: { background: '#102a4e', surface: '#173b6d', accent: '#e3222f', text: '#ffffff', muted: '#cbd6e3' },
  Paraguai: { background: '#102a4e', surface: '#173b6d', accent: '#e3222f', text: '#ffffff', muted: '#cbd6e3' },
  Catar: { background: '#5a1230', surface: '#76183e', accent: '#ffffff', text: '#ffffff', muted: '#e2ccd6' },
  'Arábia Saudita': { background: '#075b35', surface: '#0d7042', accent: '#ffffff', text: '#ffffff', muted: '#cce6d8' },
  Escócia: { background: '#082b59', surface: '#0b3f7f', accent: '#ffffff', text: '#ffffff', muted: '#c7d6e7' },
  'África do Sul': { background: '#075b35', surface: '#0d7042', accent: '#f5c518', text: '#ffffff', muted: '#cce6d8' },
  'Coreia do Sul': { background: '#102a4e', surface: '#173b6d', accent: '#e3222f', text: '#ffffff', muted: '#cbd6e3' },
  Espanha: { background: '#8f0c13', surface: '#b5121b', accent: '#f5c518', text: '#ffffff', muted: '#f0cfd1' },
  Suécia: { background: '#063f77', surface: '#0b579c', accent: '#f5c518', text: '#ffffff', muted: '#c9dced' },
  Suíça: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  Tunísia: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  Turquia: { background: '#8f0c13', surface: '#b5121b', accent: '#ffffff', text: '#ffffff', muted: '#f0cfd1' },
  'Estados Unidos': { background: '#102a4e', surface: '#173b6d', accent: '#e3222f', text: '#ffffff', muted: '#cbd6e3' },
  Uruguai: { background: '#063f77', surface: '#0b579c', accent: '#ffffff', text: '#ffffff', muted: '#c9dced' },
  Uzbequistão: { background: '#063f77', surface: '#0b579c', accent: '#2a9d55', text: '#ffffff', muted: '#c9dced' }
};

const fallbackTeamTheme = themes.night;

selectedTheme = function selectedThemeWithTeamColors() {
  const selected = themeInputs.find((input) => input.checked)?.value || 'team';
  if (selected === 'team') {
    return teamPalettes[teamSelect?.value] || fallbackTeamTheme;
  }
  return themes[selected] || fallbackTeamTheme;
};

if (normalizedMatches.length && teamSelect?.value) {
  drawCard();
  updatePageUrl();
}
