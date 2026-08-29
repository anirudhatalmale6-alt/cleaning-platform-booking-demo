/* ============================================================
   The browser twin of bot/engine.py + bot/validate.py.

   It reads the SAME flow.json the server reads, so the demo cannot say
   anything the real bot would not say. tests/test_parity.py runs a set of
   scripted conversations through both this file and the Python engine and
   fails if a single reply differs.

   Exposed for the tests as window.WA.
   ============================================================ */
(function (global) {
'use strict';

const MIN_AGE = 18, MAX_AGE = 80;
const BTN_TITLE_MAX = 20, ROW_TITLE_MAX = 24, ROW_DESC_MAX = 72, MAX_ROWS = 10, MAX_BUTTONS = 3;

/* ---------------------------------------------------------- validation */

const digits = s => (s || '').replace(/\D/g, '');
const strip  = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');

function luhnOk(n){
  if(!/^\d+$/.test(n)) return false;
  let total = 0, alt = false;
  for(let i = n.length - 1; i >= 0; i--){
    let d = +n[i];
    if(alt){ d *= 2; if(d > 9) d -= 9; }
    total += d; alt = !alt;
  }
  return total % 10 === 0;
}

function normaliseSaNumber(raw){
  let d = digits(raw);
  if(d.startsWith('0027'))                    d = '0' + d.slice(4);
  else if(d.startsWith('27') && d.length === 11) d = '0' + d.slice(2);
  else if(d.length === 9 && d[0] !== '0')     d = '0' + d;
  return d;
}

const MONTHS = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];

function mkDate(y, m, d){
  const dt = new Date(Date.UTC(y, m - 1, d));
  if(dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
  return dt;
}
const iso = dt => dt.toISOString().slice(0, 10);

function parseDate(raw){
  const s = (raw || '').trim().toLowerCase().replace(/,/g, ' ');
  let y, mo, d, m;
  if((m = s.match(/^(\d{4})[-/. ](\d{1,2})[-/. ](\d{1,2})$/))){
    y = +m[1]; mo = +m[2]; d = +m[3];
  } else if((m = s.match(/^(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{2,4})$/))){
    d = +m[1]; mo = +m[2]; y = +m[3];
  } else if((m = s.match(/^(\d{1,2})\s+([a-z]+)\s+(\d{2,4})$/))){
    d = +m[1]; mo = MONTHS.indexOf(m[2].slice(0, 3)) + 1; y = +m[3];
    if(!mo) return null;
  } else return null;
  if(y < 100) y += y > 25 ? 1900 : 2000;
  return mkDate(y, mo, d);
}

function ageOn(born, today){
  let a = today.getUTCFullYear() - born.getUTCFullYear();
  const bm = born.getUTCMonth(), bd = born.getUTCDate();
  const tm = today.getUTCMonth(), td = today.getUTCDate();
  if(tm < bm || (tm === bm && td < bd)) a--;
  return a;
}

function saIdBirthdate(id, today){
  const yy = +id.slice(0, 2), mm = +id.slice(2, 4), dd = +id.slice(4, 6);
  for(const century of [1900, 2000]){
    const dt = mkDate(century + yy, mm, dd);
    if(!dt) continue;
    const a = ageOn(dt, today);
    if(a >= MIN_AGE && a <= MAX_AGE) return dt;
  }
  return null;
}

const V = {
  name(raw){
    const s = (raw || '').trim().replace(/\s+/g, ' ');
    const plain = strip(s);
    if(s.length < 2 || s.length > 40) return [false, null, true];
    if(!/^[A-Za-z][A-Za-z' -]*$/.test(plain)) return [false, null, true];
    if(plain.replace(/[^A-Za-z]/g, '').length < 2) return [false, null, true];
    return [true, s.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '), null];
  },
  sentence(raw){
    const s = (raw || '').trim().replace(/\s+/g, ' ');
    return s.length < 6 ? [false, null, true] : [true, s, null];
  },
  email(raw){
    const s = (raw || '').trim().toLowerCase();
    if(!/^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/.test(s) || s.length > 120) return [false, null, true];
    return [true, s, null];
  },
  years(raw){
    const m = (raw || '').trim().match(/^(\d{1,2})(\s*(years?|yrs?))?$/i);
    if(!m) return [false, null, true];
    const n = +m[1];
    return (n < 0 || n > 50) ? [false, null, true] : [true, n, null];
  },
  sa_mobile(raw){
    const d = normaliseSaNumber(raw);
    if(d.length !== 10 || d[0] !== '0' || !'678'.includes(d[1])) return [false, null, true];
    return [true, d, null];
  },
  sa_phone(raw){
    const d = normaliseSaNumber(raw);
    if(d.length !== 10 || d[0] !== '0' || !'12345678'.includes(d[1])) return [false, null, true];
    return [true, d, null];
  },
  dob(raw, ctx){
    const d = parseDate(raw);
    if(!d) return [false, null, true];
    const a = ageOn(d, ctx.today);
    if(a < MIN_AGE) return [false, null, 'under_age'];
    if(a > MAX_AGE) return [false, null, true];
    return [true, iso(d), null];
  },
  id_number(raw, ctx){
    const s = (raw || '').trim().toUpperCase().replace(/ /g, '');
    if((ctx.kind || 'id') !== 'id'){
      return /^[A-Z0-9]{6,15}$/.test(s) ? [true, s, null] : [false, null, true];
    }
    const d = digits(s);
    if(d.length !== 13 || !luhnOk(d)) return [false, null, true];
    const born = saIdBirthdate(d, ctx.today);
    if(!born) return [false, null, true];
    if(ctx.dob && iso(born) !== ctx.dob) return [false, null, 'dob_mismatch'];
    return [true, d, null];
  }
};

function runValidator(kind, raw, ctx){
  const fn = V[kind];
  return fn ? fn(raw, ctx || {}) : [true, (raw || '').trim(), null];
}

/* ---------------------------------------------------------- rendering */

const clip = (s, n) => { s = s || ''; return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+$/, '') + '…'; };

const MONTH_NAMES = ['January','February','March','April','May','June','July',
                     'August','September','October','November','December'];

function fmtDate(s){
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
  return m ? `${+m[3]} ${MONTH_NAMES[+m[2] - 1]} ${+m[1]}` : s;
}
const fmtPhone = d => (d && d.length === 10 && /^\d+$/.test(d))
  ? `${d.slice(0,3)} ${d.slice(3,6)} ${d.slice(6)}` : d;

function stepById(flow, id){ return flow.steps.find(s => s.id === id) || null; }

function labelFor(flow, field, value){
  return ((flow.valueLabels || {})[field] || {})[value] || value;
}

function display(flow, field, value){
  if(value === null || value === undefined || value === '') return '—';
  if(Array.isArray(value)) return value.join(', ');
  if(field === 'dob') return fmtDate(value);
  if(['phone','r1Phone','r2Phone'].includes(field)) return fmtPhone(value);
  if(field === 'idNum' && String(value).length > 6){
    const v = String(value);
    return v.slice(0, 6) + '•'.repeat(v.length - 6);
  }
  return String(labelFor(flow, field, value));
}

function interpolate(flow, text, answers){
  return (text || '').replace(/\{(\w+)\}/g, (_, key) => {
    if(key === 'idKindLabel') return flow.idKindLabels[answers.idKind || 'id'] || 'ID';
    const v = answers[key];
    return (v === undefined || v === null) ? '' : display(flow, key, v);
  });
}

function optionsFor(flow, step, state){
  const src = step.optionsFrom;
  if(!src) return (step.options || []).map(o => Object.assign({}, o));
  if(src === 'provinces') return Object.keys(flow.optionSets.provinces).map(p => ({id:p, title:p}));
  if(src === 'cities'){
    const prov = state.answers.prov || Object.keys(flow.optionSets.provinces)[0];
    return flow.optionSets.provinces[prov].map(c => ({id:c, title:c}));
  }
  if(src === 'languages') return flow.optionSets.languages.map(l => ({id:l, title:l}));
  if(src === 'editable') return flow.editable.map((e, i) => ({id:String(i), title:e.title}));
  return [];
}

function summary(flow, state){
  const lines = [];
  for(const row of flow.summaryRows){
    const vals = row.fields.map(f => display(flow, f, state.answers[f])).filter(v => v && v !== '—');
    if(!vals.length) continue;
    lines.push(`*${row.label}:* ` + vals.join(' · ') + (row.suffix || ''));
  }
  const got = ['upId','upPhoto','upCrim'].filter(f => state.media[f]).length;
  lines.push(`*Documents:* ${got} of 3 received`);
  return lines.join('\n');
}

function render(flow, state){
  const step = stepById(flow, state.step);
  if(!step) return [];
  const answers = Object.assign({}, state.answers);
  let text = interpolate(flow, step.text, answers);
  if(step.text.includes('{summary}')) text = step.text.replace('{summary}', summary(flow, state));
  if(step.hint) text += '\n\n_' + interpolate(flow, step.hint, answers) + '_';

  if(step.kind === 'buttons'){
    return [{kind:'buttons', text, options: optionsFor(flow, step, state)
      .slice(0, MAX_BUTTONS).map(o => ({id:o.id, title:clip(o.title, BTN_TITLE_MAX)}))}];
  }
  if(step.kind === 'list'){
    return [{kind:'list', text, button: step.button || 'Choose',
      rows: optionsFor(flow, step, state).slice(0, MAX_ROWS)
        .map(o => ({id:o.id, title:clip(o.title, ROW_TITLE_MAX), description:''}))}];
  }
  if(step.kind === 'multi'){
    const chosen = state.answers[step.field] || [];
    const rows = optionsFor(flow, step, state).map(o => {
      const picked = chosen.includes(o.id);
      return {id:o.id, title:clip((picked ? '✅ ' : '') + o.title, ROW_TITLE_MAX),
              description: clip(picked ? 'Chosen — tap to remove' : '', ROW_DESC_MAX)};
    });
    if(chosen.length >= (step.min || 1))
      rows.push({id:step.doneId, title:clip(step.doneTitle, ROW_TITLE_MAX),
                 description:clip('Chosen: ' + chosen.join(', '), ROW_DESC_MAX)});
    if(chosen.length) text += '\n\nSo far: *' + chosen.join(', ') + '*';
    return [{kind:'list', text, button: step.button || 'Choose', rows: rows.slice(0, MAX_ROWS)}];
  }
  if(step.kind === 'text' && step.options){
    return [{kind:'buttons', text, options: step.options.slice(0, MAX_BUTTONS)
      .map(o => ({id:o.id, title:clip(o.title, BTN_TITLE_MAX)}))}];
  }
  return [{kind:'text', text}];
}

/* ---------------------------------------------------------- movement */

function newState(){
  return {step:'welcome', answers:{}, media:{}, history:[],
          editUntil:null, appId:null, submitted:null, started:false};
}

function goto(state, id, push){
  if(push !== false && state.step !== id) state.history.push(state.step);
  state.step = id;
  return state;
}

function advance(state, step){
  if(state.editUntil === step.id){ state.editUntil = null; return goto(state, 'review'); }
  return goto(state, step.next);
}

function matchText(flow, step, state, lowered){
  if(!lowered) return null;
  let opts = optionsFor(flow, step, state);
  if(step.kind === 'multi') opts = opts.concat([{id:step.doneId, title:step.doneTitle}]);
  for(const o of opts)
    if(lowered === o.title.toLowerCase() || lowered === String(o.id).toLowerCase()) return o.id;
  const hits = opts.filter(o => o.title.toLowerCase().includes(lowered));
  if(hits.length === 1) return hits[0].id;
  if(/^\d+$/.test(lowered)){
    const i = +lowered - 1;
    if(i >= 0 && i < opts.length) return opts[i].id;
  }
  return null;
}

/* ---------------------------------------------------------- the entry point */

function handle(state, msg, flow, opts){
  opts = opts || {};
  const today = opts.today ? new Date(opts.today + 'T00:00:00Z') : new Date();
  state = state ? JSON.parse(JSON.stringify(state)) : newState();

  const text = (msg.text || '').trim();
  const lowered = text.toLowerCase();
  let choice = msg.id || null;
  const mtype = msg.type || 'text';

  if(mtype === 'text' && lowered){
    const c = flow.commands;
    if(c.cancel.includes(lowered))
      return [newState(), [{kind:'text', text:flow.texts.cancelled}]];
    if(c.help.includes(lowered))
      return [state, [{kind:'text', text:flow.texts.help}].concat(render(flow, state))];
    if(c.restart.includes(lowered)){
      const s = newState(); s.started = true; s.step = 'first_name';
      return [s, [{kind:'text', text:flow.texts.restarted}].concat(render(flow, s))];
    }
    if(c.back.includes(lowered)){
      if(!state.history.length)
        return [state, [{kind:'text', text:flow.texts.back_at_start}].concat(render(flow, state))];
      state.step = state.history.pop();
      state.editUntil = null;
      return [state, render(flow, state)];
    }
    if(lowered === 'status' && state.appId)
      return [state, [{kind:'text', text: flow.texts.already_applied
        .replace('{appId}', state.appId).replace('{submitted}', fmtDate(state.submitted))}]];
  }

  if(state.appId)
    return [state, [{kind:'text', text: flow.texts.already_applied
      .replace('{appId}', state.appId).replace('{submitted}', fmtDate(state.submitted))}]];

  if(!state.started){
    state.started = true;
    state.step = 'welcome';
    return [state, render(flow, state)];
  }

  const step = stepById(flow, state.step);
  if(!step){ const s = newState(); s.started = true; return [s, render(flow, s)]; }

  if(step.kind === 'end'){ const s = newState(); s.started = true; return [s, render(flow, s)]; }

  if(step.kind === 'buttons' || step.kind === 'list'){
    const valid = new Set(optionsFor(flow, step, state).map(o => o.id));
    if(!valid.has(choice)) choice = matchText(flow, step, state, lowered);
    if(choice === null)
      return [state, [{kind:'text', text:flow.texts.unknown_option}].concat(render(flow, state))];

    if(step.id === 'fix_pick'){
      const entry = flow.editable[+choice];
      state.editUntil = entry.to;
      return [goto(state, entry.from), render(flow, state)];
    }
    if(step.field) state.answers[step.field] = choice;

    const target = (step.routes || {})[choice] || step.next;
    if(target === '__restart'){
      const s = newState(); s.started = true; s.step = 'first_name';
      return [s, [{kind:'text', text:flow.texts.restarted}].concat(render(flow, s))];
    }
    if(target === 'submitted'){
      state.appId = (opts.submitter ? opts.submitter(state) : 'SPW-A1001');
      state.submitted = opts.today || iso(new Date());
      state.answers.appId = state.appId;
      goto(state, 'submitted');
      return [state, render(flow, state)];
    }
    if(state.editUntil === step.id){
      state.editUntil = null;
      return [goto(state, 'review'), render(flow, state)];
    }
    return [goto(state, target), render(flow, state)];
  }

  if(step.kind === 'multi'){
    const chosen = (state.answers[step.field] || []).slice();
    const ids = new Set(optionsFor(flow, step, state).map(o => o.id));
    if(!ids.has(choice) && choice !== step.doneId) choice = matchText(flow, step, state, lowered);
    if(choice === step.doneId){
      if(chosen.length < (step.min || 1)) return [state, render(flow, state)];
      state.answers[step.field] = chosen;
      return [advance(state, step), render(flow, state)];
    }
    if(choice === null)
      return [state, [{kind:'text', text:flow.texts.unknown_option}].concat(render(flow, state))];
    const i = chosen.indexOf(choice);
    if(i >= 0) chosen.splice(i, 1); else chosen.push(choice);
    state.answers[step.field] = chosen;
    return [state, render(flow, state)];
  }

  if(step.kind === 'media'){
    if(!step.accepts.includes(mtype)){
      const key = (step.accepts.length === 1 && step.accepts[0] === 'image') ? 'image' : 'any';
      return [state, [{kind:'text', text:flow.mediaErrors[key]}]];
    }
    state.media[step.field] = {type:mtype, id:msg.media_id || null,
                               mime:msg.mime || null, filename:msg.filename || null};
    state.answers[step.field] = msg.filename || (step.field + '.' + mtype);
    return [advance(state, step), render(flow, state)];
  }

  if(step.kind === 'text'){
    if(choice === 'use_this' && opts.sender){
      const [ok, val] = runValidator('sa_mobile', opts.sender, {});
      if(ok){
        state.answers[step.field] = val;
        return [advance(state, step), render(flow, state)];
      }
    }
    const ctx = {today};
    if(step.field === 'idNum'){
      ctx.kind = state.answers.idKind || 'id';
      ctx.dob  = state.answers.dob;
    }
    const [ok, val, err] = runValidator(step.validator, text, ctx);
    if(!ok){
      if(typeof err === 'string' && flow.specialErrors[err]){
        if(err === 'under_age') return [newState(), [{kind:'text', text:flow.specialErrors[err]}]];
        return [state, [{kind:'text', text:flow.specialErrors[err]}]];
      }
      return [state, [{kind:'text', text:flow.validators[step.validator].error}]];
    }
    state.answers[step.field] = val;
    return [advance(state, step), render(flow, state)];
  }

  return [state, render(flow, state)];
}

global.WA = {handle, render, newState, runValidator, luhnOk, parseDate,
             normaliseSaNumber, saIdBirthdate, summary, fmtDate, fmtPhone};

})(typeof window !== 'undefined' ? window : globalThis);
