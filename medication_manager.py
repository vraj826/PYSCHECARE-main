import json
import uuid
from datetime import date
from pathlib import Path


DEFAULT_STORE = Path(__file__).with_name("medications.json")
MAX_FIELD_LENGTH = 120
MAX_NOTES_LENGTH = 500


class MedicationValidationError(ValueError):
    pass


class MedicationManager:
    def __init__(self, store_path=DEFAULT_STORE):
        self.store_path = Path(store_path)

    def list_medications(self):
        return self._read()["medications"]

    def list_logs(self):
        return self._read()["logs"]

    def create_medication(self, data):
        medication = self._validated_medication(data)
        medication["id"] = str(uuid.uuid4())
        store = self._read()
        store["medications"].append(medication)
        self._write(store)
        return medication

    def update_medication(self, medication_id, data):
        updates = self._validated_medication(data)
        store = self._read()
        for index, medication in enumerate(store["medications"]):
            if medication["id"] == medication_id:
                updates["id"] = medication_id
                store["medications"][index] = updates
                self._write(store)
                return updates
        return None

    def delete_medication(self, medication_id):
        store = self._read()
        remaining = [
            medication for medication in store["medications"]
            if medication["id"] != medication_id
        ]
        if len(remaining) == len(store["medications"]):
            return False
        store["medications"] = remaining
        self._write(store)
        return True

    def log_adherence(self, medication_id, status, log_date=None):
        if status not in {"taken", "skipped"}:
            raise MedicationValidationError("Status must be taken or skipped.")
        entry_date = self._validate_date(log_date or date.today().isoformat(), "date")

        store = self._read()
        medication = next(
            (item for item in store["medications"] if item["id"] == medication_id),
            None,
        )
        if not medication:
            return None

        log_entry = {
            "id": str(uuid.uuid4()),
            "medication_id": medication_id,
            "medication_name": medication["name"],
            "date": entry_date,
            "status": status,
        }
        store["logs"].append(log_entry)
        self._write(store)
        return log_entry

    def adherence_stats(self):
        logs = self.list_logs()
        total = len(logs)
        taken = len([entry for entry in logs if entry["status"] == "taken"])
        skipped = len([entry for entry in logs if entry["status"] == "skipped"])
        percentage = round((taken / total) * 100) if total else 0
        return {
            "total_doses_logged": total,
            "taken_count": taken,
            "skipped_count": skipped,
            "adherence_percentage": percentage,
        }

    def due_today(self):
        today = date.today().isoformat()
        return [
            medication for medication in self.list_medications()
            if medication["start_date"] <= today
        ]

    def _validated_medication(self, data):
        name = self._required_text(data, "name", "Medication name")
        dosage = self._required_text(data, "dosage", "Dosage")
        frequency = self._optional_text(data, "frequency", "Frequency") or "As directed"
        notes = self._optional_text(data, "notes", "Notes", MAX_NOTES_LENGTH)
        start_date = self._validate_date(data.get("start_date", ""), "start date")
        return {
            "name": name,
            "dosage": dosage,
            "frequency": frequency,
            "start_date": start_date,
            "notes": notes,
        }

    def _required_text(self, data, field, label):
        value = self._optional_text(data, field, label)
        if not value:
            raise MedicationValidationError(f"{label} is required.")
        return value

    def _optional_text(self, data, field, label, max_length=MAX_FIELD_LENGTH):
        value = str(data.get(field, "")).strip()
        if len(value) > max_length:
            raise MedicationValidationError(
                f"{label} must be {max_length} characters or fewer."
            )
        return value

    def _validate_date(self, value, label):
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError as exc:
            raise MedicationValidationError(f"Please enter a valid {label}.") from exc

    def _read(self):
        if not self.store_path.exists():
            return {"medications": [], "logs": []}
        with self.store_path.open("r", encoding="utf-8") as store_file:
            data = json.load(store_file)
        return {
            "medications": data.get("medications", []),
            "logs": data.get("logs", []),
        }

    def _write(self, data):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("w", encoding="utf-8") as store_file:
            json.dump(data, store_file, indent=2)
