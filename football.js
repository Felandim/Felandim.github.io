const searchInput = document.querySelector('[data-match-search]');
const resultCount = document.querySelector('[data-result-count]');
const matchRows = [...document.querySelectorAll('[data-match-row]')];
const groupRows = [...document.querySelectorAll('.group-row')];

const normalize = (value) => value
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase();

const teamAliases = {
  brasil: 'brazil',
  alemanha: 'germany',
  espanha: 'spain',
  inglaterra: 'england',
  holanda: 'netherlands',
  marrocos: 'morocco',
  suica: 'switzerland',
  'estados unidos': 'usa',
  'coreia do sul': 'south korea',
  'africa do sul': 'south africa'
};

function updateGroups() {
  groupRows.forEach((group) => {
    let row = group.nextElementSibling;
    let hasVisibleMatch = false;
    while (row && !row.classList.contains('group-row')) {
      if (row.hasAttribute('data-match-row') && !row.hidden) hasVisibleMatch = true;
      row = row.nextElementSibling;
    }
    group.hidden = !hasVisibleMatch;
  });
}

function filterMatches() {
  const normalizedQuery = normalize(searchInput?.value.trim() || '');
  const query = teamAliases[normalizedQuery] || normalizedQuery;
  let visible = 0;
  matchRows.forEach((row) => {
    row.hidden = query !== '' && !normalize(row.textContent).includes(query);
    if (!row.hidden) visible += 1;
  });
  updateGroups();
  if (resultCount) resultCount.textContent = `${visible} ${visible === 1 ? 'jogo encontrado' : 'jogos encontrados'}`;
}

searchInput?.addEventListener('input', filterMatches);
filterMatches();
