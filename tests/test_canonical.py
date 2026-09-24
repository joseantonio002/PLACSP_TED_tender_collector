from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from importlib import import_module
from itertools import permutations

import pytest

import tenderwatch.normalization as normalization
from tenderwatch.inspection import serialize
from tenderwatch.normalization.models import Identifier, Money, Scope, Scoped
from normalization.support import Cases, P_BUDGET


@pytest.fixture
def api():
    return import_module('tenderwatch.canonical')


@pytest.fixture
def cases(tmp_path):
    return Cases(tmp_path)


def one(api, observations):
    result = api.canonicalize(observations)
    assert not result.unresolved_observations
    canonical, = result.canonical_observations
    return canonical


def procedure_net(canonical, currency=None):
    return next(fact for fact in canonical.current_state.financials
                if fact.scope.kind == 'procedure' and fact.candidates[0].value.purpose == 'tender_budget'
                and fact.candidates[0].value.tax_basis == 'excluded' and fact.candidates[0].value.currency == currency)


def test_explicit_cross_source_procedure_identity(api, cases):
    observations = [cases.get(name).one(normalization) for name in ('C01-P000', 'C01-G', 'J01')]
    canonical = one(api, observations)
    assert canonical.normalized_observation_ids == tuple(sorted(o.observation_id for o in observations))
    assert canonical.canonical_id.startswith('canonical:v1:')
    decisions = canonical.resolution_provenance
    assert any(d.rule == 'er.v1.shared_procedure_identifier' and d.identifier.scheme == 'pscp_uuid' for d in decisions)
    assert {oid for d in decisions for oid in d.observation_ids} == set(canonical.normalized_observation_ids)
    assert not hasattr(canonical, 'normalized_observations')
    with pytest.raises(FrozenInstanceError):
        canonical.canonical_id = 'changed'


def test_same_atom_over_time_and_explicit_alias_bridge(api, cases):
    first = cases.get('C01-P000').one(normalization)
    later = cases.get('C01-P002').one(normalization)
    without_uuid = replace(later, procedure_identifiers=tuple(i for i in later.procedure_identifiers if i.scheme == 'atom_id'))
    table = cases.get('C01-G').one(normalization)
    canonical = one(api, [first, without_uuid, table])
    assert len(canonical.normalized_observation_ids) == 3
    assert {d.identifier.scheme for d in canonical.resolution_provenance} == {'pscp_uuid', 'atom_id'}
    lifecycle = next(f for f in canonical.current_state.statuses if f.candidates[0].value.dimension == 'procurement_lifecycle')
    assert lifecycle.selected_candidate_id is None
    assert {c.value.value.normalized for c in lifecycle.candidates} == {'submission_open_reported', 'awaiting_award'}


def test_lot_rows_share_procedure_but_not_lot_occurrences(api, cases):
    base = cases.get('C05-G1')
    synthetic_lot7 = cases.mutate_json(base, '/numero_lot', '7')
    observations = [base.one(normalization), synthetic_lot7.one(normalization)]
    canonical = one(api, observations)
    assert {item.value.number for item in canonical.current_state.lots} == {'1', '7'}
    assert {item.observation_id for item in canonical.current_state.lots} == set(canonical.normalized_observation_ids)
    net = procedure_net(canonical)
    assert len(net.candidates) == 1 and net.value.value == Decimal('41129079.80')
    assert {e.observation_id for e in net.candidates[0].evidence} == set(canonical.normalized_observation_ids)
    lot_facts = [fact for fact in canonical.current_state.financials if fact.scope.kind == 'lots']
    assert len({f.scope.observation_id for f in lot_facts}) == 2


def test_duplicate_display_numbers_do_not_merge_lots_or_awards(api, cases):
    observations = [cases.get(name).one(normalization) for name in ('C15-G0', 'C15-G2')]
    canonical = one(api, observations)
    assert [item.value.number for item in canonical.current_state.lots] == ['3', '3']
    assert len(canonical.current_state.awards) == 2
    assert len({(item.observation_id, item.value.key) for item in canonical.current_state.lots}) == 2


def test_same_number_buyer_title_money_is_not_identity(api, cases):
    original = cases.get('C01-G').one(normalization)
    other_id = replace(original.procedure_identifiers[0], value='00000000-0000-4000-8000-000000000001')
    other = replace(original, observation_id='other', raw_source_record_id='other-raw', procedure_identifiers=(other_id,))
    result = api.canonicalize([original, other])
    assert len(result.canonical_observations) == 2
    assert not result.unresolved_observations
    assert {len(c.normalized_observation_ids) for c in result.canonical_observations} == {1}


