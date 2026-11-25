Inventaire de réseau par interface web
======================================

Une interface Streamlit permet de saisir des postes/noeuds, transformateurs,
lignes HT/HTA et IACM, puis d'exporter le réseau au format JSON pandapower.

Installation et lancement depuis la racine du dépôt::

    pip install -e ".[webapp]"
    streamlit run pandapower/webapp/app.py

Les postes sont représentés par des bus pandapower, les transformateurs et lignes
par les éléments correspondants, et les IACM par des interrupteurs ``DS`` aux
extrémités de ligne. L'export est un réseau pandapower, mais un calcul de flux
nécessite aussi les sources et les charges du réseau.
