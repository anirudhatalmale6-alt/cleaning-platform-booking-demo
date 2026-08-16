/* ============================================================
   Sparrow — shared config, mock data and UI helpers.

   PRICING NOTE: every rate below is a PLACEHOLDER. The spec fixes
   the *structure* (rooms -> 40 min each -> hours; office by unit
   size band; VAT as its own checkout line) but not the numbers.
   All of it lives here so the admin dashboard edits data, never
   logic, and so real rates drop in without touching any screen.
   ============================================================ */
const CFG = {
  currency: 'R',
  minutesPerRoom: 40,          // from the customer spec, verbatim
  minHours: 2,                 // shortest job we will dispatch a cleaner for
  hourlyRate: 120,             // PLACEHOLDER — awaiting client
  vatRate: 0.15,               // South African standard rate, added on top
  vatRegistered: true,
  serviceFeePct: 0.07,         // platform fee on the net

  unitTypes: ['House', 'Flat / Apartment', 'Townhouse', 'Cottage', 'Bachelor unit'],

  // Office cleaning is priced by unit size band x number of units
  officeBands: [
    { id:'xs', label:'Under 50 m²',  hours:2,  price:340 },
    { id:'s',  label:'50 – 120 m²',  hours:3,  price:520 },
    { id:'m',  label:'120 – 250 m²', hours:5,  price:820 },
    { id:'l',  label:'250 – 500 m²', hours:8,  price:1280 },
    { id:'xl', label:'Over 500 m²',  hours:12, price:1850 }
  ],

  services: [
    { id:'standard', group:'indoor',  name:'Standard house cleaning', model:'rooms',  icon:'home',    mins:0 },
    { id:'deep',     group:'indoor',  name:'Deep clean',              model:'rooms',  icon:'sparkle', roomFactor:1.5 },
    { id:'move',     group:'indoor',  name:'Move-in / move-out',      model:'rooms',  icon:'box',     roomFactor:1.8 },
    { id:'office',   group:'indoor',  name:'Office cleaning',         model:'office', icon:'office' },
    { id:'laundry',  group:'indoor',  name:'Laundry & ironing',       model:'flat',   icon:'shirt',   price:220, hours:2 },
    { id:'outdoor',  group:'outdoor', name:'Outdoor cleaning',        model:'flat',   icon:'leaf',    price:360, hours:2.5 },
    { id:'garden',   group:'outdoor', name:'Gardening',               model:'flat',   icon:'shovel',  price:400, hours:3 },
    { id:'windows',  group:'outdoor', name:'Window cleaning',         model:'flat',   icon:'window',  price:300, hours:2 },
    { id:'pool',     group:'outdoor', name:'Pool service',            model:'flat',   icon:'wave',    price:380, hours:1.5 }
  ],

  // Booking checklist — taken from the customer document, in its order
  checklist: [
    { id:'general', name:'General cleaning',   price:0,   mins:0,  note:'included' },
    { id:'laundry', name:'Laundry',            price:85,  mins:40 },
    { id:'ironing', name:'Ironing',            price:100, mins:60 },
    { id:'windows', name:'Windows',            price:90,  mins:30 },
    { id:'oven',    name:'Oven',               price:120, mins:35 },
    { id:'fridge',  name:'Fridge',             price:90,  mins:25 },
    { id:'wardrobe',name:'Wardrobe packing',   price:150, mins:50 },
    { id:'rug',     name:'Rug cleaning',       price:180, mins:45 },
    { id:'garage',  name:'Garage cleaning',    price:200, mins:60 },
    { id:'washing', name:'Laundry washing',    price:80,  mins:35 },
    { id:'drying',  name:'Laundry drying',     price:60,  mins:30 },
    { id:'fulllaun',name:'Full laundry service',price:260,mins:110 }
  ],

  frequencies: [
    { id:'once',   title:'One-off',   sub:'Just this time',      mult:1.00, save:0  },
    { id:'weekly', title:'Weekly',    sub:'Same pro, same slot', mult:0.85, save:15 },
    { id:'biweek', title:'Bi-weekly', sub:'Every 2 weeks',       mult:0.90, save:10 }
  ],

  promos: {
    SPARROW20: { type:'pct',  val:.20, label:'20% off your first clean' },
    WELCOME50: { type:'flat', val:50,  label:'R50 off' }
  },

  slots: ['07:00','08:00','09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00'],

  provinces: {
    'Western Cape':   ['Cape Town','Stellenbosch','Paarl','George','Somerset West'],
    'Gauteng':        ['Johannesburg','Pretoria','Sandton','Midrand','Soweto'],
    'KwaZulu-Natal':  ['Durban','Pietermaritzburg','Ballito','Umhlanga','Richards Bay'],
    'Eastern Cape':   ['Gqeberha','East London','Mthatha'],
    'Free State':     ['Bloemfontein','Welkom'],
    'Mpumalanga':     ['Nelspruit','Witbank'],
    'Limpopo':        ['Polokwane','Tzaneen'],
    'North West':     ['Rustenburg','Potchefstroom'],
    'Northern Cape':  ['Kimberley','Upington']
  }
};

