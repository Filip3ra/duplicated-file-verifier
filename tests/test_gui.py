from duplicate_verifier.gui import methods_from_toggles


def test_methods_from_toggles() -> None:
    assert methods_from_toggles(exact=True, visual=True) == ("exact", "visual")
    assert methods_from_toggles(exact=True, visual=False) == ("exact",)
    assert methods_from_toggles(exact=False, visual=True) == ("visual",)
    assert methods_from_toggles(exact=False, visual=False) == ()
