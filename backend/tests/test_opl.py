from app.services.compression.opl import CompressedOptimizationTrace


def test_opl_round_trip():
    trace = CompressedOptimizationTrace(
        heuristics=["CoT", "SelfCheck"],
        metrics={"acc": "0.82", "lat": "95ms", "cost": "0.12"},
        exemplars=["ex#12", "ex#48"],
        params={"temp": "0.2", "top_p": "0.9"},
        notes="improved on auth cases",
    )
    s = trace.to_opl()
    parsed = CompressedOptimizationTrace.from_opl(s)

    assert parsed.heuristics == ["CoT", "SelfCheck"]
    assert parsed.metrics.get("lat") == "95ms"
    assert parsed.params.get("top_p") == "0.9"
    assert "ex#48" in parsed.exemplars
    assert parsed.notes.startswith("improved on auth")


def test_opl_parsing_and_escaping():
    s = (
        r"H:CoT\+Self\|Check|M:acc:0.82,lat:95ms,cost:0.12|"
        r"E:ex\#12,ex\#48|P:temp:0.2,top\:p:0.9|N:improved\|auth"
    )
    parsed = CompressedOptimizationTrace.from_opl(s)

    assert parsed.heuristics == ["CoT+Self|Check"]
    assert parsed.metrics.get("cost") == "0.12"
    assert parsed.exemplars == ["ex#12", "ex#48"]
    assert parsed.params.get("top:p") == "0.9"
    assert parsed.notes == "improved|auth"

    out = parsed.to_opl()
    parsed2 = CompressedOptimizationTrace.from_opl(out)
    assert parsed2.params.get("top:p") == "0.9"

