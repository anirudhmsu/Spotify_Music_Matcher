from app.services.scoring import score


def test_score_basic_overlap():
    u1 = {
        "artists": ["a1", "a2", "a3"],
        "genres": ["techno", "house"],
        "audio": [120.0, 0.8, 0.6, 0.7, 0.1, -6.0],
    }
    u2 = {
        "artists": ["a2", "a3", "a4"],
        "genres": ["house", "trance"],
        "audio": [122.0, 0.78, 0.62, 0.69, 0.12, -6.5],
    }

    s = score(u1, u2)
    assert 0 < s <= 1
