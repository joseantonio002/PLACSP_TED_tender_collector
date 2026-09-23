from types import ModuleType

import pytest

from .support import Cases, ids, json_bytes


PHASES = [
    ('data_publicacio_futura', 'url_json_futura', 'future_notice'),
    ('data_publicacio_consulta', 'url_json_cpm', 'market_consultation'),
    ('data_publicacio_previ', 'url_json_previ', 'prior_information'),
    ('data_publicacio_anunci', 'url_json_licitacio', 'tender_notice'),
    ('data_publicacio_avaluacio', 'url_json_avaluacio', 'evaluation'),
    ('data_publicacio_adjudicacio', 'url_json_adjudicacio', 'award_notice'),
    ('data_publicacio_formalitzacio', 'url_json_formalitzacio', 'formalization_notice'),
    ('data_publicacio_anul', 'url_json_anulacio', 'annulment_notice'),
    ('data_publicacio_contracte', 'url_json_agregada', 'aggregate_contract_report'),
    ('data_publicacio_encarrec', None, 'own_resource_entrustment_notice'),
]


@pytest.mark.parametrize('date_field,export_field,phase', PHASES)
def test_D25_every_phase_date_is_independent(api: ModuleType, cases: Cases, date_field: str, export_field: str | None, phase: str) -> None:
    base = cases.get('C14-G0' if phase == 'aggregate_contract_report' else 'C16-parent')
    token = '2026-01-02T03:04:00.000'
    observation = cases.mutate_json(base, '/' + date_field, token).one(api)
    publication, = [publication for publication in observation.publications if publication.publication_at and publication.publication_at.raw == token]
    assert publication.type.normalized == phase
    assert publication.publication_at.utc_instant is None
    assert not publication.identifiers
    if phase == 'aggregate_contract_report':
        assert publication.scope.kind == 'publication_batch'


@pytest.mark.parametrize('date_field,export_field,phase', [row for row in PHASES if row[1]])
def test_D25_same_phase_export_pairing(api: ModuleType, cases: Cases, date_field: str, export_field: str, phase: str) -> None:
    base = cases.get('C14-G0' if phase == 'aggregate_contract_report' else 'C16-parent')
    row = base.payload()
    row[date_field] = '2026-01-02T03:04:00.000'
    row[export_field] = cases.get('C01-G').payload()['url_json_licitacio']
    case = cases.from_bytes('synthetic-phase-pair', json_bytes([row]), 'main', recipe=(base.raw.content.document_sha256, date_field + '+' + export_field, 'synthetic paired phase fields, not a retained phase combination'))
    observation = case.one(api)
    publication, = [p for p in observation.publications if p.publication_at and p.publication_at.raw == row[date_field]]
    assert publication.type.normalized == phase and ids(publication.identifiers) == ['300885987']
    reference, = [reference for reference in observation.source_references if reference.source_path == '/' + export_field + '/url']
    assert reference.publication_keys == (publication.key,)


@pytest.mark.parametrize('removed', ['data_publicacio_anunci', 'url_json_licitacio'])
def test_D25_partial_phase_reference_survives(api: ModuleType, cases: Cases, removed: str) -> None:
    observation = cases.mutate_json(cases.get('C01-G'), '/' + removed).one(api)
    if removed == 'data_publicacio_anunci':
        publication, = [p for p in observation.publications if '300885987' in ids(p.identifiers)]
        assert publication.publication_at is None
    else:
        publication, = [p for p in observation.publications if p.publication_at and p.publication_at.raw == '2026-09-17T20:18:00.000']
        assert not publication.identifiers
    assert publication.type.normalized == 'tender_notice'
