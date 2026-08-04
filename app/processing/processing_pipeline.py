"""Data processing pipeline.

ProcessingPipeline transforms raw extracted leads into clean, validated,
deduplicated leads that are ready for export. The pipeline runs three stages in
order — normalization, validation, and deduplication — and returns a
ProcessingResult holding the final leads and processing statistics.

Each stage is an injectable, independently testable component. Missing or
malformed data never crashes the pipeline: values that cannot be cleaned
become empty strings, and leads that fail validation are skipped while the
remaining leads keep flowing (Requirement 7).
"""

import logging
from dataclasses import dataclass, field

from app.config.logging_config import get_logger
from app.models.lead import Lead
from app.processing.lead_deduplicator import LeadDeduplicator
from app.processing.lead_normalizer import LeadNormalizer
from app.processing.lead_validator import LeadValidator, ValidationResult


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Statistics and final leads produced by the processing pipeline.

    Attributes:
        input_count: Number of leads received.
        valid_count: Number of leads that passed validation.
        invalid_count: Number of leads rejected during validation.
        duplicates_removed: Number of duplicate leads removed.
        leads: The final, clean leads ready for export.
    """

    input_count: int
    valid_count: int
    invalid_count: int
    duplicates_removed: int
    leads: list[Lead] = field(default_factory=list)

    @property
    def final_count(self) -> int:
        """Return the number of leads that survived processing."""
        return len(self.leads)


class ProcessingPipeline:
    """Normalize, validate, and deduplicate a list of leads."""

    def __init__(
        self,
        normalizer: LeadNormalizer | None = None,
        validator: LeadValidator | None = None,
        deduplicator: LeadDeduplicator | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the pipeline with its three stage components.

        Every stage is optional: a default implementation is created when one
        is not injected, so stages can be swapped or faked in isolation.

        Args:
            normalizer: Optional LeadNormalizer.
            validator: Optional LeadValidator.
            deduplicator: Optional LeadDeduplicator.
            logger: Optional logger; a package logger is used when omitted.
        """
        self._normalizer = normalizer or LeadNormalizer()
        self._validator = validator or LeadValidator()
        self._deduplicator = deduplicator or LeadDeduplicator(logger=logger)
        self._logger = logger or get_logger("processing")

    def process(self, leads: list[Lead] | None = None) -> ProcessingResult:
        """Run the pipeline over the given leads and return the result.

        Normalizes every lead, validates each one, and removes duplicates. An
        unexpected value never stops the run: leads that cannot be normalized
        or validated are skipped and logged.

        Args:
            leads: The raw extracted leads to process.

        Returns:
            A ProcessingResult with the final leads and processing statistics.
        """
        leads = list(leads or [])
        self._logger.info("Processing started. Total input leads: %d.", len(leads))

        self._logger.info("Normalization started.")
        normalized = [self._normalize_safely(lead) for lead in leads]
        self._logger.info("Normalization complete.")

        self._logger.info("Validation started.")
        valid: list[Lead] = []
        invalid_count = 0
        for lead in normalized:
            verdict = self._validate_safely(lead)
            if verdict is None or not verdict.is_valid:
                invalid_count += 1
                continue
            valid.append(lead)
        self._logger.info("Validation complete. Total valid leads: %d.", len(valid))

        self._logger.info("Deduplication started.")
        deduplicated = self._deduplicator.deduplicate(valid)
        self._logger.info(
            "Duplicate removal complete. Duplicates removed: %d.",
            deduplicated.duplicates_removed,
        )

        result = ProcessingResult(
            input_count=len(leads),
            valid_count=len(valid),
            invalid_count=invalid_count,
            duplicates_removed=deduplicated.duplicates_removed,
            leads=deduplicated.leads,
        )
        self._logger.info(
            "Processing completed. Input leads: %d, valid leads: %d, "
            "duplicates removed: %d, final leads: %d.",
            result.input_count,
            result.valid_count,
            result.duplicates_removed,
            result.final_count,
        )
        return result

    def _normalize_safely(self, lead: Lead) -> Lead:
        """Normalize a lead, keeping it unchanged if normalization fails."""
        try:
            return self._normalizer.normalize(lead)
        except Exception as exc:
            self._logger.warning("Normalization failed: %s. Keeping lead unchanged.", exc)
            return lead

    def _validate_safely(self, lead: Lead) -> ValidationResult | None:
        """Validate a lead, treating an unexpected value as invalid."""
        try:
            verdict = self._validator.validate(lead)
        except Exception as exc:
            self._logger.warning("Lead removed: 'unknown' (%s).", exc)
            return None
        if not verdict.is_valid:
            self._logger.warning("Lead removed: '%s' (%s).", lead.business_name, verdict.reason)
        return verdict
