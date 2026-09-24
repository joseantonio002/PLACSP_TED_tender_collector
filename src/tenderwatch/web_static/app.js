const state = { all: [], page: 1, pageSize: 8 };
const $ = (id) => document.getElementById(id);
const text = (value) => value == null ? '' : String(value);
const orderedCandidates = (fact) => [...(fact.candidates || [])].sort((a, b) => a.candidate_id.localeCompare(b.candidate_id));
const selected = (fact) => fact?.candidates?.find(candidate => candidate.candidate_id === fact.selected_candidate_id)?.value;
function facts(item, key) {
  const value = item.current_state?.[key];
  return (Array.isArray(value) ? value : value ? [value] : []).filter(fact => fact.fact_id).sort((a, b) => a.fact_id.localeCompare(b.fact_id));
}
function selectedValues(item, key) { return facts(item, key).map(selected).filter(value => value != null); }
function factState(fact) {
  if (selected(fact) != null) return 'Selected';
  if (fact.rule === 'reconcile.v1.unresolved_conflict') return 'In conflict';
  if (fact.rule === 'reconcile.v1.no_valid_value') return 'No valid value';
  return fact.candidates?.length ? 'Unresolved' : 'Not reported';
}
function names(party) { return party?.names?.map(name => name.text).filter(Boolean).join(' / ') || ''; }
function code(value) { return value?.normalized || value?.source?.labels?.map(x => x.text).join(' / ') || value?.source?.value || ''; }
function temporal(value) {
  if (!value) return '';
  if (value.at) return temporal(value.at);
  return value.local_date ? [value.local_date, value.local_time].filter(Boolean).join(' ') : value.utc_instant || value.raw || value.local_time || '';
}
function money(value, currency) {
  if (value == null || value === '' || !Number.isFinite(Number(value))) return text(value) || 'Not reported';
  if (!currency || !/^[A-Z]{3}$/.test(currency)) return `${value} (currency ${currency || 'not reported'})`;
  return new Intl.NumberFormat('en-GB', {style: 'currency', currency, maximumFractionDigits: 2}).format(Number(value));
}
function readableCode(value) {
  const labels = {resolved_unspecified: 'Resolved (outcome unspecified)', submission_open_reported: 'Open for submissions (reported)', award_reported: 'Awarded (reported)', awaiting_award: 'Awaiting award', prior_information: 'Prior information'};
  if (value?.normalized) return labels[value.normalized] || value.normalized.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
  return value?.source?.labels?.map(label => label.text).filter(Boolean).join(' / ') || 'Not interpretable — see evidence';
}
function valueLabel(value) {
  if (value == null) return 'Not reported';
  if (typeof value !== 'object') return String(value);
  if (value.purpose) return `${money(value.value, value.currency)} · ${value.tax_basis === 'included' ? 'incl. VAT' : value.tax_basis === 'excluded' ? 'excl. VAT' : 'VAT not reported'}`;
  if (value.text != null) return value.text;
  if (value.names) return names(value) || 'Buyer details in evidence';
  if (value.dimension) return readableCode(value.value);
  if (value.kind && ('at' in value || 'notes' in value)) {
    const role = {offers: 'Submission', document_access: 'Document access', participation_requests: 'Participation request'}[value.kind] || value.kind.replaceAll('_', ' ');
    const notes = Array.isArray(value.notes) ? value.notes.map(note => typeof note === 'string' ? note : note.text).filter(Boolean).join('; ') : value.notes;
    return `${role}: ${[temporal(value.at), notes].filter(Boolean).join(' · ') || 'Date not reported'}`;
  }
  if (value.normalized || value.source) return readableCode(value);
  if (value.locality || value.address || value.country_code) return [value.locality, value.address, value.country_code].filter(Boolean).join(' · ');
  return 'Reported value — see evidence';
}
function scopeLabel(scope) {
  if (!scope) return '';
  return [scope.kind, scope.observation_id, ...(scope.lot_keys || []), ...(scope.source_lot_identifiers || []).map(value => value.value)].filter(Boolean).join(' · ');
}
function factLabel(fact, technical = false) {
  const status = factState(fact);
  const value = selected(fact);
  const label = status === 'Selected' ? valueLabel(value) : status === 'No valid value' && !technical ? 'Not interpretable — see evidence' : `${status}${fact.candidates?.length ? ': ' + orderedCandidates(fact).map(candidate => valueLabel(candidate.value)).join(' / ') : ''}`;
  if (technical) return `${label}${fact.scope ? ' [' + scopeLabel(fact.scope) + ']' : ''}`;
  const scope = fact.scope?.kind;
  const qualifier = !scope || scope === 'procedure' ? '' : scope === 'lots' ? 'Lot-specific' : scope === 'record_subject' ? 'Source-record scope' : 'Scope unspecified';
  return qualifier ? `${qualifier}: ${label}` : label;
}
function fieldLabel(item, key, predicate = () => true) {
  const seen = new Set();
  return facts(item, key).filter(predicate).filter(fact => {
    const value = selected(fact);
    if (key !== 'financials' || value?.value == null) return true;
    const amount = String(value.value).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
    const identity = JSON.stringify([value.purpose, value.currency, amount, fact.scope]);
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  }).map(fact => factLabel(fact)).join('\n') || 'Not reported';
}
function hasPurpose(fact, purpose) { return fact.candidates?.some(candidate => candidate.value?.purpose === purpose); }
function uniqueSelected(item, key, predicate) {
  const matching = facts(item, key).filter(fact => fact.scope?.kind === 'procedure' && fact.candidates?.some(candidate => predicate(candidate.value)));
  return matching.length === 1 ? selected(matching[0]) : null;
}
function dateValue(value) { return value?.local_date || value?.utc_instant?.slice(0, 10) || ''; }
function projection(item) {
  const budgetTaxBasis = facts(item, 'financials').some(fact => fact.candidates?.some(candidate => candidate.value.purpose === 'tender_budget' && candidate.value.tax_basis === 'included')) ? 'included' : 'excluded';
  const isBudget = value => value.purpose === 'tender_budget' && value.tax_basis === budgetTaxBasis;
  const budgetValue = uniqueSelected(item, 'financials', value => isBudget(value) && value.currency === 'EUR');
  const deadlineValue = uniqueSelected(item, 'deadlines', value => value.kind === 'offers');
  const publicationDates = (item.current_state?.publications || []).map(x => dateValue(x.value?.publication_at)).filter(Boolean).sort();
  const title = fieldLabel(item, 'titles');
  const description = fieldLabel(item, 'descriptions');
  const buyer = fieldLabel(item, 'buyer');
  const budget = budgetValue?.value != null && budgetValue.value !== '' && Number.isFinite(Number(budgetValue.value)) ? Number(budgetValue.value) : null;
  return {item, title, description, buyer, search: `${title} ${description} ${buyer} ${JSON.stringify(selectedValues(item, 'identifiers'))}`.toLowerCase(),
    buyerFilter: selectedValues(item, 'buyer').map(names).join(' '), budget, budgetLabel: fieldLabel(item, 'financials', fact => fact.candidates?.some(candidate => isBudget(candidate.value))),
    deadline: dateValue(deadlineValue?.at) || null, deadlineLabel: fieldLabel(item, 'deadlines'), publication: publicationDates.at(-1) || null,
    statuses: selectedValues(item, 'statuses').map(value => code(value.value)), contract: selectedValues(item, 'contract_type').map(code).join(' '),
    cpv: selectedValues(item, 'classifications').map(value => value.code || value.raw_code || ''), conflictCount: item.conflicts?.length || 0,
    lots: item.current_state?.lots?.length || 0, sources: (item._source_systems || []).map(source => source.toLowerCase())};
}
function matchText(value, query) { return !query.trim() || value.toLowerCase().includes(query.trim().toLowerCase()); }
function range(value, from, to) { return (!from && !to) || (value != null && value !== '' && (!from || value >= from) && (!to || value <= to)); }
function numericRange(value, min, max) { return (min === '' && max === '') || (value != null && (min === '' || value >= Number(min)) && (max === '' || value <= Number(max))); }
function filtered() {
  const q = $('search').value.trim().toLowerCase();
  return state.all.map(projection).filter(x => (!q || x.search.includes(q)) && matchText(x.buyerFilter, $('buyer').value) && (!$('source').value || x.sources.includes($('source').value)) && matchText(x.statuses.join(' '), $('status').value) && matchText(x.contract, $('contract-type').value) && (!$('cpv').value || x.cpv.some(value => value.includes($('cpv').value))) && range(x.publication, $('publication-from').value, $('publication-to').value) && range(x.deadline, $('deadline-from').value, $('deadline-to').value) && numericRange(x.budget, $('min-budget').value, $('max-budget').value) && (!$('has-conflicts').checked || x.conflictCount > 0));
}
function compareRows(a, b, mode) {
  const key = mode === 'budget' ? 'budget' : mode === 'newest' ? 'publication' : 'deadline';
  const left = a[key], right = b[key];
  const tie = a.item.canonical_id.localeCompare(b.item.canonical_id);
  if (left == null || right == null) return left == null && right == null ? tie : left == null ? 1 : -1;
  const comparison = key === 'budget' ? left - right : left.localeCompare(right);
  return (mode === 'deadline' ? comparison : -comparison) || tie;
}
function dateLabel(value) { if (!value) return 'Not reported'; const d = new Date(value); return Number.isNaN(d.valueOf()) ? value : new Intl.DateTimeFormat('en-GB', {dateStyle: 'medium', timeZone: 'UTC'}).format(d); }
function animateOnScroll() { const elements = document.querySelectorAll('.scroll-reveal'); if (!('IntersectionObserver' in window)) { elements.forEach(element => element.classList.add('is-visible')); return; } const observer = new IntersectionObserver((entries, currentObserver) => { entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); currentObserver.unobserve(entry.target); } }); }, {threshold: 0.12}); elements.forEach(element => observer.observe(element)); }
function render() {
  const items = filtered().sort((a, b) => compareRows(a, b, $('sort').value));
  const pages = Math.max(1, Math.ceil(items.length / state.pageSize));
  state.page = Math.min(state.page, pages);
  $('result-count').textContent = `${items.length} tender${items.length === 1 ? '' : 's'} found`;
  $('empty').hidden = items.length !== 0;
  $('cards').innerHTML = items.slice((state.page - 1) * state.pageSize, state.page * state.pageSize).map(card).join('');
  $('pagination').innerHTML = pages > 1 ? pagination(pages) : '';
  animateOnScroll();
}
function sourceLabel(source) { return source === 'gencat' ? 'Generalitat' : source === 'placsp' ? 'PLACSP' : source; }
function card(x) { return `<a class="card scroll-reveal" href="/tender/${encodeURIComponent(x.item.canonical_id)}"><div class="card-top"><span>${escapeHtml(x.buyer)}</span><span>${x.lots ? `${x.lots} lots` : 'Procedure'}</span></div><h3>${escapeHtml(x.title)}</h3><p>${escapeHtml(x.description.slice(0, 145))}${x.description.length > 145 ? '…' : ''}</p><div class="facts"><div class="fact"><small>Budget</small><strong>${escapeHtml(x.budgetLabel)}</strong></div><div class="fact"><small>Deadlines</small><strong>${escapeHtml(x.deadlineLabel)}</strong></div><div class="fact"><small>Latest dated publication</small><strong>${escapeHtml(dateLabel(x.publication))}</strong></div></div><div class="card-footer">${x.sources.map(source => `<span class="pill">${escapeHtml(sourceLabel(source))}</span>`).join('')}${x.conflictCount ? `<span class="pill alert">${x.conflictCount} conflict${x.conflictCount === 1 ? '' : 's'} · view alternatives and evidence</span>` : ''}</div></a>`; }
function pagination(pages) {
  const visible = new Set([1, 2, 3, pages, state.page - 1, state.page, state.page + 1].filter(page => page >= 1 && page <= pages));
  const buttons = [];
  let previous = 0;
  [...visible].sort((a, b) => a - b).forEach(page => {
    if (page - previous > 1) buttons.push('<span class="pagination-gap">...</span>');
    buttons.push(`<button ${state.page === page ? 'class="active"' : ''} onclick="go(${page})">${page}</button>`);
    previous = page;
  });
  return `<button ${state.page === 1 ? 'disabled' : ''} onclick="go(${state.page - 1})">‹</button>${buttons.join('')}<button ${state.page === pages ? 'disabled' : ''} onclick="go(${state.page + 1})">›</button>`;
}
function go(page) { state.page = page; render(); window.scrollTo({top: document.querySelector('.results').offsetTop - 20, behavior: 'smooth'}); }
function escapeHtml(value) { return text(value).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'}[c])); }
function stat(label, value, modifier = '') { return `<div class="state-stat ${modifier}"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value == null || value === '' ? 'Not reported' : value)}</strong></div>`; }
function factDisclosure(label, fieldFacts) {
  if (!fieldFacts.length) return '';
  return `<details class="evidence-disclosure"><summary>${escapeHtml(label)} (${fieldFacts.length})</summary>${fieldFacts.map(fact => `<div class="evidence-fact"><strong>${escapeHtml(factLabel(fact, true))}</strong><span>${escapeHtml(fact.rule)} · ${escapeHtml(fact.fact_id)}</span>${orderedCandidates(fact).map(candidate => `<div class="candidate"><p>${escapeHtml(valueLabel(candidate.value))}${candidate.candidate_id === fact.selected_candidate_id ? ' · Selected' : ' · Not selected'}</p><small>${(candidate.evidence || []).map(evidence => `${escapeHtml(evidence.observation_id)} · ${escapeHtml(evidence.normalized_path)}`).sort().join('<br>')}</small><details><summary>Full candidate value and scope</summary><pre>${escapeHtml(JSON.stringify({value: candidate.value, scope: fact.scope}, null, 2))}</pre></details></div>`).join('')}</div>`).join('')}</details>`;
}
function occurrenceSection(label, occurrences, renderer, description = '') { if (!occurrences?.length) return ''; return `<section class="detail-section scroll-reveal"><div class="section-heading"><p class="eyebrow">${escapeHtml(label)}</p><span>${occurrences.length}</span></div>${description ? `<p class="section-description">${escapeHtml(description)}</p>` : ''}<div class="occurrence-list">${occurrences.map(occurrence => `<article class="occurrence"><div>${renderer(occurrence.value)}</div><small>Evidence: ${escapeHtml(occurrence.observation_id)} · ${escapeHtml(occurrence.normalized_path)}</small></article>`).join('')}</div></section>`; }
function detailHtml(item) {
  if (!item) return '<main class="detail-page"><h1>Canonical not found</h1><a class="back-link" href="/">Back to explorer</a></main>';
  const s = item.current_state || {};
  const p = projection(item);
  const factKeys = Object.keys(s).filter(key => facts(item, key).some(fact => fact.fact_id)).sort();
  return `<header class="site-header"><a class="brand" href="/">TENDER<span>WATCH</span></a><div class="header-note">Canonical evidence view</div></header>
<main class="detail-page"><a class="back-link" href="/">Back to explorer</a><p class="eyebrow">CURRENT PROCEDURE STATE</p><h1>${escapeHtml(p.title)}</h1><p class="detail-id">${escapeHtml(item.canonical_id)}</p>
<div class="detail-summary">${stat('Buyer', p.buyer)}${stat('Current status', fieldLabel(item, 'statuses'))}${stat('Evidence observations', item.normalized_observation_ids?.length || 0)}${stat('Conflicts', p.conflictCount, p.conflictCount ? 'alert-stat' : '')}</div>
<section class="current-panel scroll-reveal"><p class="eyebrow">AT A GLANCE</p><div class="state-grid">${stat('Budget', p.budgetLabel)}${stat('Estimated value', fieldLabel(item, 'financials', fact => hasPurpose(fact, 'estimated_value')))}${stat('Deadlines', p.deadlineLabel)}${stat('Contract type', fieldLabel(item, 'contract_type'))}${stat('Procurement method', fieldLabel(item, 'procurement_method'))}${stat('Latest dated publication', dateLabel(p.publication))}${stat('Lots', p.lots)}${stat('Location', fieldLabel(item, 'execution_locations'))}</div></section>
<section class="detail-section prose-section scroll-reveal"><p class="eyebrow">DESCRIPTION</p><p class="description">${escapeHtml(p.description)}</p></section>
${item.conflicts?.length ? `<section class="conflict-box scroll-reveal"><p class="eyebrow">REVIEW NEEDED</p><h2>Some current values remain unresolved</h2><p>Alternatives are not selected values. Expand reconciliation details below for their evidence.</p>${item.conflicts.map(conflict => `<div class="conflict-item"><strong>${escapeHtml(conflict.field.replaceAll('_', ' '))}</strong><span>Multiple supported values; no value selected.</span></div>`).join('')}</section>` : ''}
${occurrenceSection('Lots', s.lots, lot => `<h3>${escapeHtml(lot.number || lot.key)}</h3><p>${escapeHtml(lot.titles?.map(value => value.text).join(' / ') || 'Lot details not reported')}</p>`)}
${occurrenceSection('Awards', s.awards, award => `<h3>${escapeHtml(award.suppliers?.map(supplier => names(supplier.party)).filter(Boolean).join(' · ') || 'Award information')}</h3><p>${escapeHtml(award.amounts?.map(valueLabel).join(' · ') || temporal(award.decision_at) || 'Decision date not reported')}</p>`)}
${occurrenceSection('Publications', s.publications, publication => `<h3>${escapeHtml(code(publication.type) || 'Publication')}</h3><p>${escapeHtml(temporal(publication.publication_at) || 'Date not reported')}</p>`, 'Official notices and publication events associated with this procedure, including tender, award, formalization, correction, and modification notices.')}
${occurrenceSection('Documents', s.documents, document => `<h3>${escapeHtml(document.titles?.map(value => value.text).join(' / ') || 'Source document')}</h3><p>${escapeHtml(code(document.role) || 'Document reference')}</p>`, 'Documents and attachments referenced by the source, such as notices, specifications, award records, and supporting files.')}
<section class="detail-section reconciliation-section scroll-reveal"><p class="eyebrow">RECONCILIATION DETAILS</p>${factKeys.map(key => factDisclosure(key.replaceAll('_', ' '), facts(item, key))).join('')}<details class="evidence-disclosure"><summary>Source evidence and resolution provenance</summary><pre class="evidence">${escapeHtml(JSON.stringify({normalized_observation_ids: item.normalized_observation_ids, resolution_provenance: item.resolution_provenance}, null, 2))}</pre></details></section></main>`;
}
function renderDetail(item) { document.body.innerHTML = detailHtml(item); animateOnScroll(); }
async function init() {
  const response = await fetch('/api/canonicals');
  state.all = await response.json();
  if (location.pathname.startsWith('/tender/')) { renderDetail(state.all.find(item => item.canonical_id === decodeURIComponent(location.pathname.split('/').pop()))); return; }
  document.querySelectorAll('input,select').forEach(control => {
    control.addEventListener('input', () => { state.page = 1; render(); });
    control.addEventListener('change', () => { state.page = 1; render(); });
  });
  $('clear-filters').onclick = () => { document.querySelectorAll('.filters input,.filters select').forEach(control => control.type === 'checkbox' ? control.checked = false : control.value = ''); state.page = 1; render(); };
  $('empty-clear').onclick = $('clear-filters').onclick;
  render();
}
if (typeof document !== 'undefined') init().catch(() => { $('result-count').textContent = 'Catalog unavailable'; $('cards').innerHTML = '<div class="empty"><h3>Unable to load canonical data</h3><p>Start the TenderWatch explorer from the project root and try again.</p></div>'; });
if (typeof module !== 'undefined') module.exports = {factLabel, fieldLabel, projection, numericRange, range, compareRows, detailHtml, card};
