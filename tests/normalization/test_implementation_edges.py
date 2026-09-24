from copy import deepcopy
from datetime import date
import xml.etree.ElementTree as ET

import pytest

from .support import CFS, NS, issue, semantic, xml_path


@pytest.mark.parametrize('code,normalized', [('PRE', 'prior_information'), ('ADJ', 'award_reported')])
def test_remaining_documented_lifecycle_labels(api, cases, code, normalized):
    path = xml_path('ext:ContractFolderStatus/ebc:ContractFolderStatusCode')
    changed = cases.mutate_xml(cases.get('C01-P000'), path, lambda entry, node: setattr(node, 'text', code))
    assert changed.one(api).statuses[0].value.normalized == normalized


def test_xml_comments_are_raw_evidence_not_procurement_elements(api, cases):
    base = cases.get('C01-P000')
    changed = cases.mutate_xml(base, CFS, lambda entry, node: node.append(ET.Comment('retained source annotation')))
    assert semantic(changed.one(api)) == semantic(base.one(api))


def test_distinct_atom_display_title_is_not_discarded(api, cases):
    path = xml_path('a:title')
    changed = cases.mutate_xml(cases.get('C01-P000'), path, lambda entry, node: setattr(node, 'text', 'Distinct source display title'))
    titles = changed.one(api).titles
    assert len(titles) == 2
    assert any(text.text == 'Distinct source display title' and text.source_role == 'atom_title' for text in titles)


def test_negative_result_owns_its_explicit_decision_date(api, cases):
    def add_date(entry, node):
        ET.SubElement(node, '{' + NS['cbc'] + '}AwardDate').text = '2026-01-02'
    changed = cases.mutate_xml(cases.get('C09-P000'), xml_path('ext:ContractFolderStatus/cac:TenderResult'), add_date)
    observation = changed.one(api)
    assert not observation.awards
    assert observation.outcomes[0].decision_at.local_date == date(2026, 1, 2)


def test_unreviewed_multi_project_result_does_not_pool_totals(api, cases):
    parent = xml_path('ext:ContractFolderStatus/cac:TenderResult')
    path = parent + '/' + xml_path('cac:AwardedTenderedProject')[2:]
    changed = cases.mutate_xml(cases.get('C07-P001'), path, lambda entry, node: entry.find(parent).append(deepcopy(node)))
    observation = changed.one(api)
    assert not observation.awards
    assert observation.outcomes[0].scope.kind == 'unknown'
    issue(observation, 'unsupported_structure', parent)


def test_batch_header_mixed_flag_is_not_a_member_assertion(api, cases):
    assert all(item.mixed_contract is None for item in cases.get('J14').normalize(api))
