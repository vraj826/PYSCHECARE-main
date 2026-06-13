import pytest

from medication_manager import MedicationManager, MedicationValidationError


@pytest.fixture
def manager(tmp_path):
    return MedicationManager(tmp_path / "medications.json")


def test_medication_creation(manager):
    medication = manager.create_medication({
        "name": "Sertraline",
        "dosage": "50 mg",
        "frequency": "Daily",
        "start_date": "2026-06-01",
        "notes": "Morning",
    })

    assert medication["id"]
    assert manager.list_medications()[0]["name"] == "Sertraline"


def test_medication_update(manager):
    medication = manager.create_medication({
        "name": "Sertraline",
        "dosage": "50 mg",
        "frequency": "Daily",
        "start_date": "2026-06-01",
    })

    updated = manager.update_medication(medication["id"], {
        "name": "Sertraline",
        "dosage": "75 mg",
        "frequency": "Daily",
        "start_date": "2026-06-01",
    })

    assert updated["dosage"] == "75 mg"
    assert manager.list_medications()[0]["dosage"] == "75 mg"


def test_medication_deletion(manager):
    medication = manager.create_medication({
        "name": "Vitamin D",
        "dosage": "1000 IU",
        "frequency": "Daily",
        "start_date": "2026-06-01",
    })

    assert manager.delete_medication(medication["id"]) is True
    assert manager.list_medications() == []


def test_mark_taken_and_skipped(manager):
    medication = manager.create_medication({
        "name": "Vitamin D",
        "dosage": "1000 IU",
        "frequency": "Daily",
        "start_date": "2026-06-01",
    })

    taken = manager.log_adherence(medication["id"], "taken", "2026-06-02")
    skipped = manager.log_adherence(medication["id"], "skipped", "2026-06-03")

    assert taken["status"] == "taken"
    assert skipped["status"] == "skipped"
    assert [entry["status"] for entry in manager.list_logs()] == ["taken", "skipped"]


def test_adherence_calculation(manager):
    medication = manager.create_medication({
        "name": "Vitamin D",
        "dosage": "1000 IU",
        "frequency": "Daily",
        "start_date": "2026-06-01",
    })
    manager.log_adherence(medication["id"], "taken", "2026-06-02")
    manager.log_adherence(medication["id"], "taken", "2026-06-03")
    manager.log_adherence(medication["id"], "skipped", "2026-06-04")

    assert manager.adherence_stats() == {
        "total_doses_logged": 3,
        "taken_count": 2,
        "skipped_count": 1,
        "adherence_percentage": 67,
    }


def test_validation_errors(manager):
    with pytest.raises(MedicationValidationError, match="Medication name is required"):
        manager.create_medication({
            "name": " ",
            "dosage": "10 mg",
            "frequency": "Daily",
            "start_date": "2026-06-01",
        })

    with pytest.raises(MedicationValidationError, match="Dosage is required"):
        manager.create_medication({
            "name": "Medication",
            "dosage": "",
            "frequency": "Daily",
            "start_date": "2026-06-01",
        })

    with pytest.raises(MedicationValidationError, match="valid start date"):
        manager.create_medication({
            "name": "Medication",
            "dosage": "10 mg",
            "frequency": "Daily",
            "start_date": "not-a-date",
        })
