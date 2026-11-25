"""Streamlit interface for collecting electrical-network assets."""

from __future__ import annotations

import pandas as pd
import pandapower as pp
import streamlit as st
from pandapower.std_types import available_std_types

from pandapower.webapp.network_model import (
    STATION_TYPES,
    add_iacm,
    add_line,
    add_station,
    add_transformer,
    create_network,
)


st.set_page_config(page_title="Inventaire de réseau électrique", layout="wide")
st.title("Inventaire de réseau électrique")
st.caption(
    "Saisissez les postes et les ouvrages. Les données sont conservées dans un réseau pandapower "
    "et peuvent être exportées au format JSON."
)

if "network" not in st.session_state:
    st.session_state.network = create_network()
net = st.session_state.network

with st.sidebar:
    st.subheader("Réseau")
    network_name = st.text_input("Nom", value=net.name)
    base_mva = st.number_input("Puissance de base (MVA)", min_value=0.1, value=float(net.sn_mva))
    frequency = st.number_input("Fréquence (Hz)", min_value=1.0, value=float(net.f_hz))
    net.name = network_name.strip() or "Nouveau réseau"
    net.sn_mva = base_mva
    net.f_hz = frequency
    if st.button("Nouveau réseau", width="stretch"):
        st.session_state.network = create_network(
            name=net.name, sn_mva=base_mva, f_hz=frequency
        )
        st.rerun()


def bus_options() -> dict[str, int]:
    return {
        f"{idx} — {row['name'] or 'Sans nom'} ({row['vn_kv']:g} kV)": int(idx)
        for idx, row in net.bus.iterrows()
    }


def show_success(message: str) -> None:
    st.success(message)


stations_tab, transformer_tab, lines_tab, iacm_tab, network_tab, export_tab = st.tabs(
    ["Postes et noeuds", "Transformateurs", "Lignes HT / HTA", "IACM", "Réseau", "Export"]
)

with stations_tab:
    st.subheader("Ajouter un poste ou un noeud électrique")
    with st.form("station_form", clear_on_submit=True):
        station_name = st.text_input("Nom du poste / noeud")
        station_type = st.selectbox("Catégorie", STATION_TYPES)
        voltage_kv = st.number_input(
            "Tension nominale (kV)", min_value=0.01, value=20.0, step=1.0
        )
        if st.form_submit_button("Ajouter le poste"):
            try:
                idx = add_station(net, station_name, voltage_kv, station_type)
                show_success(f"Poste ajouté (bus {idx}).")
            except ValueError as exc:
                st.error(str(exc))
    st.caption(
        "Chaque poste est enregistré comme un bus pandapower. Créez des bus aux deux niveaux "
        "de tension avant d'ajouter un transformateur entre eux."
    )
    st.dataframe(net.bus, width="stretch")

with transformer_tab:
    st.subheader("Ajouter un transformateur")
    buses = bus_options()
    if len(buses) < 2:
        st.info("Ajoutez au moins deux postes/noeuds à des tensions différentes.")
    else:
        with st.form("transformer_form", clear_on_submit=True):
            hv_label = st.selectbox("Bus HT", list(buses))
            lv_label = st.selectbox("Bus BT / HTA", list(buses))
            hv_bus = buses[hv_label]
            lv_bus = buses[lv_label]
            hv_kv = float(net.bus.at[hv_bus, "vn_kv"])
            lv_kv = float(net.bus.at[lv_bus, "vn_kv"])
            trafo_types = available_std_types(net, "trafo")
            compatible_types = trafo_types[
                (trafo_types["vn_hv_kv"].sub(hv_kv).abs() < 1e-6)
                & (trafo_types["vn_lv_kv"].sub(lv_kv).abs() < 1e-6)
            ]
            if compatible_types.empty:
                st.warning(
                    "Aucun type standard du catalogue ne correspond exactement à ces tensions."
                )
                transformer_type = None
            else:
                transformer_type = st.selectbox(
                    "Type standard", compatible_types.index.tolist()
                )
            transformer_name = st.text_input("Nom du transformateur")
            submitted = st.form_submit_button("Ajouter le transformateur")
            if submitted:
                if transformer_type is None:
                    st.error("Choisissez des tensions ayant un type standard compatible.")
                else:
                    try:
                        idx = add_transformer(
                            net, hv_bus, lv_bus, transformer_type, transformer_name
                        )
                        show_success(f"Transformateur ajouté (index {idx}).")
                    except ValueError as exc:
                        st.error(str(exc))
    st.dataframe(net.trafo, width="stretch")

