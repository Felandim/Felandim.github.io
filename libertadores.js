(() => {
  const phase = document.querySelector('#lib-phase-filter');
  const team = document.querySelector('#lib-team-filter');
  const games = [...document.querySelectorAll('.lib-game')];
  const count = document.querySelector('#lib-result-count');
  const empty = document.querySelector('#lib-empty');
  if (!phase || !team || !games.length) return;

  const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const filter = () => {
    const phaseValue = phase.value;
    const teamValue = normalize(team.value.trim());
    let visible = 0;
    games.forEach((game) => {
      const matches = (!phaseValue || game.dataset.phase === phaseValue)
        && (!teamValue || normalize(game.dataset.teams || '').includes(teamValue));
      game.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = `${visible} ${visible === 1 ? 'partida' : 'partidas'}`;
    empty.hidden = visible !== 0;
  };

  phase.addEventListener('change', filter);
  team.addEventListener('input', filter);
  filter();
})();
