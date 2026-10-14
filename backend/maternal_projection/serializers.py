"""Serializers for the identity-review queue."""
from rest_framework import serializers

from .models import IdentityCandidate


REASON_LABELS = {
    "card_match_name_conflict": "Card number matches, but the name looks different",
    "card_match_name_missing": "Card number matches, but there's no name on this row to verify against",
    "card_match_stale": "Card number matches, but the last sighting is over a year old",
    "probabilistic": "Possible match on name/phone — no shared card number",
}


class IdentityCandidateSerializer(serializers.ModelSerializer):
    new_record = serializers.SerializerMethodField()
    candidate = serializers.SerializerMethodField()
    reason_label = serializers.SerializerMethodField()

    class Meta:
        model = IdentityCandidate
        fields = [
            "id",
            "confidence",
            "matched_fields",
            "status",
            "created_at",
            "reason",
            "reason_label",
            "new_record",
            "candidate",
        ]

    def get_reason_label(self, obj):
        return REASON_LABELS.get(obj.reason, "Candidate match for review")

    def get_new_record(self, obj):
        row = obj.source_row
        return {
            "source_row_id": str(row.id),
            "intake_id": str(row.intake_id),
            "register_family": row.intake.register_family,
            "row_number": row.row_number,
            "values": row.normalized or {},
            "service_date": row.service_date,
        }

    def get_candidate(self, obj):
        w = obj.candidate_woman
        return {
            "woman_id": str(w.id),
            "internal_id": w.internal_id,
            "name": w.name,
            "stable_identifier": w.stable_identifier,
            "phone": w.phone,
        }
