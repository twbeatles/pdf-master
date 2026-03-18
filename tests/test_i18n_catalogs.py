def test_i18n_catalog_key_sets_match():
    from src.core.i18n_catalogs import EN_TRANSLATIONS, KO_TRANSLATIONS

    assert set(KO_TRANSLATIONS) == set(EN_TRANSLATIONS)


def test_i18n_facade_reexports_catalogs():
    from src.core import i18n
    from src.core.i18n_catalogs import EN_TRANSLATIONS, KO_TRANSLATIONS

    assert i18n.TRANSLATIONS["ko"] is KO_TRANSLATIONS
    assert i18n.TRANSLATIONS["en"] is EN_TRANSLATIONS
