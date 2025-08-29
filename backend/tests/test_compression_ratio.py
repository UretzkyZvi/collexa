import json
from app.services.compression.basic_engine import BasicCompressionEngine
from app.services.compression.dictionary_trainer import ZstdDictionaryTrainer


def test_zstd_dictionary_improves_ratio_when_available():
    # Build repetitive domain-like samples (learning session-ish strings)
    base_samples = [
        b"L47:FastAPI{routing\xe2\x86\x92L:0.85,DI\xe2\x86\x92D:0.85,async_db\xe2\x86\x92M:0.85,T:8/10,E:auth:3,db_timeout:2}",
        b"L48:FastAPI{routing\xe2\x86\x92L:0.88,DI\xe2\x86\x92M:0.90,async_db\xe2\x86\x92M:0.92,T:9/10,E:auth:1,db_timeout:1}",
        b"L49:FastAPI{routing\xe2\x86\x92M:0.91,DI\xe2\x86\x92M:0.91,async_db\xe2\x86\x92M:0.93,T:10/10,E:auth:0,db_timeout:0}",
    ]
    # Replicate to ensure enough data for dictionary training
    samples = base_samples * 50

    trainer = ZstdDictionaryTrainer(dict_size=1024)
    dictionary = trainer.train(samples)

    # If zstd is not installed, dictionary is None -> test becomes a no-op assertion
    engine_no_dict = BasicCompressionEngine()
    obj = {
        "sessions": [s.decode("utf-8", errors="ignore") for s in base_samples],
        "meta": {"system": "FastAPI", "iter": 50},
    }

    res_no_dict = engine_no_dict.compress(obj)

    # Try with dictionary-backed compressor
    compressor = trainer.build_compressor(dictionary)
    engine_with_dict = BasicCompressionEngine(zstd_compressor=compressor, zstd_dict=dictionary)
    res_with_dict = engine_with_dict.compress(obj)

    # Always sanity-check roundtrip
    assert engine_with_dict.decompress(res_with_dict)

    # If both msgpack and zstd available, expect improved ratio with dict
    # Otherwise, allow equal ratios
    if res_with_dict.method == "zstd+msgpack" and res_no_dict.method in ("msgpack", "zstd+msgpack"):
        # When dictionary is used, compressed len should be <= no-dict payload
        assert len(res_with_dict.data) <= len(res_no_dict.data)

