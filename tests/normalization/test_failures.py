from dataclasses import asdict, replace
from decimal import Decimal
from functools import partial
from types import ModuleType

import pytest

from tenderwatch.raw import to_raw
from tenderwatch.sources.artifacts import load_record
from tenderwatch.sources.errors import ArtifactReadError, IntegrityError, LocatorError, SourceFormatError

from .support import BATCH, CFS, Cases


def test_exception_hierarchy_keeps_defects_separate(api: ModuleType) -> None:
    assert issubclass(api.InvalidNormalizationInput, api.NormalizationError)
    assert issubclass(api.UnsupportedNormalizationInput, api.NormalizationError)
    assert issubclass(api.NormalizationInvariantError, RuntimeError)
    assert not issubclass(api.NormalizationInvariantError, api.NormalizationError)


@pytest.mark.parametrize('name', ['C01-P000', 'P-native', 'C01-G', 'C05-G1', 'C14-G0', 'C19-E0'])
def test_F03_unresolvable_raw_occurrence(api: ModuleType, cases: Cases, name: str) -> None:
    case = cases.get(name)
    locator = replace(case.raw.content.locator, ordinal=999)
    raw = to_raw(replace(case.raw, content=replace(case.raw.content, locator=locator)))
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        api.normalize(raw, resolve=partial(load_record, case.root))
    assert caught.value.reason == 'unresolvable_occurrence'
    assert caught.value.raw_source_record_id == raw.raw_record_id
    assert isinstance(caught.value.__cause__, LocatorError)


def test_F04_checksum_failure_preserves_domain_cause(api: ModuleType, cases: Cases) -> None:
    case = cases.get('C01-G')
    content = replace(case.raw.content, document_sha256='0' * 64)
    raw = to_raw(replace(case.raw, content=content))
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        api.normalize(raw, resolve=partial(load_record, case.root))
    assert caught.value.reason == 'raw_integrity_mismatch'
    assert isinstance(caught.value.__cause__, IntegrityError)


def test_F05_resolver_decode_failure_is_contextual(api: ModuleType, cases: Cases) -> None:
    case = cases.get('J01')
    error = SourceFormatError('controlled decoder-domain failure')
    def resolve(content):
        raise error
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        api.normalize(case.raw, resolve=resolve)
    assert caught.value.reason == 'unparseable_payload'
    assert caught.value.raw_source_record_id == case.raw.raw_record_id
    assert caught.value.__cause__ is error


def test_F06_missing_placsp_procurement_root(api: ModuleType, cases: Cases) -> None:
    changed = cases.mutate_xml(cases.get('C01-P000'), CFS, lambda entry, node: entry.remove(node))
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        changed.normalize(api)
    assert caught.value.reason == 'missing_root_or_wrong_shape'


@pytest.mark.parametrize('projection', [BATCH + '/6', BATCH + '/-1', BATCH + '/01', '/2023~1800'])
def test_F07_F08_invalid_member_pointer_no_first_member_fallback(api: ModuleType, cases: Cases, projection: str) -> None:
    case = cases.get('J14')
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        case.normalize(api, projection=projection)
    assert caught.value.reason == 'unresolvable_projection'
    assert caught.value.projection_locator == projection
    assert caught.value.raw_source_record_id == case.raw.raw_record_id


def test_F08_batch_expansion_atomic_but_explicit_sibling_still_works(api: ModuleType, cases: Cases) -> None:
    changed = cases.mutate_json(cases.get('J14'), BATCH + '/1', 42)
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        changed.normalize(api)
    assert caught.value.reason == 'missing_root_or_wrong_shape'
    assert caught.value.projection_locator == BATCH + '/1'
    sibling = changed.one(api, projection=BATCH + '/0')
    assert sibling.procedure_numbers[0].value == '2023/585'