/* ---------- money / time ---------- */
const money = n => CFG.currency + Math.round(n).toLocaleString('en-ZA');
const hoursLabel = h => {
  const m = Math.round(h * 60);
  return `${Math.floor(m/60)}h${m%60 ? ' ' + (m%60) + 'm' : ''}`;
};

/* ============================================================
   PRICE ENGINE — one function, used by the booking flow, the
   customer dashboard and the admin quote screen so the three
   can never disagree about what a job costs.
   ============================================================ */
function priceBooking(b){
  const svc = CFG.services.find(s => s.id === b.service);
  if(!svc) return null;
  let hours = 0, base = 0;

  if(svc.model === 'rooms'){
    const rooms = Math.max(1, b.rooms || 1);
    hours = Math.max(CFG.minHours, rooms * CFG.minutesPerRoom / 60 * (svc.roomFactor || 1));
    base  = hours * CFG.hourlyRate;
  } else if(svc.model === 'office'){
    const band = CFG.officeBands.find(x => x.id === b.band) || CFG.officeBands[0];
    const units = Math.max(1, b.units || 1);
    hours = band.hours * units;
    base  = band.price * units;
  } else {
    hours = svc.hours;
    base  = svc.price;
  }

  let extras = 0, extraMins = 0;
  (b.extras || []).forEach(id => {
    const e = CFG.checklist.find(x => x.id === id);
    if(e){ extras += e.price; extraMins += e.mins; }
  });
  hours += extraMins / 60;

  const freq = CFG.frequencies.find(f => f.id === (b.freq || 'once'));
  const sub = base + extras;
  const freqDisc = Math.round(sub * (1 - freq.mult));

  let promoDisc = 0;
  const promo = b.promo && CFG.promos[b.promo];
  if(promo) promoDisc = promo.type === 'pct'
    ? Math.round((sub - freqDisc) * promo.val)
    : Math.min(promo.val, sub - freqDisc);

  const discount = freqDisc + promoDisc;
  const net      = sub - discount;
  const fee      = Math.round(net * CFG.serviceFeePct);
  const exVat    = net + fee;
  const vat      = CFG.vatRegistered ? Math.round(exVat * CFG.vatRate) : 0;

  return {
    serviceName: svc.name, base: Math.round(base), extras, freqDisc, promoDisc,
    discount, fee, exVat, vat, total: exVat + vat,
    hours, hoursLabel: hoursLabel(hours), freqLabel: freq.title, model: svc.model
  };
}

/* ============================================================
   MOCK DATA — stands in for the API. Deliberately shared across
   all three dashboards so the same booking reads consistently
   from the customer, cleaner and admin side.
   ============================================================ */
