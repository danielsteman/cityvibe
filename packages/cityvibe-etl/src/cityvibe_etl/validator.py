"""Event data validator."""


class EventValidator:
    """Validates event data for required fields and data quality."""

    def validate(self, event: dict) -> bool:
        """
        Validate an event dictionary.

        Checks:
        - Required fields (title, start_time, venue_id, source_url)
        - Date sanity (start_time in future, end_time after start_time)
        - Price ranges (price_min <= price_max)
        - URL formats

        Args:
            event: Event dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        # TODO: Implement validation logic
        return True

    def validate_batch(self, events: list[dict]) -> list[dict]:
        """Validate a batch of events, returning only valid ones."""
        return [e for e in events if self.validate(e)]
