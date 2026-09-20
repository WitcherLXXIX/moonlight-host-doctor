import json

from conftest import fixture, ok

from moonlight_host_doctor.cli import main
from moonlight_host_doctor.redact import redact

# Shaped like real output, with invented names and addresses.
REAL_CONNECTION = (
    "Connected. Clients on the tailnet can use linux.tail-demo.ts.net or 100.99.1.2."
)


def test_real_output_loses_the_tailnet_name_and_address():
    out = redact(REAL_CONNECTION)
    assert "tail-demo" not in out and "100.99.1.2" not in out
    assert out == "Connected. Clients on the tailnet can use <host>.<tailnet>.ts.net or <ipv4>."


def test_bare_tailnet_suffix_is_masked_too():
    assert redact("suffix tail-demo.ts.net.") == "suffix <tailnet>.ts.net."


def test_ipv6_and_mac_addresses_are_masked():
    assert redact("fd7a:115c:a1e0::ab12:34cd") == "<ipv6>"
    assert redact("link 02:00:00:aa:bb:cc up") == "link <mac> up"


def test_lan_addresses_and_ranges_are_masked_but_the_tailnet_constant_is_kept():
    assert redact("from 192.0.2.0/24 and 192.0.2.59") == "from <ipv4> and <ipv4>"
    text = "a client on your tailnet (100.64.0.0/10) is blocked"
    assert redact(text) == text


def test_ports_versions_and_commands_are_left_alone():
    for text in (
        "sudo ufw allow 47984,47989,48010/tcp",
        "sudo ufw allow 47998:48000/udp",
        "Sunshine 2026.914.233613 on port 47989",
        "systemctl --user enable --now app-dev.lizardbyte.app.Sunshine.service",
    ):
        assert redact(text) == text


def test_redact_flag_applies_to_text_and_json_and_default_is_untouched(make, capsys):
    system = make({
        "tailscale status --json": ok(fixture("tailscale_status_healthy.json")),
        ("getent", "hosts", "linux.tail-example.ts.net"): ok(fixture("getent_tailscale_name.txt")),
    })
    main(["--only", "tailscale"], system=system)
    assert "linux.tail-example.ts.net" in capsys.readouterr().out

    main(["--only", "tailscale", "--redact"], system=system)
    text = capsys.readouterr().out
    assert "tail-example" not in text and "100.64.0.10" not in text
    assert "<host>.<tailnet>.ts.net" in text

    main(["--only", "tailscale", "--redact", "--json"], system=system)
    raw = capsys.readouterr().out
    assert "tail-example" not in raw and "100.64.0.10" not in raw
    assert json.loads(raw)[0]["check"] == "tailscale"


def test_an_address_at_the_end_of_a_sentence_is_masked_but_a_version_number_is_not():
    assert redact("use 100.99.1.2.") == "use <ipv4>."
    assert redact("use 100.99.1.2, or 10.0.0.1)") == "use <ipv4>, or <ipv4>)"
    assert redact("version 1.102.4 and 2026.914.233613") == "version 1.102.4 and 2026.914.233613"


def test_times_and_ordinary_colon_text_are_not_mistaken_for_ipv6():
    for text in ("at 12:30:45 today", "Status: active", "a:b", "ss:ss:ss"):
        assert redact(text) == text


def test_ipv6_with_a_prefix_length_is_masked():
    assert redact("via fd7a:115c:a1e0::/48 now") == "via <ipv6> now"