const DB = {
  customer: {
    name:'Thandi', surname:'Mokoena', initials:'TM', email:'thandi.m@example.co.za',
    phone:'+27 82 445 1190', points:1840, tier:'Gold', referrals:3,
    joined:'March 2026', memberNo:'CUS-10428'
  },

  addresses: [
    { id:'a1', label:'Home',   line:'18 Ocean View Drive, Flat 4B', suburb:'Sea Point', city:'Cape Town', prov:'Western Cape', notes:'Buzzer 12. Two cats — keep the balcony door shut.', primary:true },
    { id:'a2', label:'Mom’s place', line:'7 Protea Street', suburb:'Rondebosch', city:'Cape Town', prov:'Western Cape', notes:'Key under the ceramic pot.', primary:false },
    { id:'a3', label:'Office', line:'Unit 3, The Foundry, 12 Prestwich St', suburb:'Green Point', city:'Cape Town', prov:'Western Cape', notes:'Reception has the access card.', primary:false }
  ],

  cards: [
    { id:'c1', brand:'Visa', last4:'4821', exp:'09/29', primary:true },
    { id:'c2', brand:'Mastercard', last4:'6613', exp:'04/28', primary:false }
  ],

  cleaners: [
    { id:'cl1', name:'Nomsa', surname:'Mabaso', initials:'NM', rating:4.94, jobs:216, years:6, langs:['English','isiZulu','isiXhosa'], group:'indoor', city:'Cape Town', prov:'Western Cape', status:'active', fav:true,  tone:'', earnings:18420 },
    { id:'cl2', name:'Sipho', surname:'Dlamini', initials:'SD', rating:4.81, jobs:143, years:4, langs:['English','isiZulu'], group:'outdoor', city:'Cape Town', prov:'Western Cape', status:'active', fav:true, tone:'sky', earnings:14180 },
    { id:'cl3', name:'Grace', surname:'Nkosi',   initials:'GN', rating:4.88, jobs:302, years:9, langs:['English','Sesotho'], group:'indoor', city:'Cape Town', prov:'Western Cape', status:'active', fav:false, tone:'clay', earnings:26900 },
    { id:'cl4', name:'Lerato', surname:'Molefe', initials:'LM', rating:4.72, jobs:88,  years:3, langs:['English','Setswana'], group:'indoor', city:'Johannesburg', prov:'Gauteng', status:'active', fav:false, tone:'gold', earnings:9110 },
    { id:'cl5', name:'Andile', surname:'Khumalo',initials:'AK', rating:0,    jobs:0,   years:2, langs:['English','isiXhosa'], group:'outdoor', city:'Durban', prov:'KwaZulu-Natal', status:'pending', fav:false, tone:'sky', earnings:0 },
    { id:'cl6', name:'Precious', surname:'Sithole', initials:'PS', rating:0, jobs:0,  years:5, langs:['English','isiZulu'], group:'indoor', city:'Cape Town', prov:'Western Cape', status:'pending', fav:false, tone:'', earnings:0 }
  ],

  customers: [
    { id:'cu1', name:'Thandi Mokoena', initials:'TM', email:'thandi.m@example.co.za', phone:'+27 82 445 1190', bookings:14, spend:9840, fav:'Nomsa Mabaso', joined:'Mar 2026', tone:'' },
    { id:'cu2', name:'Riaan van Wyk', initials:'RW', email:'riaan.vw@example.co.za', phone:'+27 83 220 7712', bookings:6, spend:4120, fav:'Grace Nkosi', joined:'May 2026', tone:'sky' },
    { id:'cu3', name:'Aisha Patel', initials:'AP', email:'aisha.p@example.co.za', phone:'+27 71 998 0032', bookings:22, spend:17650, fav:'Nomsa Mabaso', joined:'Jan 2026', tone:'clay' },
    { id:'cu4', name:'Johan Botha', initials:'JB', email:'j.botha@example.co.za', phone:'+27 84 551 3390', bookings:2, spend:1180, fav:'—', joined:'Aug 2026', tone:'gold' }
  ],

  /* status: pending (awaiting admin confirmation) -> confirmed (cleaner assigned)
     -> enroute -> inprogress -> completed | cancelled                          */
  bookings: [
    { id:'SPW-104312', cust:'cu1', service:'standard', rooms:4, extras:['oven','fridge'], freq:'weekly',
      date:'2026-08-18', time:'09:00', addr:'a1', cleaner:'cl1', status:'confirmed', eta:'08:45', rated:null },
    { id:'SPW-104298', cust:'cu1', service:'outdoor', extras:[], freq:'once',
      date:'2026-08-22', time:'11:00', addr:'a2', cleaner:null, status:'pending', eta:null, rated:null },
    { id:'SPW-104201', cust:'cu1', service:'office', band:'m', units:1, extras:['windows'], freq:'biweek',
      date:'2026-08-25', time:'07:00', addr:'a3', cleaner:'cl3', status:'confirmed', eta:'06:50', rated:null },
    { id:'SPW-103980', cust:'cu1', service:'standard', rooms:4, extras:['laundry'], freq:'weekly',
      date:'2026-08-11', time:'09:00', addr:'a1', cleaner:'cl1', status:'completed', eta:null, rated:5 },
    { id:'SPW-103844', cust:'cu1', service:'deep', rooms:4, extras:['oven','rug'], freq:'once',
      date:'2026-07-29', time:'08:00', addr:'a1', cleaner:'cl3', status:'completed', eta:null, rated:4 },
    { id:'SPW-103702', cust:'cu1', service:'garden', extras:[], freq:'once',
      date:'2026-07-15', time:'10:00', addr:'a2', cleaner:'cl2', status:'completed', eta:null, rated:5 },
    { id:'SPW-103551', cust:'cu1', service:'windows', extras:[], freq:'once',
      date:'2026-06-30', time:'13:00', addr:'a1', cleaner:'cl2', status:'cancelled', eta:null, rated:null },
    { id:'SPW-104355', cust:'cu2', service:'standard', rooms:3, extras:['fridge'], freq:'once',
      date:'2026-08-19', time:'10:00', addr:'a1', cleaner:null, status:'pending', eta:null, rated:null },
    { id:'SPW-104361', cust:'cu3', service:'deep', rooms:5, extras:['oven','garage'], freq:'once',
      date:'2026-08-20', time:'08:00', addr:'a1', cleaner:null, status:'pending', eta:null, rated:null },
    { id:'SPW-104366', cust:'cu4', service:'garden', extras:[], freq:'once',
      date:'2026-08-21', time:'09:00', addr:'a2', cleaner:'cl2', status:'confirmed', eta:'08:40', rated:null }
  ],

  notifications: [
    { id:'n1', t:'Nomsa confirmed your Tuesday clean', s:'Booking SPW-104312 · 2 hours ago', kind:'ok' },
    { id:'n2', t:'Your invoice for SPW-103980 is ready', s:'Yesterday', kind:'mute' },
    { id:'n3', t:'You earned 180 loyalty points', s:'2 days ago', kind:'ok' },
    { id:'n4', t:'Outdoor booking SPW-104298 is awaiting confirmation', s:'3 days ago', kind:'wait' }
  ],

  offers: [
    { id:'o1', t:'20% off your next deep clean', s:'Use code SPARROW20 · expires 30 Sep', kind:'promo' },
    { id:'o2', t:'Refer a friend, both get R100', s:'You have referred 3 friends so far', kind:'referral' },
    { id:'o3', t:'Spring window special', s:'Windows + patio bundled, save R140', kind:'season' }
  ]
};

