"""Data processing pipeline package.

The pipeline turns raw extracted leads into clean, validated, deduplicated
leads that are ready for export. Every stage lives in its own small module so
it can be reused and tested in isolation:

- :class:`LeadNormalizer` cleans field values into a consistent form.
- :class:`LeadValidator` checks the required business name and any present
  optional fields.
- :class:`LeadDeduplicator` removes duplicate businesses.
- :class:`ProcessingPipeline` orchestrates the three stages.
"""

from app.processing.lead_deduplicator import DeduplicationResult, LeadDeduplicator
from app.processing.lead_normalizer import LeadNormalizer
from app.processing.lead_validator import LeadValidator, ValidationResult
from app.processing.processing_pipeline import ProcessingPipeline, ProcessingResult

__all__ = [
    "DeduplicationResult",
    "LeadDeduplicator",
    "LeadNormalizer",
    "LeadValidator",
    "ProcessingPipeline",
    "ProcessingResult",
    "ValidationResult",
]
