const { test } = require('node:test');
const assert = require('node:assert/strict');
const ui = require('../src/tenderwatch/web_static/app.js');

const amount = (value, extra = {}) => ({value: String(value), purpose: 'tender_budget', currency: 'EUR', tax_basis: 'included', ...extra});
const fact = (values, selected = null, extra = {}) => ({fact_id: 'f', scope: {kind: 'procedure'}, rule: selected === null ? 'reconcile.v1.unresolved_conflict' : 'reconcile.v1.agreed_value', selected_candidate_id: selected, candidates: values.map((value, i) => ({candidate_id: String(i), value, evidence: [{observation_id: `o${i}`, normalized_path: '/financials/0'}]})), ...extra});
const item = (current_state, id = 'a') => ({canonical_id: id, current_state, conflicts: [], normalized_observation_ids: []});

test('Paradores summary contains readable values, not internal metadata', () => {
  const title = 'Suministro e implantación de licencias perpetuas';
  const record = item({
    titles: [fact([{text: title, source_role: 'project_name', language: 'es'}], '0')],
    buyer: fact([{names: [{text: 'Paradores de Turismo de España, S.M.E., S.A.'}]}], '0'),
    statuses: [fact([{dimension: 'procurement_lifecycle', value: {normalized: 'resolved_unspecified'}}], '0')],
    financials: [fact([amount('79786.00', {tax_basis: 'excluded'})], '0'), fact([amount('96541.06', {tax_basis: 'included'})], '0', {fact_id: 'gross'}), fact([amount('167690.00', {purpose: 'estimated_value'})], '0', {fact_id: 'estimated'})],
    deadlines: [fact([{kind: 'offers', at: {local_date: '2018-07-11', local_time: '14:00:00'}, notes: []}], '0')],
    contract_type: fact([{normalized: 'services'}], '0'),
    procurement_method: fact([{normalized: null, source: {value: '3'}}], null, {rule: 'reconcile.v1.no_valid_value'}),
    execution_locations: [fact([{locality: 'Madrid'}], '0')],
  });
  const html = ui.detailHtml(record);
  const summary = html.split('<section class="detail-section reconciliation-section')[0];
  assert.equal(ui.projection(record).title, title);
  assert.doesNotMatch(summary, /project_name|\[procedure\]|procurement lifecycle|resolved_unspecified|tender budget|estimated_value|No valid value: 3|\{&quot;/);
  assert.match(summary, /Resolved \(outcome unspecified\)/);
  assert.doesNotMatch(summary, /€79,786\.00/);
  assert.match(summary, /€96,541\.06/);
  assert.doesNotMatch(summary, /VAT rate|con IVA|sin IVA/);
  assert.match(summary, /Submission: 2018-07-11 14:00:00/);
  assert.match(summary, /Services/);
  assert.match(summary, /Not interpretable — see evidence/);
  assert.match(html, /project_name/);
  assert.match(html, /\[procedure\]/);
});

test('money labels show tax basis without rates while evidence and conflicts retain metadata', () => {
  const f = fact([amount(196703.89, {vat_rate: '21', tax_basis: 'included', multiple_vat_rates: true}), amount(214732.89, {vat_rate: '21', tax_basis: 'included'})]);
  const record = item({financials: [f]});
  assert.doesNotMatch(ui.projection(record).budgetLabel, /VAT rate|multiple VAT rates|included/);
  assert.match(ui.projection(record).budgetLabel, /196,703\.89 · incl. VAT/);
  assert.match(ui.card(ui.projection(record)), /incl. VAT/);
  assert.match(ui.detailHtml(record), /incl. VAT/);
  assert.match(ui.projection(record).budgetLabel, /In conflict.*196,703\.89.*214,732\.89/);
  assert.doesNotMatch(ui.card(ui.projection(record)), /VAT rate|con IVA|sin IVA/);
  assert.match(ui.detailHtml(record), /vat_rate/);
  assert.match(ui.detailHtml(record), /multiple_vat_rates/);
  assert.equal(ui.projection(record).budget, null);
});

test('conflicting budgets show alternatives and never provide a filter value', () => {
  const f = fact([amount(5), amount(6)]);
  const record = item({financials: [f]});
  const label = ui.factLabel(f);
  assert.match(label, /In conflict/);
  assert.match(label, /5\.00/);
  assert.match(label, /6\.00/);
  assert.equal(ui.projection(record).budget, null);
  assert.match(ui.card(ui.projection(record)), /In conflict.*5\.00.*6\.00/);
  assert.equal(ui.numericRange(null, '', ''), true);
  assert.equal(ui.numericRange(null, '0', '10'), false);
  assert.match(ui.detailHtml(record), /o0/);
  assert.match(ui.detailHtml(record), /\/financials\/0/);
  const reversed = item({financials: [{...f, candidates: [...f.candidates].reverse()}]});
  assert.equal(ui.detailHtml(record), ui.detailHtml(reversed));
});

test('selected candidate wins over invalid alternatives, including zero', () => {
  const f = fact([amount(0), amount('bad', {value_state: 'invalid'})], '0');
  assert.equal(ui.projection(item({financials: [f]})).budget, 0);
  assert.doesNotMatch(ui.factLabel(f), /bad|In conflict/);
  assert.equal(ui.numericRange(0, '0', '0'), true);
  assert.equal(ui.numericRange(1, '', '0'), false);
});

test('missing, invalid and conflicting facts remain distinct', () => {
  assert.equal(ui.fieldLabel(item({}), 'buyer'), 'Not reported');
  assert.match(ui.factLabel(fact([amount('bad')], null, {rule: 'reconcile.v1.no_valid_value'})), /Not interpretable/);
  for (const key of ['titles', 'buyer', 'contract_type', 'procurement_method', 'statuses', 'deadlines']) {
    const f = fact([{text: 'A', normalized: 'A'}, {text: 'B', normalized: 'B'}]);
    const record = item({[key]: ['buyer', 'contract_type', 'procurement_method'].includes(key) ? f : [f]});
    assert.match(ui.fieldLabel(record, key), /In conflict/);
    assert.match(ui.detailHtml(record), /In conflict/);
  }
});

test('equal selected financial amounts are shown once without merging evidence', () => {
  const net = fact([amount('684090.48', {tax_basis: 'excluded'})], '0', {fact_id: 'net'});
  const gross = fact([amount('684090.4800', {tax_basis: 'included'})], '0', {fact_id: 'gross'});
  const record = item({financials: [net, gross]});
  assert.equal(ui.projection(record).budgetLabel, '€684,090.48 · incl. VAT');
  assert.equal(ui.projection(record).budget, 684090.48);
  assert.equal((ui.card(ui.projection(record)).match(/€684,090\.48/g) || []).length, 1);
  const detail = ui.detailHtml(record);
  assert.equal((detail.split('<section class="detail-section reconciliation-section')[0].match(/€684,090\.48/g) || []).length, 1);
  assert.match(detail, /included/);
  assert.match(detail, /excluded/);
  assert.equal(record.current_state.financials.length, 2);
  const conflicting = fact([amount('684090.48'), amount('700000')], null, {fact_id: 'conflict'});
  assert.match(ui.projection(item({financials: [net, gross, conflicting]})).budgetLabel, /In conflict.*684,090\.48.*700,000\.00/);
  const usd = fact([amount('684090.48', {currency: 'USD'})], '0', {fact_id: 'usd'});
  const lot = fact([amount('684090.48')], '0', {fact_id: 'lot', scope: {kind: 'lots', observation_id: 'o', lot_keys: ['l']}});
  assert.equal(ui.projection(item({financials: [net, gross, usd, lot]})).budgetLabel.split('\n').length, 3);
  assert.equal(ui.projection(item({financials: [gross, net]})).budgetLabel, ui.projection(record).budgetLabel);
});

test('budgets prefer gross and fall back to net only when gross is absent', () => {
  const net = fact([amount('1537990.48', {tax_basis: 'excluded'})], '0');
  const gross = fact([amount('1707768.49')], '0', {fact_id: 'gross'});
  const record = item({financials: [net, gross]});
  assert.equal(ui.projection(record).budgetLabel, '€1,707,768.49 · incl. VAT');
  assert.equal(ui.projection(record).budget, 1707768.49);
  assert.equal(ui.projection(item({financials: [net]})).budgetLabel, '€1,537,990.48 · excl. VAT');
  assert.equal(ui.projection(item({financials: [net]})).budget, 1537990.48);
  const conflict = fact([amount(10), amount(20)], null, {fact_id: 'gross-conflict'});
  assert.match(ui.projection(item({financials: [net, conflict]})).budgetLabel, /In conflict/);
  assert.equal(ui.projection(item({financials: [net, conflict]})).budget, null);
  const unknown = fact([amount(9, {tax_basis: 'unspecified'})], '0');
  assert.equal(ui.projection(item({financials: [unknown]})).budgetLabel, 'Not reported');
  assert.doesNotMatch(ui.card(ui.projection(record)), /1,537,990/);
  assert.doesNotMatch(ui.detailHtml(record).split('<section class="detail-section reconciliation-section')[0], /1,537,990/);
  assert.match(ui.detailHtml(record), /1537990.48/);
});

test('financial concepts, currencies and scopes stay separate', () => {
  const fs = [fact([amount(5, {tax_basis: 'excluded'})], '0'), fact([amount(6, {tax_basis: 'included'})], '0', {fact_id: 'gross'}), fact([amount(7, {purpose: 'estimated_value'})], '0', {fact_id: 'estimated'}), fact([amount(8, {currency: 'USD'})], '0', {fact_id: 'usd'}), fact([amount(9)], '0', {fact_id: 'lot', scope: {kind: 'lots', observation_id: 'o1', lot_keys: ['l1']}})];
  const record = item({financials: fs});
  assert.equal(ui.projection(record).budget, 6);
  const html = ui.detailHtml(record);
  for (const qualifier of ['tax_basis', 'excluded', 'included', 'Estimated value', 'USD', 'lots', 'l1']) assert.ok(html.includes(qualifier));
  assert.doesNotMatch(html, /In conflict/);
  assert.equal(ui.projection(item({financials: [fs[2]]})).budget, null);
  assert.equal(ui.projection(item({financials: [fs[1], {...fs[1], fact_id: 'other', candidates: [{candidate_id: '0', value: amount(10, {vat_rate: '21'})}]}]})).budget, null);
});

test('only a single selected procedure offer deadline is comparable', () => {
  const d = date => ({kind: 'offers', at: {local_date: date}});
  assert.equal(ui.projection(item({deadlines: [fact([d('2026-01-01'), d('2026-02-01')])]})).deadline, null);
  assert.equal(ui.projection(item({deadlines: [fact([d('2026-01-01')], '0')]})).deadline, '2026-01-01');
  assert.equal(ui.projection(item({deadlines: [fact([{kind: 'document_access', at: {local_date: '2026-01-01'}}], '0')]})).deadline, null);
});

test('display titles omit technical scope but retain conflicts and evidence scope', () => {
  for (const selected of ['0', null]) {
    const record = item({titles: [fact([{text: 'Cleaning'}, {text: 'Cleaning services'}], selected)], financials: [fact([amount(5)], '0')]});
    const row = ui.projection(record);
    assert.doesNotMatch(row.title, /\[procedure\]/);
    assert.match(ui.card(row), /<h3>[^<]*Cleaning[^<]*<\/h3>/);
    assert.doesNotMatch(ui.card(row).match(/<h3>(.*?)<\/h3>/)[1], /\[procedure\]/);
    assert.doesNotMatch(ui.detailHtml(record).match(/<h1>(.*?)<\/h1>/)[1], /\[procedure\]/);
    assert.doesNotMatch(row.budgetLabel, /\[procedure\]/);
    assert.match(ui.detailHtml(record), /\[procedure\]/);
    if (selected === null) assert.match(row.title, /In conflict.*Cleaning.*Cleaning services/);
  }
});

test('multiple legitimate facts are displayed without inventing conflicts', () => {
  const record = item({titles: [fact([{text: 'Català', language: 'ca'}], '0', {fact_id: 'ca'}), fact([{text: 'Castellano', language: 'es'}], '0', {fact_id: 'es'})]});
  const label = ui.fieldLabel(record, 'titles');
  assert.match(label, /Català/);
  assert.match(label, /Castellano/);
  assert.doesNotMatch(label, /conflict/);
});

test('sorting puts unavailable values last with stable canonical ID ties', () => {
  for (const mode of ['budget', 'deadline', 'newest']) {
    const rows = [{item: {canonical_id: 'z'}, budget: null, deadline: null, publication: null}, {item: {canonical_id: 'b'}, budget: 0, deadline: '2026-01-01', publication: '2026-01-01'}, {item: {canonical_id: 'a'}, budget: 0, deadline: '2026-01-01', publication: '2026-01-01'}];
    assert.deepEqual(rows.sort((a, b) => ui.compareRows(a, b, mode)).map(x => x.item.canonical_id), ['a', 'b', 'z']);
  }
});

test('candidate text and evidence are HTML escaped', () => {
  const record = item({titles: [fact([{text: '<script>bad</script>'}, {text: 'other'}])]});
  assert.doesNotMatch(ui.detailHtml(record), /<script>bad/);
  assert.match(ui.detailHtml(record), /&lt;script&gt;/);
});

test('filters never consume conflicting status, buyer, type or deadline alternatives', () => {
  const record = item({
    statuses: [fact([{dimension: 'lifecycle', value: {normalized: 'open'}}, {dimension: 'lifecycle', value: {normalized: 'closed'}}])],
    buyer: fact([{names: [{text: 'Buyer A'}]}, {names: [{text: 'Buyer B'}]}]),
    contract_type: fact([{normalized: 'services'}, {normalized: 'works'}]),
    deadlines: [fact([{kind: 'offers', at: {local_date: '2026-01-01'}}, {kind: 'offers', at: {local_date: '2026-02-01'}}])],
  });
  const row = ui.projection(record);
  assert.deepEqual(row.statuses, []);
  assert.equal(row.buyerFilter, '');
  assert.equal(row.contract, '');
  assert.equal(ui.range(row.deadline, '', ''), true);
  assert.equal(ui.range(row.deadline, '2026-01-01', '2026-12-31'), false);
});

test('occurrences remain renderable and are not mistaken for reconciled facts', () => {
  const occurrence = value => ({observation_id: 'o', normalized_path: '/lots/0', value});
  const record = item({lots: [occurrence({number: '1'}), occurrence({number: '2'})], publications: [occurrence({publication_at: {local_date: '2026-01-01'}}), occurrence({publication_at: {local_date: '2026-02-01'}})]});
  assert.match(ui.detailHtml(record), /Lots/);
  assert.equal(ui.projection(record).publication, '2026-02-01');
});
