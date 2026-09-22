from datetime import datetime
from io import BytesIO
import zipfile
import xml.etree.ElementTree as ET

import requests


year_month = datetime.now().strftime("%Y%m")

url = (
    "https://contrataciondelsectorpublico.gob.es/"
    "sindicacion/sindicacion_643/"
    f"licitacionesPerfilesContratanteCompleto3_{year_month}.zip"
)

print(f"Downloading {url}")

response = requests.get(url, timeout=60)
response.raise_for_status()

with zipfile.ZipFile(BytesIO(response.content)) as zf:

    # Buscamos el Atom base del paquete.
    atom_name = next(
        name
        for name in zf.namelist()
        if name.endswith("licitacionesPerfilesContratanteCompleto3.atom")
    )

    print("Reading:", atom_name)

    xml_data = zf.read(atom_name)


ATOM = {"atom": "http://www.w3.org/2005/Atom"}

root = ET.fromstring(xml_data)

entries = root.findall("atom:entry", ATOM)

print("Entries in this Atom file:", len(entries))

entry = entries[0]


def text(path):
    element = entry.find(path, ATOM)
    return element.text.strip() if element is not None and element.text else None


print("\n--- BASIC ATOM DATA ---")

print("Title:  ", text("atom:title"))
print("Updated:", text("atom:updated"))
print("ID:     ", text("atom:id"))
print("Summary:", text("atom:summary"))

link = entry.find("atom:link", ATOM)

if link is not None:
    print("URL:    ", link.attrib.get("href"))


# {*} significa: ignora el namespace concreto.
# Es útil para una primera inspección.
contract_folder_id = entry.find(".//{*}ContractFolderID")

if contract_folder_id is not None:
    print("Expediente:", contract_folder_id.text)


print("\n--- RAW XML ---")

raw_entry = ET.tostring(
    entry,
    encoding="unicode"
)

print(raw_entry[:5000])