def test_batch_planning_and_action_only_identity_stay_unresolved(api, cases):
    observations = [cases.get('C14-G0').one(normalization), *cases.get('J14').normalize(normalization),
                    cases.get('J16').one(normalization), cases.get('C19-E0').one(normalization)]
    result = api.canonicalize(observations)
    assert not result.canonical_observations
    assert {u.observation_id for u in result.unresolved_observations} == {o.observation_id for o in observations}
    assert {u.reason for u in result.unresolved_observations} == {'not_a_procedure_subject', 'no_strong_procedure_identifier'}


@pytest.mark.parametrize('scheme,namespace,role,value', [
    ('pscp_publication', 'gencat:pscp', 'publication', '300885987'),
    ('pscp_uuid', 'unreviewed', 'procedure', '4b131001-63ad-4eac-a80a-ab91c3a9f366'),
    ('source_unclassified', 'gencat:pscp', 'procedure', '4b131001-63ad-4eac-a80a-ab91c3a9f366'),
    ('pscp_uuid', 'gencat:pscp', 'procedure', 'not-a-uuid'),
    ('lot_number', 'gencat:pscp', 'lot', '1'),
])
def test_wrong_identifier_roles_and_namespaces_are_not_keys(api, cases, scheme, namespace, role, value):
    observation = cases.get('C01-G').one(normalization)
    observation = replace(observation, procedure_identifiers=(Identifier(scheme, namespace, value, role),))
    result = api.canonicalize([observation])
    assert not result.canonical_observations
    assert result.unresolved_observations[0].reason == 'no_strong_procedure_identifier'


def test_conflicting_uuid_bridge_is_quarantined_independent_of_order(api, cases):
    placsp = cases.get('C01-P000').one(normalization)
    table = cases.get('C01-G').one(normalization)
    ids = tuple(replace(i, value='00000000-0000-4000-8000-000000000001') if i.scheme == 'pscp_uuid' else i for i in placsp.procedure_identifiers)
    contradictory = replace(placsp, observation_id='contradictory', procedure_identifiers=ids)
    expected = None
    for order in permutations([placsp, table, contradictory]):
        result = api.canonicalize(order)
        assert not result.canonical_observations
        assert len(result.unresolved_observations) == 3
        assert {u.reason for u in result.unresolved_observations} == {'contradictory_procedure_identifiers'}
        encoded = serialize(result)
        assert expected is None or encoded == expected
        expected = encoded


def test_multiple_body_uuid_assertions_remain_unresolved(api, cases):
    case = cases.mutate_json(cases.get('J01'), '/publicacio/expedientId', '00000000-0000-4000-8000-000000000001')
    result = api.canonicalize([case.one(normalization)])
    assert not result.canonical_observations
    assert result.unresolved_observations[0].reason == 'contradictory_procedure_identifiers'


def test_matching_money_consolidates_exact_decimals_and_evidence(api, cases):
    case = cases.get('C01-P000')
    second = cases.mutate_xml(case, P_BUDGET, lambda entry, node: setattr(node, 'text', '949509.1000'))
    observations = [case.one(normalization), second.one(normalization)]
    canonical = one(api, observations)
    fact = procedure_net(canonical, 'EUR')
    assert len(fact.candidates) == 1
    assert fact.value.value == Decimal('949509.1')
    assert fact.rule == 'reconcile.v1.agreed_value'
    assert len(fact.candidates[0].evidence) == 2
    assert all(e.normalized_path.startswith('/financials/') for e in fact.candidates[0].evidence)


def test_conflicts_survive_newer_technical_timestamps_and_source_order(api, cases):
    case = cases.get('C01-G')
    changed = cases.mutate_json(case, '/pressupost_licitacio_sense_1', '1')
    changed = cases.mutate_json(changed, '/:updated_at', '2099-01-01T00:00:00Z')
    observations = [case.one(normalization), changed.one(normalization)]
    canonical = one(api, observations)
    fact = procedure_net(canonical)
    assert fact.selected_candidate_id is None and fact.value is None
    assert {c.value.value for c in fact.candidates} == {Decimal('949509.1'), Decimal('1')}
    conflict, = [c for c in canonical.conflicts if c.fact_id == fact.fact_id]
    assert conflict.reason == 'competing_values_without_safe_ordering'
    assert set(conflict.observation_ids) == set(canonical.normalized_observation_ids)
    assert serialize(one(api, reversed(observations))) == serialize(canonical)


