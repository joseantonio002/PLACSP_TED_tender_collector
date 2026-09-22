from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse, parse_qs
import zipfile
import xml.etree.ElementTree as ET

from download import ROOT

ATOM = '{http://www.w3.org/2005/Atom}'
TOMB = '{http://purl.org/atompub/tombstones/1.0}'


def local(tag: str) -> str:
    return tag.split('}')[-1]


def text(e: ET.Element | None, path: str) -> str | None:
    if e is None:
        return None
    node = e.find(path)
    return node.text.strip() if node is not None and node.text else None


def texts(e: ET.Element, path: str) -> list[str]:
    return [n.text.strip() for n in e.findall(path) if n.text and n.text.strip()]


def tree(e: ET.Element) -> dict:
    return {'tag': e.tag, 'attributes': dict(e.attrib), 'text': (e.text or '').strip(), 'children': [tree(n) for n in e]}


def stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def url_ids(url: str | None) -> tuple[str | None, str | None]:
    import re
    if not url:
        return None, None
    u = urlparse(url)
    if u.hostname not in ('contractaciopublica.cat', 'contractaciopublica.gencat.cat'):
        return None, None
    uuid = re.search(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}', u.path)
    pub = re.search(r'/detall-publicacio/(?:[^/]+/)?(\d+)(?:/|$)', u.path)
    return uuid.group().lower() if uuid else None, pub.group(1) if pub else parse_qs(u.query).get('idDoc', [None])[0]


def parse_entry(e: ET.Element) -> dict:
    c = e.find('{*}ContractFolderStatus')
    if c is None:
        c = ET.Element('missing')
    party = c.find('{*}LocatedContractingParty/{*}Party')
    project = c.find('{*}ProcurementProject')
    budget = project.find('{*}BudgetAmount') if project is not None else None
    ids = [(n.attrib.get('schemeName', ''), (n.text or '').strip()) for n in party.findall('{*}PartyIdentification/{*}ID')] if party is not None else []
    link = e.find(ATOM + 'link')
    url = link.attrib.get('href') if link is not None else None
    uuid, publication_id = url_ids(url)
    nuts = texts(c, './/{*}RealizedLocation/{*}CountrySubentityCode')
    buyer_postal = text(party, '{*}PostalAddress/{*}PostalZone')
    agent = text(party, '{*}AgentParty/{*}PartyIdentification/{*}ID')
    reasons = []
    if agent == '62':
        reasons.append('origin_platform_62')
    if url and urlparse(url).hostname in ('contractaciopublica.cat', 'contractaciopublica.gencat.cat'):
        reasons.append('pscp_url')
    if any(n.startswith('ES51') for n in nuts):
        reasons.append('execution_nuts_ES51')
    if buyer_postal and len(buyer_postal) == 5 and buyer_postal[:2] in ('08', '17', '25', '43'):
        reasons.append('buyer_postcode_catalunya')
    lots = []
    for lot in c.findall('{*}ProcurementProjectLot'):
        lots.append({'id': text(lot, '{*}ID'), 'title': text(lot, '{*}ProcurementProject/{*}Name'), 'budget': text(lot, '{*}ProcurementProject/{*}BudgetAmount/{*}TaxExclusiveAmount'), 'cpv': texts(lot, './/{*}ItemClassificationCode')})
    awards = []
    for result in c.findall('{*}TenderResult'):
        awards.append({'result': text(result, '{*}ResultCode'), 'award_date': text(result, '{*}AwardDate'), 'lot': text(result, '{*}AwardedTenderedProject/{*}ProcurementProjectLotID'), 'amount': text(result, '{*}AwardedTenderedProject/{*}LegalMonetaryTotal/{*}TaxExclusiveAmount'), 'supplier_ids': texts(result, './/{*}WinningParty/{*}PartyIdentification/{*}ID'), 'supplier_names': texts(result, './/{*}WinningParty/{*}PartyName/{*}Name'), 'contract_dates': texts(result, './/{*}Contract/{*}IssueDate')})
    notices = []
    for n in c.findall('{*}ValidNoticeInfo'):
        notices.append({'type': text(n, '{*}NoticeTypeCode'), 'notice_issue': text(n, '{*}NoticeIssueDate'), 'media': texts(n, './/{*}PublicationMediaName'), 'dates': texts(n, './/{*}IssueDate'), 'ids': texts(n, './/{*}ID'), 'urls': texts(n, './/{*}URI')})
    docs = []
    for n in c:
        if 'DocumentReference' in local(n.tag):
            docs.append({'kind': local(n.tag), 'id': text(n, '{*}ID'), 'urls': texts(n, './/{*}URI')})
    obj = {'id': text(e, ATOM + 'id'), 'updated': text(e, ATOM + 'updated'), 'url': url, 'uuid': uuid, 'publication_id': publication_id, 'expediente': text(c, '{*}ContractFolderID'), 'title': text(e, ATOM + 'title'), 'status': text(c, '{*}ContractFolderStatusCode'), 'buyer_name': text(party, '{*}PartyName/{*}Name'), 'buyer_ids': ids, 'buyer_postal': buyer_postal, 'agent': agent, 'agent_name': text(party, '{*}AgentParty/{*}PartyName/{*}Name'), 'budget': text(budget, '{*}TaxExclusiveAmount'), 'budget_gross': text(budget, '{*}TotalAmount'), 'estimated_value': text(budget, '{*}EstimatedOverallContractAmount'), 'currency': [n.attrib.get('currencyID') for n in budget] if budget is not None else [], 'cpv': texts(c, './/{*}ItemClassificationCode'), 'execution_nuts': nuts, 'execution_names': texts(c, './/{*}RealizedLocation/{*}CountrySubentity'), 'deadline_date': text(c, '{*}TenderingProcess/{*}TenderSubmissionDeadlinePeriod/{*}EndDate'), 'deadline_time': text(c, '{*}TenderingProcess/{*}TenderSubmissionDeadlinePeriod/{*}EndTime'), 'procedure_type': text(c, '{*}TenderingProcess/{*}ProcedureCode'), 'lots': lots, 'awards': awards, 'notices': notices, 'documents': docs, 'geography_reasons': reasons}
    return obj


