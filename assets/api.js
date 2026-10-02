/* ============================================================
   Sparrow — the bridge between the four screens and the database.

   The screens were built against an in-memory `DB` object. Rather than
   rewrite them, this file fills that same object from the real API when
   one is reachable, and sends changes back. The render code does not
   know or care which it is looking at.

   WHY IT PROBES INSTEAD OF BEING CONFIGURED
   The same four HTML files are served two ways: from GitHub Pages, where
   there is no PHP and no database, and from a real host where there is.
   On boot it asks the API whether it is there. If it answers, the site
   runs on MySQL. If it does not, the site runs on the sample data and
   says so in the bar at the top. One build, both modes.

   A 200 is not enough to decide that. A web server with no PHP can
   answer /api/health with a styled 404 page, and `await res.json()` on
   an HTML body throws somewhere far away from the cause. So the API
   stamps every response with X-Sparrow-Api, and that header is what is
   checked.
   ============================================================ */
const API = {
  live: false,
  base: null,
  role: null,      // 'customer' | 'employee' | 'admin' once signed in
  user: null,

  /* Candidate locations, in the order they are tried. Covers the site
     and the API sharing a domain, and the API sitting in the backend
     folder of the same checkout. */
  candidates(){
    const here = location.href.replace(/[^/]*$/, '');
    return [here + 'api/', here + 'backend/api/', here + 'backend/api/index.php/'];
  },

  async probe(){
    for (const base of this.candidates()){
      try {
        const res = await fetch(base + 'health', { credentials:'include' });
        if (res.ok && res.headers.get('X-Sparrow-Api')){
          const j = await res.json();
          if (j && j.service === 'sparrow-api'){
            this.base = base;
            this.live = true;
            return true;
          }
        }
      } catch (e) { /* not there; try the next one */ }
    }
    return false;
  },

  async call(path, body, method){
    const res = await fetch(this.base + path.replace(/^\//, ''), {
      method: method || (body !== undefined ? 'POST' : 'GET'),
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
    let data = {};
    try { data = await res.json(); } catch (e) {}
    if (!res.ok){
      const err = new Error(data.error || ('Request failed: ' + res.status));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },

  get(p){ return this.call(p); },
  post(p, b){ return this.call(p, b || {}); }
};

/* ---------- shapes ----------
   The API speaks SQL column names; the screens speak the prototype's
   field names. Everything that translates between the two lives here,
   so there is exactly one place to look when a field is wrong. */

const toNum = v => v == null ? null : Number(v);

function cfgFromCatalog(cat){
  const s = cat.settings || {};
  CFG.hourlyRate   = Number(s.hourly_rate);
  CFG.serviceFee   = Number(s.service_fee);
  CFG.flatRate     = Number(s.flat_rate);
  CFG.maxHours     = Number(s.max_hours);
  CFG.stepMins     = Number(s.step_minutes);
  CFG.reduceMins   = Number(s.reduce_minutes);
  CFG.carWashHours = Number(s.car_wash_hours);

  /* The icon is presentation, not data, so it stays on the client and is
     matched by code. A service added in the database that this build has
     never heard of still renders, with a neutral icon. */
  const ICONS = { standard:'home', deep:'sparkle', move:'box', laundry:'shirt',
                  office:'office', outdoor:'leaf', garden:'shovel',
                  windows:'window', carwash:'car' };
  CFG.services = cat.services.map(s => ({
    id: s.code,
    name: s.name,
    desc: s.description,
    group: s.service_group,
    model: s.pricing_model,
    icon: ICONS[s.code] || 'sparkle',
    flatRate: s.flat_rate_override == null ? undefined : Number(s.flat_rate_override),
    estHours: s.est_hours == null ? undefined : Number(s.est_hours),
    addHours: Number(s.add_hours || 0),
    extraSet: s.extra_set || undefined,
    placeholder: !!Number(s.hours_are_estimated)
  }));
  CFG.extras = cat.extras.map(e => ({
    id: e.code,
    name: e.name,
    sub: e.description || undefined,
    set: e.extra_set,
    mins: Number(e.minutes),
    price: Number(e.price),
    placeholder: !!Number(e.price_is_estimated)
  }));
}

function orderToBooking(o){
  return {
    id: o.reference,
    cust: 'cu' + o.customer_id,
    service: o.service_code,
    band: o.bedroom_band || undefined,
    wash: o.laundry_wash || undefined,
    finish: o.laundry_finish || undefined,
    rooms: o.window_rooms == null ? undefined : Number(o.window_rooms),
    vehicle: o.vehicle_size || undefined,
    hours: Number(o.hours_booked),
    extras: (o.extras || []).map(e => e.extra_code),
    addr: {
      line: o.address_line, unit: o.address_unit || '', suburb: o.address_suburb,
      city: o.address_city, prov: o.address_province, notes: o.access_notes || '',
      label: 'Booked address', type: 'House'
    },
    cleaner: o.employee_id == null ? null : 'cl' + o.employee_id,
    date: o.scheduled_date,
    time: (o.scheduled_time || '').slice(0, 5),
    status: o.status === 'pending_payment' ? 'paid' : o.status,
    note: o.note_for_worker || '',
    rating: o.rating_stars ? { stars: Number(o.rating_stars), comment: o.rating_comment || '' } : null,
    /* The money as it was charged, carried through rather than recomputed,
       so a past order on screen matches the row in the database even after
       a price change. */
    frozen: {
      flat: Number(o.flat_rate), labour: Number(o.labour_total),
      extras: Number(o.extras_total), fee: Number(o.service_fee),
      total: Number(o.total), hourlyRate: Number(o.hourly_rate)
    }
  };
}

function cleanerFromApi(c){
  return {
    id: 'cl' + c.id,
    name: c.first_name,
    surname: c.last_name,
    initials: (c.first_name[0] || '') + (c.last_name[0] || ''),
    rating: Number(c.rating || 0),
    jobs: Number(c.jobs || 0),
    years: Number(c.years_experience || 0),
    langs: c.languages || [],
    group: c.service_group,
    city: c.cities ? String(c.cities).split(',')[0] : (c.city || ''),
    prov: c.province || '',
    account: c.account_status || 'approved',
    fav: false,
    /* The drawn portrait needs three colours. Deriving them from the id
       keeps a given worker looking the same on every screen and on every
       reload, which a random pick would not. */
    skin:  ['#8a5a3b','#6f4429','#a8734a','#7a4e30','#95643f'][c.id % 5],
    hair:  ['#2a1e18','#181310','#3a2418','#241a14','#1e1712'][c.id % 5],
    shirt: ['#2F5D50','#3E6FA3','#B4573A','#7A6A3A','#4C7A5A'][c.id % 5],
    blocked: c.unavailable || []
  };
}

/* ---------- boot ---------- */

API.boot = async function({ role } = {}){
  if (!(await this.probe())) return false;

  const cat = await this.get('catalog');
  cfgFromCatalog(cat);

  // Who, if anyone, is already signed in on this browser.
  if (role === 'customer' || !role){
    try {
      const me = await this.get('customer/me');
      this.role = 'customer';
      this.user = me.customer;
      DB.customers = [{
        id: 'cu' + me.customer.id,
        name: me.customer.first_name + ' ' + me.customer.last_name,
        initials: me.customer.first_name[0] + me.customer.last_name[0],
        email: me.customer.email, phone: me.customer.phone || '', tone: '',
        joined: (me.customer.created_at || '').slice(0, 7)
      }];
      DB.addresses = me.addresses.map(a => ({
        id: 'a' + a.id, label: a.label, type: a.property_type, line: a.street_line,
        unit: a.unit_number || '', suburb: a.suburb, city: a.city, prov: a.province,
        notes: a.access_notes || '', primary: !!Number(a.is_primary)
      }));
      DB.bookings = me.orders.map(orderToBooking);
      this.favourites = (me.favourites || []).map(id => 'cl' + id);
    } catch (e) { /* nobody signed in; the screens show their guest state */ }
  }
  return true;
};

/* ---------- actions the screens call ---------- */

API.availability = async function(b, date, city){
  const p = priceBooking(b);
  const qs = new URLSearchParams({
    date, city, service: b.service, hours: String(p ? p.hours : 1)
  });
  const r = await this.get('availability?' + qs);
  return r.cleaners.map(cleanerFromApi);
};

API.createOrder = function(b, address, customer){
  return this.post('orders', {
    service: b.service, band: b.band, wash: b.wash, finish: b.finish,
    rooms: b.rooms, vehicle: b.vehicle, hours: b.hours,
    extras: b.extras || [],
    date: b.date, time: b.time,
    employee_id: Number(String(b.cleaner).replace('cl', '')),
    address, note: b.note || '',
    ...(customer || {})
  });
};

API.rateOrder = (ref, stars, comment) => API.post(`orders/${ref}/rate`, { stars, comment });
API.cancelOrder = (ref, reason) => API.post(`orders/${ref}/cancel`, { reason });
API.blockDay = (date, remove) => API.post('employee/unavailability', { date, remove: !!remove });
API.decide = (id, decision, reason) =>
  API.post(`admin/applications/${id}/decide`, { decision, reason });

/* A visible, honest label. Nobody should have to guess whether what they
   are looking at is real data or the sample set. */
API.badge = function(){
  return this.live
    ? '<span class="pill ok" title="' + this.base + '">Live database</span>'
    : '<span class="pill mute">Sample data, no database</span>';
};
