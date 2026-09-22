import unittest
import xml.etree.ElementTree as ET
from decimal import Decimal

from compare_sources import amount, norm
from inspect_placsp import parse_entry, stable_hash, tree, url_ids


class ResearchTests(unittest.TestCase):
    def test_direct_publication_link(self):
        self.assertEqual(url_ids('https://contractaciopublica.cat/ca/detall-publicacio/4b131001-63ad-4eac-a80a-ab91c3a9f366/300888482'), ('4b131001-63ad-4eac-a80a-ab91c3a9f366', '300888482'))

    def test_old_publication_link(self):
        self.assertEqual(url_ids('https://contractaciopublica.gencat.cat/ecofin_pscp/AppJava/notice.pscp?idDoc=12345'), (None, '12345'))

    def test_other_host_not_shared_identifier(self):
        self.assertEqual(url_ids('https://example.com/detall-publicacio/4b131001-63ad-4eac-a80a-ab91c3a9f366/300888482'), (None, None))

    def test_single_numeric_publication_link(self):
        self.assertEqual(url_ids('https://contractaciopublica.cat/ca/detall-publicacio/300888482'), (None, '300888482'))

    def test_uuid_only_link_does_not_invent_publication_id(self):
        self.assertEqual(url_ids('https://contractaciopublica.cat/ca/detall-publicacio/4b131001-63ad-4eac-a80a-ab91c3a9f366'), ('4b131001-63ad-4eac-a80a-ab91c3a9f366', None))

    def test_decimal_values_not_float(self):
        self.assertEqual(amount('949509.10'), amount('949509.1'))
        self.assertEqual(amount('0'), Decimal('0'))
        self.assertIsNone(amount('10||20'))
        self.assertIsNone(amount(None))

    def test_matching_normalization_is_lossy(self):
        self.assertEqual(norm('AB-01 / 2025'), norm('ab012025'))
        self.assertNotEqual(norm('01/2025'), norm('1/2025'))

    def test_xml_tree_hash_ignores_indentation_not_attributes(self):
        a = ET.fromstring('<x a="1"><y>value</y></x>')
        b = ET.fromstring('<x a="1">\n  <y>value</y>\n</x>')
        c = ET.fromstring('<x a="2"><y>value</y></x>')
        self.assertEqual(stable_hash(tree(a)), stable_hash(tree(b)))
        self.assertNotEqual(stable_hash(tree(a)), stable_hash(tree(c)))

    def test_buyer_and_winner_ids_are_separate(self):
        xml = '<entry xmlns="http://www.w3.org/2005/Atom" xmlns:c="urn:codice"><id>p</id><updated>2025-01-01T12:00:00+01:00</updated><c:ContractFolderStatus><c:LocatedContractingParty><c:Party><c:PartyIdentification><c:ID schemeName="ID_OC_PLAT">62</c:ID></c:PartyIdentification><c:AgentParty><c:PartyIdentification><c:ID>62</c:ID></c:PartyIdentification></c:AgentParty></c:Party></c:LocatedContractingParty><c:ProcurementProject><c:BudgetAmount><c:TaxExclusiveAmount currencyID="EUR">0</c:TaxExclusiveAmount></c:BudgetAmount></c:ProcurementProject><c:TenderResult><c:WinningParty><c:PartyIdentification><c:ID schemeName="NIF">supplier</c:ID></c:PartyIdentification></c:WinningParty></c:TenderResult></c:ContractFolderStatus></entry>'
        o = parse_entry(ET.fromstring(xml))
        self.assertEqual(o['buyer_ids'], [('ID_OC_PLAT', '62')])
        self.assertEqual(o['awards'][0]['supplier_ids'], ['supplier'])
        self.assertEqual(o['budget'], '0')
        self.assertIn('origin_platform_62', o['geography_reasons'])
        self.assertNotIn('execution_nuts_ES51', o['geography_reasons'])


if __name__ == '__main__':
    unittest.main()
