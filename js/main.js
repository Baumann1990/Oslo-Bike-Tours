/* ── Scroll restoration ──────────────────────────────────────── */
if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
document.documentElement.style.scrollBehavior = 'auto';
window.scrollTo(0, 0);
document.documentElement.style.scrollBehavior = '';

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
  { src: 'images/IMG_0255.JPG',                              alt: 'Gravel bike at Norwegian lake, autumn' },
  { src: 'images/IMG_1489.JPG',                              alt: 'Gravel bike by lake in summer' },
  { src: 'images/IMG_6630.jpg',                              alt: 'Bike stop by forest lake and red cabin' },
  { src: 'images/IMG_8053.jpeg',                             alt: 'Rest stop at remote lakeside cabin' },
  { src: 'images/IMG_8056.jpeg',                             alt: 'View from Nordmarka forest over the Oslofjord' },
  { src: 'images/christoffer-engstrom-tjguVu0GoEM-unsplash.jpg', alt: 'Oslo city skyline reflected at dusk' },
  { src: 'images/delia-giandeini--yz2HFg6WYo-unsplash.jpg', alt: 'Bygdøy fjord shore in summer' },
  { src: 'images/hana-clarinda-o0i_hR68r0o-unsplash.jpg',   alt: 'Bronze sculpture overlooking Oslo City Hall at golden hour' },
  { src: 'images/hans-joachim-kaiser-_eqvDs2vt1Q-unsplash.jpg', alt: 'Traditional wooden boats at Bygdøy harbour' },
  { src: 'images/marius-tandberg--pG0RZ36pXE-unsplash.jpg', alt: 'Vigeland Monolith and sculptures, Frogner Park' },
  { src: 'images/nick-night-NY1CGpvtDl4-unsplash.jpg',      alt: 'Vigeland Sculpture Park in summer' },
  { src: 'images/lawrence-krowdeed-QhgueME61_M-unsplash.jpg', alt: 'Rocky Oslofjord shoreline' },
  { src: 'images/lawrence-krowdeed-zXcYUETehx4-unsplash.jpg', alt: 'Oslofjord island with white boathouse' },
  { src: 'images/theo-eilertsen-photography-ax6fKJRUMlo-unsplash.jpg', alt: 'Oslo City Hall on a winter night' },
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

// IntersectionObserver watches a thin sentinel just below the hero.
// Unlike scroll events, it fires immediately on setup AND on BFCache
// restoration (back/forward navigation), so the nav background is always
// correct regardless of how the page was loaded or what scrollY was cached.
(function initNavState() {
  const heroEl = document.querySelector('.hero, .tour-hero');

  if (heroEl && 'IntersectionObserver' in window) {
    new IntersectionObserver(
      ([entry]) => nav.classList.toggle('scrolled', !entry.isIntersecting),
      // rootMargin shrinks the root by 80px at top: nav becomes opaque once
      // the hero's top edge has scrolled 80px above the viewport.
      { rootMargin: '-80px 0px 0px 0px', threshold: 0 }
    ).observe(heroEl);
  } else {
    // Fallback: scroll event for non-hero pages or older browsers
    const updateNav = () => nav.classList.toggle('scrolled', window.scrollY > 40);
    window.addEventListener('scroll', updateNav, { passive: true });
    updateNav();
  }

  // BFCache: when iOS restores the page from back/forward cache JS
  // doesn't re-run, so scroll position and nav state can be stale.
  window.addEventListener('pageshow', e => {
    if (!e.persisted) return;
    document.documentElement.style.scrollBehavior = 'auto';
    window.scrollTo(0, 0);
    document.documentElement.style.scrollBehavior = '';
  });
})();

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

