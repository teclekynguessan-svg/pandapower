import pytest

from pandapower.webapp.network_model import (
    add_iacm,
    add_line,
    add_station,
    add_transformer,
    create_network,
)


def test_add_stations_and_matching_transformer():
    net = create_network()
    hv_bus = add_station(net, "Poste HT", 110, "Poste transformateur")
    lv_bus = add_station(net, "Poste HTA", 20, "Poste de distribution")

    trafo = add_transformer(net, hv_bus, lv_bus, "40 MVA 110/20 kV", "T1")

    assert net.trafo.at[trafo, "hv_bus"] == hv_bus
    assert net.trafo.at[trafo, "lv_bus"] == lv_bus
    assert net.bus.at[hv_bus, "zone"] == "Poste transformateur"


def test_transformer_rejects_mismatched_standard_voltage():
    net = create_network()
    hv_bus = add_station(net, "Poste HT", 110, "Poste transformateur")
    lv_bus = add_station(net, "Poste HTA", 10, "Poste de distribution")

    with pytest.raises(ValueError, match="ne correspondent pas"):
        add_transformer(net, hv_bus, lv_bus, "40 MVA 110/20 kV", "T1")


def test_add_line_and_iacm_at_line_end():
    net = create_network()
    bus_a = add_station(net, "Poste A", 20, "Poste de distribution")
    bus_b = add_station(net, "Poste B", 20, "Poste de distribution")
    line = add_line(
        net,
        bus_a,
        bus_b,
        2.5,
        "NA2XS2Y 1x95 RM/25 12/20 kV",
        "L1",
    )

    switch = add_iacm(net, line, bus_a, closed=False, in_ka=0.4, name="IACM-1")

    assert net.switch.at[switch, "element"] == line
    assert net.switch.at[switch, "bus"] == bus_a
    assert not net.switch.at[switch, "closed"]
    assert net.switch.at[switch, "type"] == "DS"


def test_line_rejects_different_voltage_levels():
    net = create_network()
    bus_a = add_station(net, "Poste HT", 110, "Poste transformateur")
    bus_b = add_station(net, "Poste HTA", 20, "Poste de distribution")

    with pytest.raises(ValueError, match="même tension"):
        add_line(
            net,
            bus_a,
            bus_b,
            2.5,
            "NA2XS2Y 1x95 RM/25 12/20 kV",
            "L1",
        )