/* ---------- lookups ---------- */
const byId    = (arr, id) => arr.find(x => x.id === id) || null;
const cleaner = id => byId(DB.cleaners, id);
const address = id => byId(DB.addresses, id);
const custOf  = id => byId(DB.customers, id);
const svcOf   = id => CFG.services.find(s => s.id === id);

const STATUS = {
  pending:   { label:'Awaiting confirmation', cls:'wait' },
  confirmed: { label:'Confirmed',             cls:'ok'   },
  enroute:   { label:'On the way',            cls:'live' },
  inprogress:{ label:'In progress',           cls:'live' },
  completed: { label:'Completed',             cls:'mute' },
  cancelled: { label:'Cancelled',             cls:'bad'  }
};
const statusPill = s => `<span class="pill ${STATUS[s].cls}">${STATUS[s].label}</span>`;

const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
function fmtDate(iso){
  const [y,m,d] = iso.split('-').map(Number);
  const dt = new Date(y, m-1, d);
  return `${DAYS[dt.getDay()]} ${d} ${MON[m-1]}`;
}
function fmtDateLong(iso){
  const [y,m,d] = iso.split('-').map(Number);
  const dt = new Date(y, m-1, d);
  return `${DAYS[dt.getDay()]} ${d} ${MON[m-1]} ${y}`;
}
const starRow = n => '★'.repeat(Math.round(n)) + '☆'.repeat(5 - Math.round(n));

