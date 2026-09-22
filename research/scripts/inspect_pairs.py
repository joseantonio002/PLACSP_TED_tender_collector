import argparse
import json

from compare_sources import connect

p = argparse.ArgumentParser()
p.add_argument('ids', nargs='+')
a = p.parse_args()
db = connect()
for suffix in a.ids:
    for row in db.execute('SELECT * FROM latest WHERE id LIKE ?', ('%/' + suffix,)):
        x = json.loads(row['data'])
        y = [json.loads(r[0]) for r in db.execute('SELECT data FROM g WHERE uuid=?', (x['uuid'],))]
        fields = ('id', 'uuid', 'publication_id', 'expediente', 'buyer_name', 'buyer_ids', 'updated', 'status', 'title', 'budget', 'estimated_value', 'deadline_date', 'deadline_time', 'awards', 'lots', 'notices')
        gfields = ('id_intern', 'codi_organ', 'nom_organ', 'codi_expedient', 'enllac_publicacio', 'fase_publicacio', 'resultat', 'numero_lot', 'pressupost_licitacio_sense_1', 'valor_estimat_expedient', 'termini_presentacio_ofertes', 'data_publicacio_anunci', 'data_publicacio_adjudicacio', 'data_publicacio_formalitzacio', 'data_publicacio_anul', 'identificacio_adjudicatari', 'import_adjudicacio_sense', ':updated_at')
        print(json.dumps({'placsp': {k: x[k] for k in fields}, 'gencat': [{k: r.get(k) for k in gfields if r.get(k) is not None} for r in y]}, ensure_ascii=False, indent=2))
