"""Helpers for building pandapower networks from collected asset data."""

from __future__ import annotations

from math import isclose

import pandapower as pp
from pandapower.auxiliary import pandapowerNet
from pandapower.std_types import available_std_types


STATION_TYPES = (
    "Poste transformateur",
    "Poste de distribution",
    "Autre noeud",
)


def create_network(name: str = "Nouveau réseau", sn_mva: float = 100.0,
                   f_hz: float = 50.0) -> pandapowerNet:
    """Create an empty pandapower network for asset collection."""
    if not name.strip():
        raise ValueError("Le nom du réseau ne peut pas être vide.")
    if sn_mva <= 0 or f_hz <= 0:
        raise ValueError("La puissance de base et la fréquence doivent être positives.")
    return pp.create_empty_network(name=name.strip(), sn_mva=sn_mva, f_hz=f_hz)


def add_station(net: pandapowerNet, name: str, vn_kv: float,
                station_type: str) -> int:
    """Add a station or network node as a pandapower bus."""
    if not name.strip():
        raise ValueError("Le nom du poste ou du noeud ne peut pas être vide.")
    if vn_kv <= 0:
        raise ValueError("La tension nominale doit être positive.")
    if station_type not in STATION_TYPES:
        raise ValueError(f"Type de poste inconnu : {station_type}")
    return pp.create_bus(
        net,
        vn_kv=vn_kv,
        name=name.strip(),
        zone=station_type,
    )


def add_transformer(net: pandapowerNet, hv_bus: int, lv_bus: int,
                    std_type: str, name: str) -> int:
    """Connect two buses with a transformer from the standard-type catalogue."""
    if hv_bus not in net.bus.index or lv_bus not in net.bus.index:
        raise ValueError("Les deux bus du transformateur doivent exister.")
    if hv_bus == lv_bus:
        raise ValueError("Les côtés HT et BT doivent être raccordés à des bus distincts.")
    if not name.strip():
        raise ValueError("Le nom du transformateur ne peut pas être vide.")

    hv_voltage = float(net.bus.at[hv_bus, "vn_kv"])
    lv_voltage = float(net.bus.at[lv_bus, "vn_kv"])
    if hv_voltage <= lv_voltage:
        raise ValueError("Le bus HT doit avoir une tension nominale supérieure au bus BT.")

    transformer_types = available_std_types(net, "trafo")
    if std_type not in transformer_types.index:
        raise ValueError(f"Type standard de transformateur inconnu : {std_type}")
    params = transformer_types.loc[std_type]
    if not (
        isclose(hv_voltage, float(params["vn_hv_kv"]), rel_tol=1e-6)
        and isclose(lv_voltage, float(params["vn_lv_kv"]), rel_tol=1e-6)
    ):
        raise ValueError(
            "Les tensions des bus ne correspondent pas aux tensions du type standard choisi."
        )

    return pp.create_transformer(
        net, hv_bus=hv_bus, lv_bus=lv_bus, std_type=std_type, name=name.strip()
    )


def add_line(net: pandapowerNet, from_bus: int, to_bus: int,
             length_km: float, std_type: str, name: str) -> int:
    """Add an overhead or underground AC line between equal-voltage buses."""
    if from_bus not in net.bus.index or to_bus not in net.bus.index:
        raise ValueError("Les deux bus de la ligne doivent exister.")
    if from_bus == to_bus:
        raise ValueError("Une ligne doit relier deux bus distincts.")
    if not isclose(
        float(net.bus.at[from_bus, "vn_kv"]),
        float(net.bus.at[to_bus, "vn_kv"]),
        rel_tol=1e-6,
    ):
        raise ValueError("Les deux extrémités de la ligne doivent avoir la même tension.")
    if length_km <= 0:
        raise ValueError("La longueur de la ligne doit être positive.")
    if not name.strip():
        raise ValueError("Le nom de la ligne ne peut pas être vide.")

    line_types = available_std_types(net, "line")
    if std_type not in line_types.index:
        raise ValueError(f"Type standard de ligne inconnu : {std_type}")
    return pp.create_line(
        net,
        from_bus=from_bus,
        to_bus=to_bus,
        length_km=length_km,
        std_type=std_type,
        name=name.strip(),
    )


def add_iacm(net: pandapowerNet, line: int, bus: int, closed: bool,
             in_ka: float, name: str) -> int:
    """Represent an IACM as a line-end disconnector in the pandapower switch table."""
    if line not in net.line.index:
        raise ValueError("La ligne sélectionnée n'existe pas.")
    if bus not in (net.line.at[line, "from_bus"], net.line.at[line, "to_bus"]):
        raise ValueError("L'IACM doit être raccordé à l'une des extrémités de la ligne.")
    if in_ka <= 0:
        raise ValueError("Le courant nominal de l'IACM doit être positif.")
    if not name.strip():
        raise ValueError("Le nom de l'IACM ne peut pas être vide.")

    return pp.create_switch(
        net,
        bus=bus,
        element=line,
        et="l",
        closed=closed,
        type="DS",
        name=name.strip(),
        in_ka=in_ka,
    )