def test_F10_opaque_batch_cannot_become_header_procedure(api: ModuleType, cases: Cases) -> None:
    changed = cases.mutate_json(cases.get('J14'), BATCH, 'opaque')
    with pytest.raises(api.UnsupportedNormalizationInput) as caught:
        changed.normalize(api)
    assert caught.value.reason == 'unprojectable_subject'


@pytest.mark.parametrize('field', ['raw_record_id', 'dataset'])
def test_F11_missing_required_provenance(api: ModuleType, cases: Cases, field: str) -> None:
    case = cases.get('C01-G')
    raw = replace(case.raw, **{field: ''})
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        api.normalize(raw, resolve=partial(load_record, case.root))
    assert caught.value.reason == 'missing_provenance'


def test_E24_legacy_capability_is_explicit_not_invalid_json(api: ModuleType, cases: Cases) -> None:
    case = cases.get('L07')
    assert case.raw.content.format == 'xml'
    with pytest.raises(api.UnsupportedNormalizationInput) as caught:
        case.normalize(api)
    assert caught.value.reason == 'unsupported_structure_or_format'
    assert caught.value.raw_source_record_id == case.raw.raw_record_id


@pytest.mark.parametrize('error_type', [KeyError, IndexError, TypeError, RuntimeError, PermissionError, ArtifactReadError])
def test_B03_B04_unexpected_or_system_errors_propagate(api: ModuleType, cases: Cases, error_type: type[Exception]) -> None:
    case = cases.get('C01-G')
    sentinel = error_type('fault injection, not corrupt source data')
    before = asdict(case.raw)
    def resolve(content):
        raise sentinel
    with pytest.raises(error_type) as caught:
        api.normalize(case.raw, resolve=resolve)
    assert caught.value is sentinel
    assert asdict(case.raw) == before


@pytest.mark.parametrize('fault', ['dangling_lot', 'duplicate_key', 'wrong_publication_reference', 'empty_lot_scope'])
def test_B01_output_references_are_invariants(api: ModuleType, cases: Cases, fault: str) -> None:
    observation = cases.get('C05-G1').one(api)
    with pytest.raises(api.NormalizationInvariantError):
        if fault == 'dangling_lot':
            invalid = replace(observation, focus=replace(observation.focus, lot_keys=('does-not-exist',)))
        elif fault == 'duplicate_key':
            invalid = replace(observation, lots=observation.lots + observation.lots)
        elif fault == 'wrong_publication_reference':
            award = replace(observation.awards[0], publication_keys=(observation.lots[0].key,))
            invalid = replace(observation, awards=(award,))
        else:
            invalid = replace(observation, focus=replace(observation.focus, lot_keys=(), source_lot_identifiers=()))
        api.validate_observation(invalid)


@pytest.mark.parametrize('fault', ['mapping_version', 'schema_version', 'valid_money_without_value', 'invalid_money_with_value'])
def test_B02_generated_metadata_and_money_states(api: ModuleType, cases: Cases, fault: str) -> None:
    observation = cases.get('C01-G').one(api)
    with pytest.raises(api.NormalizationInvariantError):
        if fault in ('mapping_version', 'schema_version'):
            invalid = replace(observation, **{fault: ''})
        else:
            item = observation.financials[0]
            money = replace(item.value, value=None, value_state='valid') if fault == 'valid_money_without_value' else replace(item.value, value=Decimal('1'), value_state='invalid')
            invalid = replace(observation, financials=(replace(item, value=money),) + observation.financials[1:])
        api.validate_observation(invalid)


@pytest.mark.parametrize('kind', ['CERRADA', 'ANULADA', 'UNREVIEWED'])
def test_T01_tombstones_never_become_procurement_cancellations(api: ModuleType, cases: Cases, kind: str) -> None:
    case = cases.get('T01')
    body = (case.root / case.raw.content.artifact.path).read_bytes().replace(b'type="CERRADA"', f'type="{kind}"'.encode())
    changed = cases.from_bytes('tombstone-synthetic', body, 'placsp')
    assert changed.normalize(api) == ()