/* ---------- icons ---------- */
const I = {
  home:'<path d="M4 11l8-6 8 6v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>',
  sparkle:'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z"/>',
  box:'<path d="M4 8l8-4 8 4v8l-8 4-8-4z"/><path d="M4 8l8 4 8-4M12 12v8"/>',
  office:'<rect x="4" y="4" width="10" height="16" rx="1"/><path d="M14 10h6v10h-6M7 8h4M7 12h4M7 16h4"/>',
  leaf:'<path d="M5 19c0-8 5-13 14-13 0 9-5 14-13 14"/><path d="M5 19c3-3 6-5 10-6"/>',
  shovel:'<path d="M14 4l6 6-3 3-6-6z"/><path d="M11 7l-6 6v4l3 3h4l6-6"/>',
  shirt:'<path d="M8 4l4 2 4-2 4 3-2 3-1-1v11H7V9L6 10 4 7z"/>',
  window:'<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M12 4v16M4 12h16"/>',
  wave:'<path d="M3 9c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M3 15c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/>',
  grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  cal:'<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
  heart:'<path d="M12 20s-7-4.4-7-9.2A3.8 3.8 0 0 1 12 8a3.8 3.8 0 0 1 7 2.8C19 15.6 12 20 12 20z"/>',
  card:'<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
  pin:'<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/>',
  bell:'<path d="M18 15V10a6 6 0 1 0-12 0v5l-2 3h16z"/><path d="M10 21h4"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
  users:'<circle cx="9" cy="8" r="3.4"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 5.2a3.4 3.4 0 0 1 0 5.6M17.5 20a6.5 6.5 0 0 0-2.2-4.9"/>',
  chat:'<path d="M20 15a2 2 0 0 1-2 2H8l-4 3V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/>',
  gift:'<rect x="3" y="9" width="18" height="12" rx="1"/><path d="M3 13h18M12 9v12"/><path d="M12 9S10.5 4 8 4a2.2 2.2 0 0 0 0 5M12 9s1.5-5 4-5a2.2 2.2 0 0 1 0 5"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5.3l3.4 2"/>',
  check:'<path d="M4 12.5l5.5 5.5L20 7"/>',
  x:'<path d="M6 6l12 12M18 6L6 18"/>',
  wallet:'<path d="M3 7a2 2 0 0 1 2-2h12v3"/><rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="17" cy="13.5" r="1.3"/>',
  doc:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  upload:'<path d="M12 16V4M8 8l4-4 4 4"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
  chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  shield:'<path d="M12 3l7 3v5c0 4.4-3 8.3-7 10-4-1.7-7-5.6-7-10V6l7-3z"/>',
  star:'<path d="M12 4l2.4 5 5.6.8-4 4 1 5.5-5-2.7-5 2.7 1-5.5-4-4 5.6-.8z"/>',
  route:'<circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="18" r="2.4"/><path d="M8.4 6H14a3 3 0 0 1 0 6h-4a3 3 0 0 0 0 6h5.6"/>',
  logout:'<path d="M15 17l5-5-5-5"/><path d="M20 12H9"/><path d="M12 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.01"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  search:'<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4 4"/>'
};
const ico = (k, sz = 20, sw = 1.7) =>
  `<svg width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${I[k] || ''}</svg>`;

