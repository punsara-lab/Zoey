import mind


def test_normalize_strips_aliases():
    assert mind.normalize_user_text("Baby ZOEY, how are you?") == "how are you?"
    assert mind.normalize_user_text("Needle 2: list recent files") == "list recent files"
    assert mind.normalize_user_text("gemma, what time is it") == "what time is it"


def test_file_intent():
    assert mind.is_file_request("find my physics notes")
    assert mind.is_file_request("list recent files")
    assert mind.is_file_request("organize these pdf files")
    assert not mind.is_file_request("how are you today")
    assert not mind.is_file_request("file a plan for studying")


def test_identity_and_public_name():
    assert "Zoey" in mind.sanitize_identity("I am Gemma")
    assert mind.public_model_name("local:gemma3:1b") == "zoey · local"
    assert mind.public_model_name("baby:local_symbolic (0.90)") == "zoey · memory"
    assert mind.public_model_name("tool:run_needle2_file_agent") == "zoey · files"


def test_speak_files():
    spoken = mind.speak_files("C:\\notes\\physics.pdf")
    assert spoken.startswith("Here's what I found:")
    assert "physics.pdf" in spoken


if __name__ == "__main__":
    test_normalize_strips_aliases()
    test_file_intent()
    test_identity_and_public_name()
    test_speak_files()
    print("Mind unification tests passed")
