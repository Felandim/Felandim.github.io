document.querySelectorAll('[data-current-year]').forEach((node) => {
  node.textContent = new Date().getFullYear();
});

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
