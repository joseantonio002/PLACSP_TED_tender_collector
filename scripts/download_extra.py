from download import fetch

URLS = {
    'syndication-current.pdf': 'https://contrataciondelsectorpublico.gob.es/datosabiertos/especificacion-sindicacion.pdf',
    'datasets-summary.pdf': 'https://www.hacienda.gob.es/DGPatrimonio/plataforma_contratacion/resumen-datos-abiertos.pdf',
    'pscp-aoc-2023.pdf': 'https://www.localret.cat/wp-content/uploads/2023/04/Contractacio-Publica-i-AOC.pdf',
    'socrata-system-fields.html': 'https://dev.socrata.com/docs/system-fields.html',
    'socrata-paging.html': 'https://dev.socrata.com/docs/queries/offset',
}

for filename, source_url in URLS.items():
    fetch('documentation', source_url, filename)

fetch('gencat', 'https://analisi.transparenciacatalunya.cat/api/views/hb6v-jcbf.json', 'rpc-metadata.json')
fetch('gencat', 'https://analisi.transparenciacatalunya.cat/resource/ybgg-dgi6.json', 'audit-all-dates.json', {'$select': 'count(*) as total,min(data_publicacio_anunci) as first_tender_notice,max(data_publicacio_anunci) as last_tender_notice,min(data_publicacio_contracte) as first_aggregate,max(data_publicacio_contracte) as last_aggregate,min(:created_at) as min_row_created,max(:updated_at) as max_row_updated'})
