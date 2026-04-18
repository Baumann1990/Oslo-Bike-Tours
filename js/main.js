/* ── Gallery rotation ────────────────────────────────────────── */
const GALLERY_POOL = [
  { src: 'images/IMG_2864.jpg',                              alt: 'Cyclists overlooking Oslo' },
  { src: 'images/IMG_6329.jpg',                              alt: 'Bike along Oslo fjord' },
  { src: 'images/90ADE1E7-E973-4DF3-B474-F9B535EE3D0B.jpg', alt: 'Fjord shoreline cycling' },
  { src: 'images/IMG_5813.jpg',                              alt: 'Forest rest stop golden light' },
  { src: 'images/IMG_1453.jpg',                              alt: 'Oslo fjord golden hour' },
  { src: 'images/IMG_0270.JPG',                              alt: 'Oslo valley panorama' },
  { src: 'images/IMG_5843.jpg',                              alt: 'Group ride in the forest' },
  { src: 'images/IMG_6335.jpg',                              alt: 'Fjord silhouette ride' },
  { src: 'images/IMG_6647.jpg',                              alt: 'Lakeside cabin stop' },
  { src: 'images/IMG_5705.jpg',                              alt: 'Reservoir dam cycling' },
  { src: 'images/IMG_8055.JPG',                              alt: 'Oslo bike tour' },
  { src: 'images/IMG_6876.JPG',                              alt: 'Oslo cycling' },
  { src: 'images/IMG_7981.jpg',                              alt: 'Cycling in Oslo' },
  { src: 'images/IMG_6911.jpg',                              alt: 'Oslo landscape' },
  { src: 'images/IMG_6871.jpg',                              alt: 'Norwegian scenery' },
  { src: 'images/IMG_6869.jpg',                              alt: 'Bike tour Oslo' },
];

const GALLERY_COUNT = 7; // photos shown per visit (6–8)

(function buildGallery() {
  const track = document.getElementById('galleryTrack');
  if (!track) return;

  // Fisher-Yates shuffle, then take first GALLERY_COUNT
  const pool = [...GALLERY_POOL];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  pool.slice(0, GALLERY_COUNT).forEach(({ src, alt }) => {
    const img = document.createElement('img');
    img.src     = src;
    img.alt     = alt;
    img.loading = 'lazy';
    track.appendChild(img);
  });
})();

/* ── Nav: scroll state ───────────────────────────────────────── */
const nav = document.getElementById('nav');

const updateNav = () => {
  nav.classList.toggle('scrolled', window.scrollY > 40);
};

window.addEventListener('scroll', updateNav, { passive: true });
updateNav();

/* ── Nav: mobile toggle ──────────────────────────────────────── */
const toggle = document.getElementById('navToggle');
const menu   = document.getElementById('navMenu');

toggle.addEventListener('click', () => {
  const open = menu.classList.toggle('open');
  toggle.setAttribute('aria-expanded', open);
});

menu.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    menu.classList.remove('open');
    toggle.setAttribute('aria-expanded', false);
  });
});

/* ── Tour filters ────────────────────────────────────────────── */
const filters   = document.querySelectorAll('.filter');
const tourCards = document.querySelectorAll('.tour-card');

filters.forEach(btn => {
  btn.addEventListener('click', () => {
    filters.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const f = btn.dataset.filter;

    tourCards.forEach(card => {
      if (f === 'all') {
        card.classList.remove('hidden');
        return;
      }
      const match = card.dataset.surface === f || card.dataset.level === f;
      card.classList.toggle('hidden', !match);
    });
  });
});

/* ── Footer filter links ─────────────────────────────────────── */
document.querySelectorAll('a[data-filter]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const targetFilter = link.dataset.filter;

    // Scroll to tours section
    document.getElementById('tours').scrollIntoView({ behavior: 'smooth' });

    // Trigger the matching filter button after scroll settles
    setTimeout(() => {
      const btn = document.querySelector(`.filter[data-filter="${targetFilter}"]`);
      if (btn) btn.click();
    }, 500);
  });
});

/* ── Scroll fade-in ──────────────────────────────────────────── */
const fadeEls = document.querySelectorAll(
  '.tour-card, .guide-card, .about__grid, .book__grid, .section-header'
);

fadeEls.forEach(el => el.classList.add('fade-in'));

const observer = new IntersectionObserver(
  entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        observer.unobserve(e.target);
      }
    });
  },
  { threshold: 0.12 }
);

fadeEls.forEach(el => observer.observe(el));

/* ── Modals ──────────────────────────────────────────────────── */
const openModal = id => {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  modal.querySelector('.modal__close').focus();
};

const closeModal = modal => {
  modal.hidden = true;
  document.body.style.overflow = '';
};

// Open via "Details" buttons
document.querySelectorAll('[data-modal]').forEach(btn => {
  btn.addEventListener('click', () => openModal(btn.dataset.modal));
});

// Close via × button or backdrop
document.querySelectorAll('.modal').forEach(modal => {
  modal.querySelector('.modal__close').addEventListener('click', () => closeModal(modal));
  modal.querySelector('.modal__backdrop').addEventListener('click', () => closeModal(modal));
  // Close "Book this tour" links too
  modal.querySelectorAll('.modal__book').forEach(a => {
    a.addEventListener('click', () => closeModal(modal));
  });
});

// Close on Escape
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  document.querySelectorAll('.modal:not([hidden])').forEach(closeModal);
});

/* ── Booking form ────────────────────────────────────────────── */
const WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit';

const dateInput = document.getElementById('date');
if (dateInput) {
  dateInput.min = new Date().toISOString().split('T')[0];
}

const form         = document.getElementById('bookForm');
const confirmPanel = document.getElementById('formConfirm');

if (form) {
  form.addEventListener('submit', async e => {
    e.preventDefault();

    // Validate required fields (form uses novalidate so we handle this manually)
    let valid = true;
    form.querySelectorAll('[required]').forEach(field => {
      const empty = !field.value.trim();
      field.classList.toggle('input--error', empty);
      if (empty) valid = false;
    });
    if (!valid) return;

    const btn = form.querySelector('button[type="submit"]');
    btn.textContent = 'Sending…';
    btn.disabled    = true;

    const showConfirmation = () => {
      form.style.display         = 'none';
      confirmPanel.style.display = 'flex';
    };

    try {
      const res  = await fetch(WEB3FORMS_ENDPOINT, {
        method:  'POST',
        headers: { 'Accept': 'application/json' },
        body:    new FormData(form),
      });
      const data = await res.json();

      if (data.success) {
        showConfirmation();
      } else {
        btn.textContent = 'Something went wrong — try again';
        btn.disabled    = false;
      }
    } catch {
      btn.textContent = 'Network error — try again';
      btn.disabled    = false;
    }
  });

  // Clear error state on input
  form.querySelectorAll('[required]').forEach(field => {
    field.addEventListener('input', () => field.classList.remove('input--error'));
  });
}
