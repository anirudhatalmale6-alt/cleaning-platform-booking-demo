/* ============================================================
   Sparrow — shared config, mock data and UI helpers.

   PRICING comes from the client's message of 19 Aug 2026 and is
   used verbatim:

     R35 per hour · R35 service fee · R155 flat rate
     1–2 bedroom est 4h · 3–4 bedroom est 6h · 5+ bedroom est 8h
     extras priced and timed per his list
     a cleaner may not be booked past 10 hours

   Anything still marked PLACEHOLDER is mine and is waiting on him.
   Every number lives in this one object so the admin dashboard
   edits data, never logic.
   ============================================================ */
const CFG = {
  currency: 'R',

  /* --- the client's four price levers --- */
  hourlyRate: 35,      // R35 per hour
  serviceFee: 35,      // R35 service fee, once per booking
  flatRate: 155,       // R155 flat rate, once per booking

  /* --- the client's time rules --- */
  maxHours: 10,        // "employees are only allowed to work a maximum of 10 hours"
  stepMins: 30,        // hours move in 30-minute steps
  reduceMins: 30,      // the customer may take at most 30 min OFF the estimate

  /* Unit size -> estimated hours. His words: "these are just estimates
     for the unit size and could add more hours."                        */
  bedroomBands: [
    { id:'b12', label:'1 – 2 bedroom', hours:4 },
    { id:'b34', label:'3 – 4 bedroom', hours:6 },
    { id:'b5',  label:'5+ bedroom',    hours:8 }
  ],

  propertyTypes: ['House', 'Flat / Apartment', 'Townhouse', 'Cottage', 'Bachelor unit'],

  /* Extra tasks — his list, in his order. Each adds BOTH money and time.
     `set` decides which services offer it: 'home' on the indoor house
     cleans, 'outdoor' on the outdoor range. Pool service moved here on
     22 Aug — "please put pool services under outdoor as an extra task". */
  extras: [
    { id:'oven',     set:'home',    name:'Oven clean',                mins:30,  price:35  },
    { id:'fridge',   set:'home',    name:'Fridge clean',              mins:30,  price:35  },
    { id:'cupboard', set:'home',    name:'Cupboard clean',            mins:60,  price:35  },
    { id:'washfold', set:'home',    name:'Basic wash, dry and fold',  mins:60,  price:180 },
    { id:'washiron', set:'home',    name:'Wash, dry and iron',        mins:120, price:250 },
    /* PLACEHOLDER: he has not priced the pool. R70 is its 2 hours at his
       own R35/hr, so it at least follows his method until he says. */
    { id:'pool',     set:'outdoor', name:'Pool service',              mins:120, price:70, placeholder:true,
      sub:'Skim, vacuum, brush and a chemical check' }
  ],

  /* Strictly laundry — pick a wash, then pick a finish. */
  laundryWash: [
    { id:'hand',    name:'Hand wash',            hours:5, sub:'Delicates and hand-wash-only fabrics' },
    { id:'machine', name:'Washing machine wash', hours:4, sub:'Standard machine load' }
  ],
  laundryFinish: [
    { id:'dryfold', name:'Dry & fold',        hours:2,   sub:'Line or tumble dried, folded' },
    { id:'dryiron', name:'Dry, iron & fold',  hours:3.5, sub:'Dried, pressed and folded' }
  ],

  /* WINDOW CLEANING — his numbers, 22 Aug. "4 rooms = est 4 hours and
     for each rooms added, its an extra 30 minutes ... make the base fee
     110". So the flat rate is R110 on this one service, not R155.      */
  windowRooms: { base:4, hours:4, addMins:30, max:16 },

  /* CAR WASH — his sizes, 22 Aug. The hours are PLACEHOLDERS; he gave
     the list of vehicles but no times or prices for them.              */
  vehicles: [
    { id:'small',  name:'Small car',  hours:1,   sub:'Hatchback or city car' },
    { id:'medium', name:'Medium car', hours:1.5, sub:'Sedan' },
    { id:'big',    name:'Big car',    hours:2,   sub:'Large sedan or estate' },
    { id:'suv',    name:'SUV',        hours:2.5, sub:'Crossover or 4x4' },
    { id:'bakkie', name:'Bakkie',     hours:2.5, sub:'Single or double cab' },
    { id:'truck',  name:'Truck',      hours:3,   sub:'Light commercial' }
  ],

  /* Services. `estHours` on the hours-model services is a PLACEHOLDER —
     the client has priced indoor house cleaning, laundry and windows.
     `extraSet` says which extra tasks this service offers.
     `flatRate` overrides the R155 flat rate for that one service.      */
  services: [
    { id:'standard', group:'indoor',  name:'Standard house cleaning', model:'bedrooms', icon:'home',    addHours:0,   extraSet:'home',    desc:'Kitchen, bathrooms, bedrooms and living areas' },
    { id:'deep',     group:'indoor',  name:'Deep clean',              model:'bedrooms', icon:'sparkle', addHours:2,   extraSet:'home',    desc:'Everything in a standard clean, done to the corners', placeholder:true },
    { id:'move',     group:'indoor',  name:'Move-in / move-out',      model:'bedrooms', icon:'box',     addHours:3,   extraSet:'home',    desc:'Empty property, cupboards and appliances inside', placeholder:true },
    { id:'laundry',  group:'indoor',  name:'Laundry & ironing',       model:'laundry',  icon:'shirt',   desc:'Wash, dry, iron and fold' },
    { id:'office',   group:'indoor',  name:'Office cleaning',         model:'hours',    icon:'office',  estHours:5,   desc:'Desks, floors, kitchen and bathrooms', placeholder:true },
    { id:'outdoor',  group:'outdoor', name:'Outdoor cleaning',        model:'hours',    icon:'leaf',    estHours:4,   extraSet:'outdoor', desc:'Patios, driveways, walls and paving', placeholder:true },
    { id:'garden',   group:'outdoor', name:'Gardening',               model:'hours',    icon:'shovel',  estHours:4,   extraSet:'outdoor', desc:'Mowing, weeding, trimming and clearing', placeholder:true },
    { id:'windows',  group:'outdoor', name:'Window cleaning',         model:'rooms',    icon:'window',  flatRate:110, extraSet:'outdoor', desc:'In and out — glass, frames and sills, both sides' },
    { id:'carwash',  group:'outdoor', name:'Car wash',                model:'vehicle',  icon:'car',     desc:'Wash, rinse and dry, inside and out', placeholder:true }
  ],

  slots: ['07:00','08:00','09:00','10:00','11:00','12:00','13:00'],

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

/* ---------- money / time ----------
   Half an hour at R35 is R17.50, so totals land on 50c. Rounding those
   to a whole rand would quietly charge more than the price list says —
   show the cents instead, and only when there are any.                */
const money = n => {
  const c = Math.round(n * 100);
  const whole = Math.trunc(c / 100).toLocaleString('en-ZA').replace(/ /g, ' ');
  return CFG.currency + whole + (c % 100 ? '.' + String(c % 100).padStart(2, '0') : '');
};
const hoursLabel = h => {
  const m = Math.round(h * 60);
  const hh = Math.floor(m / 60), mm = m % 60;
  return hh ? `${hh}h${mm ? ' ' + mm + 'm' : ''}` : `${mm}m`;
};

/* ============================================================
   HOURS — the estimate, and the window the customer may move it in.

   "customer can change the hours by only being able to decrease by
    only 30 minutes and be able to increase with however minutes /
    hours (it should be in 30 minute range)"

   So: floor = estimate − 30 min. Ceiling = whatever is left under
   the 10-hour cap once the chosen extras are counted.
   ============================================================ */
/* Window cleaning: 4 rooms is 4 hours, and every room after that adds
   half an hour. Below 4 rooms he gave no figure, so 4 is the floor.  */
const roomsOf = b => Math.min(Math.max(Number(b.rooms) || CFG.windowRooms.base, CFG.windowRooms.base), CFG.windowRooms.max);
const roomHours = rooms => CFG.windowRooms.hours +
  Math.max(0, rooms - CFG.windowRooms.base) * CFG.windowRooms.addMins / 60;

function baseHoursFor(b){
  const svc = svcOf(b.service);
  if(!svc) return 0;
  if(svc.model === 'bedrooms'){
    const band = CFG.bedroomBands.find(x => x.id === b.band) || CFG.bedroomBands[0];
    return band.hours + (svc.addHours || 0);
  }
  if(svc.model === 'laundry'){
    const w = CFG.laundryWash.find(x => x.id === b.wash);
    const f = CFG.laundryFinish.find(x => x.id === b.finish);
    return (w ? w.hours : 0) + (f ? f.hours : 0);
  }
  if(svc.model === 'rooms')   return roomHours(roomsOf(b));
  if(svc.model === 'vehicle') return CFG.vehicles.find(v => v.id === b.vehicle)?.hours || 0;
  return svc.estHours || 0;
}

/* Which extra tasks this service offers, and which of them are ticked.
   Filtering by the set means an id left over from a previous service
   cannot quietly keep billing on the next one.                        */
const extrasFor = b => {
  const set = svcOf(b.service)?.extraSet;
  return set ? CFG.extras.filter(e => e.set === set) : [];
};
const chosenExtras = b => {
  const offered = extrasFor(b);
  return (b.extras || []).map(id => offered.find(e => e.id === id)).filter(Boolean);
};
const extrasMins = b => chosenExtras(b).reduce((n, e) => n + e.mins, 0);

const allowsExtras = b => extrasFor(b).length > 0;

/* The flat rate is R155 everywhere except window cleaning, where he
   set it to R110 on 22 Aug.                                          */
const flatOf = b => {
  const f = svcOf(b.service)?.flatRate;
  return f == null ? CFG.flatRate : f;
};

function hoursWindow(b){
  const est   = baseHoursFor(b);
  const exH   = allowsExtras(b) ? extrasMins(b) / 60 : 0;
  const min   = Math.max(0.5, est - CFG.reduceMins / 60);
  const max   = Math.max(min, CFG.maxHours - exH);
  return { est, min, max, extraHours: exH };
}

/* Can this extra still be ticked without pushing the cleaner past 10h?
   This is what greys tasks out on a 5+ bedroom job — 8 hours of base
   work leaves only 2 hours of extras before the cap bites.            */
function extraAllowed(b, id){
  if((b.extras || []).includes(id)) return true;      // already on, always removable
  const e = extrasFor(b).find(x => x.id === id);
  if(!e) return false;
  const svcH = b.hours != null ? b.hours : baseHoursFor(b);
  return svcH + extrasMins(b) / 60 + e.mins / 60 <= CFG.maxHours + 1e-9;
}

/* ============================================================
   PRICE ENGINE — one function. The booking flow, the customer
   dashboard, the cleaner job card and the admin order screen all
   call it, so they cannot disagree about what a job costs.

     total = R155 flat + (hours × R35) + extras + R35 service fee

   Extras are charged at the client's listed price and their time is
   added to the job; that time is NOT billed again at the hourly rate,
   which would charge for it twice. Flagged to him.
   ============================================================ */
function priceBooking(b){
  const svc = svcOf(b.service);
  if(!svc) return null;

  const win     = hoursWindow(b);
  const svcH    = b.hours != null ? Math.min(Math.max(b.hours, win.min), win.max) : win.est;
  const exMins  = allowsExtras(b) ? extrasMins(b) : 0;
  const hours   = svcH + exMins / 60;

  const labour  = svcH * CFG.hourlyRate;
  const extras  = chosenExtras(b).reduce((n, e) => n + e.price, 0);
  const flat    = flatOf(b);

  const total = flat + labour + extras + CFG.serviceFee;

  return {
    serviceName: svc.name, model: svc.model,
    flat, labour, extras,
    fee: CFG.serviceFee, total,
    serviceHours: svcH, hours,
    estHours: win.est, minHours: win.min, maxHours: win.max,
    hoursLabel: hoursLabel(hours), serviceHoursLabel: hoursLabel(svcH),
    overEstimate: Math.round((svcH - win.est) * 60),
    placeholder: !!svc.placeholder,
    extrasPlaceholder: chosenExtras(b).some(e => e.placeholder)
  };
}

/* ============================================================
   MOCK DATA — stands in for the API. Deliberately shared across
   all three dashboards so one booking reads the same from the
   customer, the cleaner and the admin side.
   ============================================================ */
const TODAY = '2026-08-19';                 // fixed so the demo repeats identically

const DB = {
  customer: {
    id:'cu1', name:'Thandi', surname:'Mokoena', initials:'TM',
    email:'thandi.m@example.co.za', phone:'+27 82 445 1190',
    joined:'March 2026', memberNo:'CUS-10428'
  },

  addresses: [
    { id:'a1', label:'Home', type:'Flat / Apartment', line:'18 Ocean View Drive', unit:'Flat 4B', suburb:'Sea Point', city:'Cape Town', prov:'Western Cape', notes:'Buzzer 12. Two cats — keep the balcony door shut.', primary:true },
    { id:'a2', label:'Mom’s place', type:'House', line:'7 Protea Street', unit:'', suburb:'Rondebosch', city:'Cape Town', prov:'Western Cape', notes:'Key under the ceramic pot.', primary:false },
    { id:'a3', label:'Office', type:'Townhouse', line:'12 Prestwich Street', unit:'Unit 3', suburb:'Green Point', city:'Cape Town', prov:'Western Cape', notes:'Reception has the access card.', primary:false }
  ],

  cards: [
    { id:'c1', brand:'Visa', last4:'4821', exp:'09/29', primary:true },
    { id:'c2', brand:'Mastercard', last4:'6613', exp:'04/28', primary:false }
  ],

  /* account: approved | pending | declined — only `approved` may sign in */
  cleaners: [
    { id:'cl1', name:'Nomsa',    surname:'Mabaso',  initials:'NM', rating:4.94, jobs:216, years:6, langs:['English','isiZulu','isiXhosa'], group:'indoor',  city:'Cape Town',    prov:'Western Cape',  account:'approved', fav:true,  skin:'#8a5a3b', hair:'#2a1e18', shirt:'#2F5D50', blocked:['2026-08-24'] },
    { id:'cl2', name:'Sipho',    surname:'Dlamini', initials:'SD', rating:4.81, jobs:143, years:4, langs:['English','isiZulu'],             group:'outdoor', city:'Cape Town',    prov:'Western Cape',  account:'approved', fav:true,  skin:'#6f4429', hair:'#181310', shirt:'#3E6FA3', blocked:[] },
    { id:'cl3', name:'Grace',    surname:'Nkosi',   initials:'GN', rating:4.88, jobs:302, years:9, langs:['English','Sesotho'],             group:'indoor',  city:'Cape Town',    prov:'Western Cape',  account:'approved', fav:false, skin:'#a8734a', hair:'#3a2418', shirt:'#B4573A', blocked:[] },
    { id:'cl7', name:'Zanele',   surname:'Ndlovu',  initials:'ZN', rating:4.76, jobs:64,  years:3, langs:['English','isiZulu'],             group:'indoor',  city:'Cape Town',    prov:'Western Cape',  account:'approved', fav:false, skin:'#7a4e30', hair:'#241a14', shirt:'#7A6A3A', blocked:['2026-08-20'] },
    { id:'cl8', name:'Thabo',    surname:'Maseko',  initials:'TM', rating:4.69, jobs:51,  years:2, langs:['English','Sesotho'],             group:'outdoor', city:'Cape Town',    prov:'Western Cape',  account:'approved', fav:false, skin:'#95643f', hair:'#1e1712', shirt:'#4C7A5A', blocked:[] },
    { id:'cl4', name:'Lerato',   surname:'Molefe',  initials:'LM', rating:4.72, jobs:88,  years:3, langs:['English','Setswana'],            group:'indoor',  city:'Johannesburg', prov:'Gauteng',       account:'approved', fav:false, skin:'#8a5a3b', hair:'#2e2018', shirt:'#8C5A8C', blocked:[] },
    { id:'cl5', name:'Andile',   surname:'Khumalo', initials:'AK', rating:0,    jobs:0,   years:2, langs:['English','isiXhosa'],            group:'outdoor', city:'Durban',       prov:'KwaZulu-Natal', account:'pending',  fav:false, skin:'#6f4429', hair:'#181310', shirt:'#3E6FA3', blocked:[] },
    { id:'cl6', name:'Precious', surname:'Sithole', initials:'PS', rating:0,    jobs:0,   years:5, langs:['English','isiZulu'],             group:'indoor',  city:'Cape Town',    prov:'Western Cape',  account:'pending',  fav:false, skin:'#a8734a', hair:'#2a1e18', shirt:'#2F5D50', blocked:[] },
    { id:'cl9', name:'Bongani',  surname:'Zulu',    initials:'BZ', rating:0,    jobs:0,   years:1, langs:['English'],                       group:'outdoor', city:'Cape Town',    prov:'Western Cape',  account:'declined', declineReason:'Criminal record check came back unresolved. Welcome to reapply once it clears.', fav:false, skin:'#7a4e30', hair:'#1e1712', shirt:'#8A8A8A', blocked:[] }
  ],

  customers: [
    { id:'cu1', name:'Thandi Mokoena', initials:'TM', email:'thandi.m@example.co.za', phone:'+27 82 445 1190', joined:'Mar 2026', tone:'' },
    { id:'cu2', name:'Riaan van Wyk',  initials:'RW', email:'riaan.vw@example.co.za', phone:'+27 83 220 7712', joined:'May 2026', tone:'sky' },
    { id:'cu3', name:'Aisha Patel',    initials:'AP', email:'aisha.p@example.co.za',  phone:'+27 71 998 0032', joined:'Jan 2026', tone:'clay' },
    { id:'cu4', name:'Johan Botha',    initials:'JB', email:'j.botha@example.co.za',  phone:'+27 84 551 3390', joined:'Aug 2026', tone:'gold' }
  ],

  /* status: paid -> upcoming -> inprogress -> completed | cancelled
     The customer picks the cleaner at checkout, so `cleaner` is always set. */
  bookings: [
    { id:'SPW-104312', cust:'cu1', service:'standard', band:'b34', hours:6,   extras:['oven','fridge'], addr:'a1', cleaner:'cl1', date:'2026-08-21', time:'09:00', status:'upcoming', note:'Please start with the kitchen.', rating:null },
    { id:'SPW-104298', cust:'cu1', service:'garden',   hours:4,               extras:[],                addr:'a2', cleaner:'cl2', date:'2026-08-22', time:'11:00', status:'upcoming', note:'Back garden only.', rating:null },
    { id:'SPW-104201', cust:'cu1', service:'laundry',  wash:'machine', finish:'dryiron', extras:[],     addr:'a3', cleaner:'cl3', date:'2026-08-25', time:'07:00', status:'upcoming', note:'', rating:null },
    { id:'SPW-103980', cust:'cu1', service:'standard', band:'b34', hours:6,   extras:['washfold'],      addr:'a1', cleaner:'cl1', date:'2026-08-11', time:'09:00', status:'completed', note:'', rating:{ stars:5, comment:'Nomsa was early, thorough and lovely with the cats. Booking her again.' } },
    { id:'SPW-103844', cust:'cu1', service:'deep',     band:'b34', hours:8,   extras:['oven'],          addr:'a1', cleaner:'cl3', date:'2026-07-29', time:'08:00', status:'completed', note:'', rating:{ stars:4, comment:'Great clean overall, skirting boards in the hallway were missed.' } },
    { id:'SPW-103702', cust:'cu1', service:'windows',  rooms:5, hours:4.5,    extras:[],                addr:'a2', cleaner:'cl2', date:'2026-07-15', time:'10:00', status:'completed', note:'', rating:null },
    { id:'SPW-103688', cust:'cu1', service:'carwash',  vehicle:'suv', hours:2.5, extras:[],             addr:'a1', cleaner:'cl8', date:'2026-07-04', time:'11:00', status:'completed', note:'Parked in bay 12.', rating:{ stars:5, comment:'Thabo did the inside as well without being asked.' } },
    { id:'SPW-103551', cust:'cu1', service:'outdoor',  hours:4,               extras:[],                addr:'a1', cleaner:'cl8', date:'2026-06-30', time:'13:00', status:'cancelled', note:'', rating:null },
    { id:'SPW-104355', cust:'cu2', service:'standard', band:'b12', hours:4,   extras:['fridge'],        addr:'a1', cleaner:'cl7', date:'2026-08-20', time:'10:00', status:'upcoming', note:'Gate code 4471.', rating:null },
    { id:'SPW-104361', cust:'cu3', service:'standard', band:'b5',  hours:8,   extras:['oven','fridge'], addr:'a1', cleaner:'cl3', date:'2026-08-20', time:'08:00', status:'upcoming', note:'', rating:null },
    { id:'SPW-104366', cust:'cu4', service:'garden',   hours:4,               extras:[],                addr:'a2', cleaner:'cl8', date:'2026-08-21', time:'09:00', status:'upcoming', note:'', rating:null },
    { id:'SPW-104290', cust:'cu3', service:'laundry',  wash:'hand', finish:'dryfold', extras:[],        addr:'a1', cleaner:'cl1', date:'2026-08-08', time:'07:00', status:'completed', note:'', rating:{ stars:5, comment:'Everything came back folded beautifully.' } },
    { id:'SPW-104277', cust:'cu2', service:'standard', band:'b12', hours:4,   extras:[],                addr:'a2', cleaner:'cl7', date:'2026-08-05', time:'09:00', status:'completed', note:'', rating:{ stars:4, comment:'Good job, arrived a little late.' } }
  ],

  /* Applications waiting on the admin — the form the cleaner submitted. */
  applications: [
    { id:'cl6', submitted:'2026-08-17' },
    { id:'cl5', submitted:'2026-08-18' }
  ],

  notifications: [
    { id:'n1', t:'Nomsa is confirmed for Friday', s:'Booking SPW-104312 · 2 hours ago', kind:'ok' },
    { id:'n2', t:'Your invoice for SPW-103980 is ready', s:'Yesterday', kind:'mute' },
    { id:'n3', t:'How did Grace do? Leave a rating', s:'2 days ago', kind:'wait' },
    { id:'n4', t:'Payment approved — R575', s:'3 days ago', kind:'ok' }
  ]
};

/* Documents every applicant uploads, per the cleaner spec. */
const DOCS = [
  { id:'id',   name:'ID / passport',        file:'id-document.pdf',   size:'412 KB' },
  { id:'photo',name:'Head & shoulders photo',file:'profile-photo.jpg', size:'268 KB' },
  { id:'crim', name:'Criminal record check', file:'police-clearance.pdf', size:'701 KB' },
  { id:'permit',name:'Work permit',          file:'work-permit.pdf',   size:'355 KB' }
];

/* ---------- lookups ---------- */
const byId    = (arr, id) => arr.find(x => x.id === id) || null;
const cleaner = id => byId(DB.cleaners, id);
const address = id => byId(DB.addresses, id);
const custOf  = id => byId(DB.customers, id);
const svcOf   = id => CFG.services.find(s => s.id === id);
/* A booking's address may be a saved-address id or a one-off object
   typed in at checkout (guests have no saved addresses).            */
const addrOf  = b => (b && typeof b.addr === 'object' && b.addr) ? b.addr : address(b && b.addr);

const STATUS = {
  paid:      { label:'Paid',        cls:'ok'   },
  upcoming:  { label:'Upcoming',    cls:'ok'   },
  inprogress:{ label:'In progress', cls:'live' },
  completed: { label:'Completed',   cls:'mute' },
  cancelled: { label:'Cancelled',   cls:'bad'  }
};
const statusPill = s => `<span class="pill ${STATUS[s].cls}">${STATUS[s].label}</span>`;

const ACCOUNT = {
  approved: { label:'Approved', cls:'ok'   },
  pending:  { label:'Pending',  cls:'wait' },
  declined: { label:'Declined', cls:'bad'  }
};

/* What was actually booked, in one line. The cleaner needs to know it
   is an SUV and not a hatchback before they arrive, so all three
   dashboards print this.                                            */
function jobDetail(b){
  const svc = svcOf(b.service);
  if(!svc) return '';
  if(svc.model === 'bedrooms')
    return (CFG.bedroomBands.find(x => x.id === b.band) || CFG.bedroomBands[0]).label;
  if(svc.model === 'laundry'){
    const w = CFG.laundryWash.find(x => x.id === b.wash);
    const f = CFG.laundryFinish.find(x => x.id === b.finish);
    return [w && w.name, f && f.name].filter(Boolean).join(' · ') || svc.desc;
  }
  if(svc.model === 'rooms'){
    const n = roomsOf(b);
    return `${n} room${n > 1 ? 's' : ''} · windows in and out`;
  }
  if(svc.model === 'vehicle')
    return CFG.vehicles.find(v => v.id === b.vehicle)?.name || svc.desc;
  return svc.desc;
}

/* ============================================================
   AVAILABILITY — "list all the workers available around the area
   for that day". A cleaner shows up only if they do that kind of
   work, cover that city, are approved, have not blocked the day
   off, and still have room under the 10-hour cap.
   ============================================================ */
function bookedHoursOn(cleanerId, date){
  return DB.bookings
    .filter(b => b.cleaner === cleanerId && b.date === date &&
                 b.status !== 'cancelled')
    .reduce((n, b) => n + (priceBooking(b)?.hours || 0), 0);
}

function availableCleaners(b){
  const svc = svcOf(b.service);
  const ad  = addrOf(b);
  if(!svc || !ad || !b.date) return [];
  const need = priceBooking(b)?.hours || 0;
  return DB.cleaners.filter(c =>
    c.account === 'approved' &&
    c.group === svc.group &&
    c.city === ad.city &&
    !(c.blocked || []).includes(b.date) &&
    bookedHoursOn(c.id, b.date) + need <= CFG.maxHours + 1e-9
  ).sort((x, y) => y.rating - x.rating);
}

/* Ratings a cleaner has actually been given, from the bookings. */
function reviewsFor(cleanerId){
  return DB.bookings
    .filter(b => b.cleaner === cleanerId && b.rating)
    .map(b => ({ ...b.rating, id:b.id, date:b.date, cust:custOf(b.cust)?.name || '' }));
}
function ratingOf(cleanerId){
  const r = reviewsFor(cleanerId);
  if(!r.length) return null;
  return Math.round(r.reduce((n, x) => n + x.stars, 0) / r.length * 100) / 100;
}

/* ---------- dates ---------- */
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const dateOf = iso => { const [y,m,d] = iso.split('-').map(Number); return new Date(y, m-1, d); };
const isoOf  = dt => `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;
const fmtDate     = iso => { const dt = dateOf(iso); return `${DAYS[dt.getDay()]} ${dt.getDate()} ${MON[dt.getMonth()]}`; };
const fmtDateLong = iso => { const dt = dateOf(iso); return `${DAYS[dt.getDay()]} ${dt.getDate()} ${MON[dt.getMonth()]} ${dt.getFullYear()}`; };
const isPast = iso => iso < TODAY;
const starRow = n => '★'.repeat(Math.round(n)) + '☆'.repeat(5 - Math.round(n));

/* ============================================================
   PORTRAIT — the cleaner's uploaded head-and-shoulders photo goes
   here. Until there is a backend to hold real uploads this draws a
   deterministic illustration so the card layout is honest about
   its shape without inventing a person's face.
   ============================================================ */
function portrait(c, size = 84){
  const s = c || {};
  return `<svg class="portrait" width="${size}" height="${size}" viewBox="0 0 100 100" role="img" aria-label="${s.name || ''} ${s.surname || ''}">
    <defs><clipPath id="pc${s.id || 'x'}"><circle cx="50" cy="50" r="50"/></clipPath></defs>
    <g clip-path="url(#pc${s.id || 'x'})">
      <rect width="100" height="100" fill="#E7E1D5"/>
      <path d="M50 62c19 0 33 13 36 30v8H14v-8c3-17 17-30 36-30z" fill="${s.shirt || '#2F5D50'}"/>
      <circle cx="50" cy="41" r="20" fill="${s.skin || '#8a5a3b'}"/>
      <path d="M30 39c0-13 9-21 20-21s20 8 20 21c0-6-8-9-20-9s-20 3-20 9z" fill="${s.hair || '#2a1e18'}"/>
      <circle cx="43" cy="42" r="1.9" fill="#2b211a"/><circle cx="57" cy="42" r="1.9" fill="#2b211a"/>
      <path d="M45 50c3 2.4 7 2.4 10 0" stroke="#2b211a" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    </g>
  </svg>`;
}

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
  car:'<path d="M4 16v2.5a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5V12l2.2-5.4a1 1 0 0 1 .93-.6h9.74a1 1 0 0 1 .93.6L18 12v6.5a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5V16"/><path d="M2 12h16"/><circle cx="6" cy="14" r="1"/><circle cx="14" cy="14" r="1"/><path d="M20 9l2 1.5-2 1.5"/>',
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
  download:'<path d="M12 4v12M8 12l4 4 4-4"/><path d="M4 18v1a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-1"/>',
  chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  shield:'<path d="M12 3l7 3v5c0 4.4-3 8.3-7 10-4-1.7-7-5.6-7-10V6l7-3z"/>',
  star:'<path d="M12 4l2.4 5 5.6.8-4 4 1 5.5-5-2.7-5 2.7 1-5.5-4-4 5.6-.8z"/>',
  mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5L12 13l8.5-6.5"/>',
  lock:'<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  logout:'<path d="M15 17l5-5-5-5"/><path d="M20 12H9"/><path d="M12 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.01"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  back:'<path d="M19 12H5M11 6l-6 6 6 6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  minus:'<path d="M5 12h14"/>',
  search:'<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4 4"/>',
  camera:'<path d="M4 8h3l1.6-2h6.8L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.6"/>'
};
const ico = (k, sz = 20, sw = 1.7) =>
  `<svg width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${I[k] || ''}</svg>`;

/* ---------- tiny UI helpers ---------- */
const $  = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

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

function modal({ title, sub, body, actions = [], wide = false }){
  const veil = document.createElement('div');
  veil.className = 'veil on';
  veil.innerHTML = `
    <div class="modal${wide ? ' wide' : ''}" role="dialog" aria-modal="true">
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
    if(a.id) b.id = a.id;
    b.onclick = () => { const keep = a.fn && a.fn(veil); if(!keep) veil.remove(); };
    foot.appendChild(b);
  });
  veil.querySelector('[data-close]').onclick = () => veil.remove();
  veil.onclick = e => { if(e.target === veil) veil.remove(); };
  document.body.appendChild(veil);
  return veil;
}

/* ============================================================
   NOTIFICATIONS — every automatic email / SMS in the brief is
   rendered here exactly as it would be sent, so the wording can be
   signed off before there is a mail server to send it with.
   ============================================================ */
const SENT = [];      // an outbox the admin dashboard can show

function sendNotice({ channel, to, subject, body }){
  SENT.unshift({ channel, to, subject, body, at:'just now' });
  return modal({
    title: channel === 'sms' ? 'SMS queued' : 'Email queued',
    sub: 'This is the message the platform sends automatically. No mail server is wired up yet — this is the exact wording for you to approve.',
    body: `<div class="mailer">
        <div class="mail-hd">
          <div><span class="mail-lbl">To</span> ${esc(to)}</div>
          ${subject ? `<div><span class="mail-lbl">Subject</span> ${esc(subject)}</div>` : ''}
        </div>
        <div class="mail-bd">${body}</div>
      </div>`,
    actions: [{ label:'Close', cls:'btn-primary' }],
    wide: true
  });
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
