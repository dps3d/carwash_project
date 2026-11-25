import json
from datetime import date, time
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import WashSlot


ATTACKERS = {"attacker1": "attack-pass-1", "attacker2": "attack-pass-2"}
SLOT_DATE = date(2099, 12, 1)
REGULAR_SLOTS = (
    (time(9), time(10)),
    (time(10), time(11)),
    (time(11), time(12)),
)
RACE_SLOT = (time(14), time(15))


class Command(BaseCommand):
    help = "Create attack users and reset the car wash slot catalog."

    def handle(self, *args, **options):
        User = get_user_model()
        for username, password in ATTACKERS.items():
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.save()

        for start_time, end_time in REGULAR_SLOTS:
            WashSlot.objects.update_or_create(
                date=SLOT_DATE,
                start_time=start_time,
                defaults={"end_time": end_time, "available": 50},
            )

        race_slot, _ = WashSlot.objects.update_or_create(
            date=SLOT_DATE,
            start_time=RACE_SLOT[0],
            defaults={"end_time": RACE_SLOT[1], "available": 1},
        )

        contract_path = Path(settings.BASE_DIR) / "contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["race_item"] = race_slot.pk
        contract_path.write_text(
            json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Ready: attacker1, attacker2, {WashSlot.objects.count()} slots; "
                f"race slot ID={race_slot.pk}, available={race_slot.available}."
            )
        )