/* ── Sticky booking button (mobile only) ────────────────────── */
(function initStickyBook() {
  // Inject the element
  const bar = document.createElement('div');
  bar.className = 'sticky-book';

  // On tour sub-pages link to /#book; on the homepage link to #book
  const isHome = window.location.pathname === '/' ||
                 window.location.pathname === '/index.html';
  const href   = isHome ? '#book' : '/#book';

  bar.innerHTML = `
    <a href="${href}" class="btn btn--primary btn--full">
      Book a Tour
    </a>`;
  document.body.appendChild(bar);

  // Detect the element we want to scroll past before showing the bar.
  // On the homepage that's the hero; on tour pages it's the tour hero.
  const hero = document.querySelector('.hero, .tour-hero');

  // On the homepage also hide the bar when the booking section is visible.
  const bookSection = isHome ? document.getElementById('book') : null;

  let ticking = false;

  const update = () => {
    ticking = false;

    // Only act if there is a hero element to measure
    if (!hero) {
      bar.classList.add('is-visible');
      return;
    }

    const heroBelowFold = hero.getBoundingClientRect().bottom <= 0;

    if (!heroBelowFold) {
      bar.classList.remove('is-visible');
      return;
    }

    // Hide the bar when the booking section itself is on screen
    if (bookSection) {
      const bookRect = bookSection.getBoundingClientRect();
      const bookVisible = bookRect.top < window.innerHeight && bookRect.bottom > 0;
      bar.classList.toggle('is-visible', !bookVisible);
    } else {
      bar.classList.add('is-visible');
    }
  };

  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(update);
      ticking = true;
    }
  }, { passive: true });

  // Run once on load in case the page opens mid-scroll
  update();
})();

/* ── Booking form ────────────────────────────────────────────── */
const WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit';

const dateInput = document.getElementById('date');
if (dateInput) {
  dateInput.min = new Date().toISOString().split('T')[0];
}

const form         = document.getElementById('bookForm');
const confirmPanel = document.getElementById('formConfirm');

if (form) {
  const setFieldError = (id, message) => {
    const field = document.getElementById(id);
    const span  = document.getElementById('error-' + id);
    if (field) field.classList.add('input--error');
    if (span)  span.textContent = message;
  };

  const clearFieldError = (id) => {
    const field = document.getElementById(id);
    const span  = document.getElementById('error-' + id);
    if (field) field.classList.remove('input--error');
    if (span)  span.textContent = '';
  };

  const validateForm = () => {
    let valid = true;
    ['name', 'email', 'tour', 'date', 'riders'].forEach(id => clearFieldError(id));

    const name = form.querySelector('#name');
    if (!name.value.trim()) {
      setFieldError('name', 'Please enter your name.');
      valid = false;
    }

    const email = form.querySelector('#email');
    if (!email.value.trim()) {
      setFieldError('email', 'Please enter your email address.');
      valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.value.trim())) {
      setFieldError('email', 'Please enter a valid email address (e.g. you@example.com).');
      valid = false;
    }

    const tour = form.querySelector('#tour');
    if (!tour.value) {
      setFieldError('tour', 'Please select a tour.');
      valid = false;
    }

    const date = form.querySelector('#date');
    if (!date.value) {
      setFieldError('date', 'Please pick a preferred date.');
      valid = false;
    }

    const riders = form.querySelector('#riders');
    if (!riders.value) {
      setFieldError('riders', 'Please enter the number of riders.');
      valid = false;
    }

    return valid;
  };

  // Clear errors as the user corrects each field
  ['name', 'email', 'tour', 'date', 'riders'].forEach(id => {
    const field = document.getElementById(id);
    if (field) field.addEventListener('input', () => clearFieldError(id));
  });

  form.addEventListener('submit', async e => {
    e.preventDefault();

    if (!validateForm()) return;

    const btn = form.querySelector('button[type="submit"]');
    btn.textContent = 'Sending…';
    btn.disabled    = true;

    try {
      const res  = await fetch(WEB3FORMS_ENDPOINT, {
        method:  'POST',
        headers: { 'Accept': 'application/json' },
        body:    new FormData(form),
      });
      const data = await res.json();

      if (data.success) {
        // Fire Google Ads conversion event, then redirect
        if (typeof gtag === 'function') {
          gtag('event', 'conversion_event_submit_lead_form_1');
        }
        setTimeout(() => { window.location.href = '/thank-you'; }, 500);
      } else {
        btn.textContent = 'Something went wrong — try again';
        btn.disabled    = false;
      }
    } catch {
      btn.textContent = 'Network error — try again';
      btn.disabled    = false;
    }
  });
}