def test_missing_and_invalid_money_do_not_erase_valid_evidence(api, cases):
    base = cases.get('C01-G')
    missing = cases.mutate_json(base, '/pressupost_licitacio_sense_1')
    invalid = cases.mutate_json(base, '/pressupost_licitacio_sense_1', 'bad')
    canonical = one(api, [base.one(normalization), missing.one(normalization), invalid.one(normalization)])
    fact = procedure_net(canonical)
    assert fact.value.value == Decimal('949509.1')
    assert len(fact.candidates) == 2
    assert fact.rule == 'reconcile.v1.sole_valid_value'
    assert not any(c.fact_id == fact.fact_id for c in canonical.conflicts)
    assert len(canonical.normalized_observation_ids) == 3


def test_complementary_financial_roles_and_currencies_remain_separate(api, cases):
    original = cases.get('C01-G').one(normalization)
    extra = replace(original, observation_id='extra', financials=(
        Scoped('/synthetic', Scope('procedure'), Money('tender_budget', Decimal('7'), '7', 'valid', 'EUR', 'excluded')),
        Scoped('/synthetic2', Scope('procedure'), Money('estimated_value', Decimal('9'), '9', 'valid', 'EUR', 'excluded')),
    ))
    canonical = one(api, [original, extra])
    assert procedure_net(canonical).value.value == Decimal('949509.1')
    assert procedure_net(canonical, 'EUR').value.value == Decimal('7')
    assert any(f.scope.kind == 'record_subject' for f in canonical.current_state.financials)
    assert not any(c.field == 'financials' for c in canonical.conflicts)


def test_historical_awards_negative_outcomes_and_actions_survive(api, cases):
    table = cases.get('C09-G').one(normalization)
    placsp = cases.get('C09-P000').one(normalization)
    synthetic_explicit_link = replace(placsp, observation_id='synthetic-linked-negative',
                                      procedure_identifiers=placsp.procedure_identifiers + table.procedure_identifiers)
    negative = one(api, [table, synthetic_explicit_link])
    assert negative.current_state.awards
    assert any(o.value.result.normalized == 'renounced' for o in negative.current_state.outcomes)
    rich = cases.get('J19').one(normalization)
    canonical = one(api, [rich])
    assert len(canonical.current_state.execution_actions) == 2
    assert canonical.current_state.awards
    assert procedure_net(canonical).value.value == Decimal('3981218.08')
    assert not hasattr(canonical.current_state, 'contracts')


def test_reduced_fixtures_do_not_imply_unreported_identity_links(api, cases):
    result = api.canonicalize([cases.get(name).one(normalization) for name in ('C05-G1', 'C05-G7', 'C09-G', 'C09-P000')])
    assert len(result.canonical_observations) == 3
    assert len(result.unresolved_observations) == 1
    assert result.unresolved_observations[0].reason == 'no_strong_procedure_identifier'


def test_deterministic_ids_serialization_and_no_duplicate_evidence(api, cases):
    observations = [cases.get(name).one(normalization) for name in ('C01-P000', 'C01-G', 'J01')]
    expected = serialize(one(api, observations))
    assert serialize(one(api, observations + observations)) == expected
    for order in permutations(observations):
        assert serialize(one(api, order)) == expected
    assert one(api, observations[:1]).canonical_id == one(api, observations).canonical_id


def test_duplicate_observation_id_with_different_content_is_a_defect(api, cases):
    observation = cases.get('C01-G').one(normalization)
    with pytest.raises(ValueError, match='observation ID'):
        api.canonicalize([observation, replace(observation, titles=())])


def test_all_current_state_evidence_points_to_retained_normalized_observations(api, cases):
    from dataclasses import fields, is_dataclass
    observations = [cases.get(name).one(normalization) for name in ('C01-P000', 'C01-G', 'J01')]
    canonical = one(api, observations)
    known = {o.observation_id for o in observations}
    def visit(value):
        if is_dataclass(value):
            if hasattr(value, 'observation_id'):
                assert value.observation_id is None or value.observation_id in known
            for field in fields(value):
                visit(getattr(value, field.name))
        elif isinstance(value, tuple):
            for item in value:
                visit(item)
    visit(canonical)