def inspect(path: Path) -> None:
    out = ROOT / 'data/processed/placsp'
    out.mkdir(parents=True, exist_ok=True)
    target = out / f'{path.stem}.sqlite'
    if target.exists():
        print(f'Already processed: {target.name}', flush=True)
        return
    tmp = target.with_suffix('.working')
    db = sqlite3.connect(tmp)
    db.executescript('CREATE TABLE observations (id TEXT, updated TEXT, uuid TEXT, publication_id TEXT, expediente TEXT, buyer TEXT, status TEXT, hash TEXT, content_hash TEXT, member TEXT, ordinal INTEGER, data TEXT); CREATE TABLE tombstones (id TEXT, updated TEXT, kind TEXT, member TEXT, data TEXT);')
    counts, statuses, months, agents, geo, fields, schema = (Counter() for _ in range(7))
    pages = []
    min_date, max_date = None, None
    def paths(node: ET.Element, prefix: str = '') -> set[str]:
        name = prefix + '/' + local(node.tag)
        found = {name}
        for child in node:
            found.update(paths(child, name))
        return found
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.namelist() if m.endswith('.atom')]
        for i, member in enumerate(members):
            root = ET.fromstring(z.read(member))
            entries = root.findall(ATOM + 'entry')
            tombs = root.findall(TOMB + 'deleted-entry')
            pages.append({'member': member, 'entries': len(entries), 'tombstones': len(tombs), 'updated': text(root, ATOM + 'updated'), 'links': [n.attrib for n in root.findall(ATOM + 'link')]})
            for t in tombs:
                counts['tombstones'] += 1
                kind = t.find(TOMB + 'comment')
                kind = kind.attrib.get('type') if kind is not None else None
                counts[f'tombstone_{kind}'] += 1
                db.execute('INSERT INTO tombstones VALUES (?,?,?,?,?)', (t.attrib.get('ref'), t.attrib.get('when'), kind, member, json.dumps(tree(t))))
            for ordinal, e in enumerate(entries):
                counts['all_entries'] += 1
                updated = text(e, ATOM + 'updated')
                if not updated or not '2025-01-01' <= updated[:10] <= '2026-09-22':
                    counts['outside_updated_date_scope'] += 1
                    continue
                counts['in_time_entries'] += 1
                min_date = min(min_date, updated) if min_date else updated
                max_date = max(max_date, updated) if max_date else updated
                o = parse_entry(e)
                agents[o['agent_name'] or '(none)'] += 1
                if not o['geography_reasons']:
                    continue
                counts['selected_entries'] += 1
                geo.update(o['geography_reasons'])
                statuses[o['status']] += 1
                months[updated[:7]] += 1
                presence = {'expediente': o['expediente'], 'buyer_identifier': o['buyer_ids'], 'buyer_nif': any(s.upper() in ('NIF', 'CIF') for s, v in o['buyer_ids'] if v), 'cpv': o['cpv'], 'budget': o['budget'], 'estimated_value': o['estimated_value'], 'deadline': o['deadline_date'], 'execution_location': o['execution_nuts'] or o['execution_names'], 'status': o['status'], 'source_link': o['url'], 'document_links': any(d['urls'] for d in o['documents']), 'award_information': o['awards'], 'winner': any(a['supplier_ids'] or a['supplier_names'] for a in o['awards']), 'lots': o['lots']}
                fields.update(k for k, v in presence.items() if v)
                schema.update(paths(e))
                counts['lot_occurrences'] += len(o['lots'])
                counts['award_result_occurrences'] += len(o['awards'])
                counts['notice_type_group_occurrences'] += len(o['notices'])
                content_hash = stable_hash(tree(e.find('{*}ContractFolderStatus')))
                o['archive'] = str(path.relative_to(ROOT))
                o['member'], o['ordinal'] = member, ordinal
                raw_hash = stable_hash(tree(e))
                buyer = next((v for s, v in o['buyer_ids'] if s == 'ID_OC_PLAT'), None)
                db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (o['id'], updated, o['uuid'], o['publication_id'], o['expediente'], buyer, o['status'], raw_hash, content_hash, member, ordinal, json.dumps(o, ensure_ascii=False)))
            if i % 100 == 0:
                db.commit()
                print(f'{path.name}: {i + 1}/{len(members)} pages; {counts["selected_entries"]:,} selected', flush=True)
    db.executescript('CREATE INDEX obs_id ON observations(id); CREATE INDEX obs_uuid ON observations(uuid); CREATE INDEX obs_buyer_exp ON observations(buyer, expediente);')
    db.commit()
    db.close()
    tmp.rename(target)
    result = {'archive': str(path.relative_to(ROOT)), 'counts': counts, 'min_updated': min_date, 'max_updated': max_date, 'selected_statuses': statuses, 'selected_months': months, 'all_agents': agents, 'selected_geography': geo, 'selected_field_presence': fields, 'selected_xml_path_entry_counts': schema, 'pages': pages}
    (out / f'{path.stem}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ('pages', 'selected_xml_path_entry_counts')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('archives', nargs='+', type=Path)
    a = p.parse_args()
    for archive in a.archives:
        inspect(archive.resolve())