with lines_tab:
    st.subheader("Ajouter une ligne HT ou HTA")
    buses = bus_options()
    if len(buses) < 2:
        st.info("Ajoutez au moins deux postes/noeuds avant de créer une ligne.")
    else:
        with st.form("line_form", clear_on_submit=True):
            from_label = st.selectbox("Bus de départ", list(buses))
            to_label = st.selectbox("Bus d'arrivée", list(buses))
            length_km = st.number_input(
                "Longueur (km)", min_value=0.001, value=1.0, step=0.1
            )
            line_types = available_std_types(net, "line")
            line_type = st.selectbox("Type standard de ligne", line_types.index.tolist())
            line_name = st.text_input("Nom de la ligne")
            if st.form_submit_button("Ajouter la ligne"):
                try:
                    idx = add_line(
                        net,
                        buses[from_label],
                        buses[to_label],
                        length_km,
                        line_type,
                        line_name,
                    )
                    show_success(f"Ligne ajoutée (index {idx}).")
                except ValueError as exc:
                    st.error(str(exc))
    st.dataframe(net.line, width="stretch")

with iacm_tab:
    st.subheader("Ajouter un IACM")
    if net.line.empty:
        st.info("Ajoutez d'abord une ligne.")
    else:
        line_options = {
            f"{idx} — {row['name'] or 'Sans nom'}": int(idx)
            for idx, row in net.line.iterrows()
        }
        with st.form("iacm_form", clear_on_submit=True):
            line_label = st.selectbox("Ligne", list(line_options))
            line_idx = line_options[line_label]
            line_row = net.line.loc[line_idx]
            end_choice = st.radio("Extrémité", ["Départ", "Arrivée"], horizontal=True)
            bus_idx = int(line_row["from_bus"] if end_choice == "Départ" else line_row["to_bus"])
            bus_name = net.bus.at[bus_idx, "name"] or f"Bus {bus_idx}"
            st.text_input("Bus de raccordement", value=f"{bus_name} ({bus_idx})", disabled=True)
            iacm_name = st.text_input("Identifiant IACM")
            closed = st.selectbox("Position", ["Fermé", "Ouvert"]) == "Fermé"
            rated_current = st.number_input(
                "Courant nominal (kA)", min_value=0.001, value=0.4, step=0.1
            )
            if st.form_submit_button("Ajouter l'IACM"):
                try:
                    idx = add_iacm(
                        net, line_idx, bus_idx, closed, rated_current, iacm_name
                    )
                    show_success(f"IACM ajouté (interrupteur {idx}).")
                except ValueError as exc:
                    st.error(str(exc))
    st.dataframe(net.switch, width="stretch")
    st.caption(
        "Dans pandapower, l'IACM est représenté comme un interrupteur de sectionnement "
        "(type DS) au bout d'une ligne. Ce modèle décrit son état, pas ses protections."
    )

with network_tab:
    st.subheader("Éléments enregistrés")
    summary = pd.DataFrame(
        {"Élément": ["Postes / bus", "Transformateurs", "Lignes", "IACM / interrupteurs"],
         "Nombre": [len(net.bus), len(net.trafo), len(net.line), len(net.switch)]}
    )
    st.dataframe(summary, hide_index=True, width="stretch")
    for label, table_name in (
        ("Postes / bus", "bus"),
        ("Transformateurs", "trafo"),
        ("Lignes", "line"),
        ("IACM / interrupteurs", "switch"),
    ):
        with st.expander(label):
            st.dataframe(net[table_name], width="stretch")

with export_tab:
    st.subheader("Exporter le réseau pandapower")
    st.write("Le fichier JSON contient le réseau et ses tables pandapower.")
    st.download_button(
        "Télécharger le réseau (.json)",
        data=pp.to_json(net),
        file_name=f"{net.name.replace(' ', '_') or 'reseau'}.json",
        mime="application/json",
        width="stretch",
    )
    st.warning(
        "Les données d'inventaire seules ne suffisent pas à lancer un calcul de flux : "
        "il faut notamment ajouter les sources et les charges."
    )
