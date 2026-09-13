from signalpost.identity.normalizer import clean_org_number, normalize_company_name
from signalpost.identity.resolver import EntityResolver

def test_clean_org_number():
    assert clean_org_number(" 923 456 789 ") == "923456789"
    assert clean_org_number("NO923456789MVA") == "923456789"
    assert clean_org_number("12345") is None

def test_normalize_company_name():
    assert normalize_company_name("Equinor ASA") == "equinor"
    assert normalize_company_name("Kongsberg Gruppen AS") == "kongsberg"
    assert normalize_company_name("DNB BANK ASA") == "dnb bank"

def test_entity_resolver_strict():
    is_match, conf, _ = EntityResolver.resolve(
        candidate_org="923609016",
        candidate_name="Equinor ASA",
        target_org="923609016",
        target_name="Equinor"
    )
    assert is_match is True
    assert conf == 1.0

def test_entity_resolver_rejection():
    is_match, conf, _ = EntityResolver.resolve(
        candidate_org="999999999",
        candidate_name="Different Company AS",
        target_org="923609016",
        target_name="Equinor ASA"
    )
    assert is_match is False
    assert conf == 0.0
