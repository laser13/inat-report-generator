from pathlib import Path

from inat_report.config import load_config


def test_load_beetles_config():
    config = load_config(Path("configs/beetles_cyprus.yaml"))
    assert config.slug == "beetles_cyprus"
    assert config.title == "Beetles of Cyprus"
    assert config.source.csv_pattern == "observations-beetles-cyprus-{year}.csv"
    assert config.source.csv_all_time == "observations-beetles-cyprus.csv"


def test_config_defaults():
    config = load_config(Path("configs/beetles_cyprus.yaml"))
    assert config.report.top_species_count == 20
    assert config.report.top_observers_count == 10
    assert config.report.language == "en"