/* ---------- tiny UI helpers ---------- */
const $  = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

function toast(msg, icon = 'check'){
  let host = $('.toast-host');
  if(!host){ host = document.createElement('div'); host.className = 'toast-host'; document.body.appendChild(host); }
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = ico(icon, 16, 2.4) + '<span></span>';
  el.querySelector('span').textContent = msg;
  host.appendChild(el);
  setTimeout(() => { el.style.transition = 'opacity .3s'; el.style.opacity = '0'; setTimeout(() => el.remove(), 320); }, 2600);
}

function modal({ title, sub, body, actions = [] }){
  const veil = document.createElement('div');
  veil.className = 'veil on';
  veil.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-head">
        <div><h3>${title}</h3>${sub ? `<div class="mh-s">${sub}</div>` : ''}</div>
        <button class="x-btn" data-close aria-label="Close">${ico('x', 20, 2.2)}</button>
      </div>
      <div class="modal-body">${body}</div>
      <div class="modal-foot"></div>
    </div>`;
  const foot = veil.querySelector('.modal-foot');
  actions.forEach(a => {
    const b = document.createElement('button');
    b.className = 'btn ' + (a.cls || 'btn-outline');
    b.textContent = a.label;
    b.onclick = () => { const keep = a.fn && a.fn(veil); if(!keep) veil.remove(); };
    foot.appendChild(b);
  });
  veil.querySelector('[data-close]').onclick = () => veil.remove();
  veil.onclick = e => { if(e.target === veil) veil.remove(); };
  document.body.appendChild(veil);
  return veil;
}

/* ---------- shared chrome ---------- */
function protoBar(active){
  const links = [
    ['index.html','Website & booking'],
    ['dashboard.html','Customer'],
    ['cleaner.html','Cleaner'],
    ['admin.html','Admin']
  ];
  return `<div class="protobar"><div class="wrap">
    <span>Prototype — sample data, no backend yet</span>
    <span class="pb-links">${links.map(([h,t]) =>
      `<a href="${h}" class="${h === active ? 'on' : ''}">${t}</a>`).join('')}</span>
  </div></div>`;
}

function topBar(role, links, active){
  return `<div class="topbar"><div class="wrap">
    <a class="brand" href="index.html">
      <span class="brand-mark">${ico('home', 17, 2).replace('currentColor', '#F3EFE7')}</span>
      <span class="brand-name">Sparrow<em>.</em></span>
      ${role ? `<span class="brand-role">${role}</span>` : ''}
    </a>
    <nav class="nav">
      ${links.map(([h,t]) => `<a href="${h}" class="hide-sm ${h === active ? 'on' : ''}">${t}</a>`).join('')}
      <button class="pill-btn" onclick="location.href='index.html'">${ico('logout', 15, 2)} Sign out</button>
    </nav>
  </div></div>`;
}

function mountChrome({ page, role, links }){
  document.body.insertAdjacentHTML('afterbegin', protoBar(page) + topBar(role, links, page));
}

/* ---------- side nav ---------- */
function sideNav(items, active, onPick){
  const el = $('#sideNav');
  el.innerHTML = items.map(i =>
    `<button class="snav ${i.id === active ? 'on' : ''}" data-nav="${i.id}">
       ${ico(i.icon, 18)}<span>${i.label}</span>
       ${i.badge ? `<span class="badge">${i.badge}</span>` : ''}
     </button>`).join('');
  el.querySelectorAll('[data-nav]').forEach(b => b.onclick = () => onPick(b.dataset.nav));
}
