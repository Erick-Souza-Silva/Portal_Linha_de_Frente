const menuToggle = document.querySelector('.menu-toggle');
const mainNav = document.querySelector('.main-nav');
const searchToggle = document.querySelector('[data-search-toggle]');
const searchPanel = document.querySelector('[data-search-panel]');
const searchInput = document.querySelector('#news-search');
const newsCards = [...document.querySelectorAll('.news-card')];
const emptyState = document.querySelector('[data-empty-state]');

menuToggle?.addEventListener('click', () => {
	const isOpen = mainNav.classList.toggle('is-open');
	menuToggle.setAttribute('aria-expanded', String(isOpen));
});

searchToggle?.addEventListener('click', () => {
	const isOpen = searchPanel.classList.toggle('is-open');
	if (isOpen) searchInput.focus();
});

searchInput?.addEventListener('input', (event) => {
	const query = event.target.value.toLowerCase().trim();
	let visibleCards = 0;

	newsCards.forEach((card) => {
		const matches = card.textContent.toLowerCase().includes(query);
		card.hidden = !matches;
		if (matches) visibleCards += 1;
	});

	emptyState.classList.toggle('is-visible', visibleCards === 0);
});

document.querySelectorAll('.nav-inner a').forEach((link) => {
	link.addEventListener('click', () => {
		document.querySelectorAll('.nav-inner a').forEach((item) => item.classList.remove('active'));
		link.classList.add('active');
		mainNav.classList.remove('is-open');
		menuToggle?.setAttribute('aria-expanded', 'false');
	});
});

document.querySelector('.newsletter form')?.addEventListener('submit', (event) => {
	event.preventDefault();
	const button = event.currentTarget.querySelector('button');
	button.innerHTML = 'Inscrito <span>✓</span>';
	button.disabled = true;
});
