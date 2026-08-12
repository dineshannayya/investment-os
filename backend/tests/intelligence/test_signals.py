"""
Tests for Investment Signal extractor.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.signals import SignalExtractor
from app.processors import DocumentContent


class TestSignalExtractor:
    """Tests for SignalExtractor."""

    @staticmethod
    def create_document(
        text: str,
        title: str = "Investment Signals",
    ) -> DocumentContent:
        return DocumentContent(
            document_id=uuid4(),
            title=title,
            text=text,
            page_count=1,
            metadata={},
        )

    @staticmethod
    def create_chunks(text: str) -> list[Chunk]:
        return [
            Chunk(
                index=0,
                text=text,
                start_offset=0,
                end_offset=len(text),
                metadata={},
            )
        ]

    # ==========================================================
    # Properties
    # ==========================================================

    def test_name(self):
        extractor = SignalExtractor()

        assert extractor.name == "signals"

    def test_supports(self):
        extractor = SignalExtractor()

        assert extractor.supports(
            self.create_document("Seed funding")
        )

    # ==========================================================
    # Stage
    # ==========================================================

    def test_extract_seed_stage(self):
        text = "The company is raising a Seed round."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert signals.stage == "seed"

    def test_extract_pre_seed_stage(self):
        text = "Currently in pre-seed funding."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert signals.stage == "pre_seed"

    # ==========================================================
    # Industry
    # ==========================================================

    def test_extract_healthcare(self):
        text = "AI platform for hospitals and patient care."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "healthcare" in signals.industry

    def test_extract_semiconductor(self):
        text = "RISC-V semiconductor SoC."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "semiconductor" in signals.industry

    # ==========================================================
    # Business Model
    # ==========================================================

    def test_extract_saas(self):
        text = "Subscription SaaS platform."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "saas" in signals.business_models

    def test_extract_marketplace(self):
        text = "Marketplace connecting buyers and sellers."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "marketplace" in signals.business_models

    def test_extract_b2b(self):
        text = "Enterprise B2B software."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "b2b" in signals.business_models

    # ==========================================================
    # Technology
    # ==========================================================

    def test_extract_ai(self):
        text = "Generative AI and LLM platform."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "ai" in signals.technologies

    def test_extract_iot(self):
        text = "IoT edge device."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "iot" in signals.technologies

    # ==========================================================
    # Geography
    # ==========================================================

    def test_extract_india(self):
        text = "Headquartered in Bengaluru, India."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "india" in signals.geographies

    # ==========================================================
    # Markets
    # ==========================================================

    def test_extract_enterprise_market(self):
        text = "Enterprise software."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "enterprise" in signals.markets

    # ==========================================================
    # Themes
    # ==========================================================

    def test_extract_deeptech(self):
        text = "DeepTech startup."

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "deeptech" in signals.themes

    # ==========================================================
    # Combined
    # ==========================================================

    def test_complete_document(self):
        text = """
Seed funding.

AI SaaS platform.

Enterprise software.

Healthcare diagnostics.

DeepTech startup.

Based in Bengaluru, India.
"""

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert signals.stage == "seed"

        assert "healthcare" in signals.industry

        assert "saas" in signals.business_models

        assert "ai" in signals.technologies

        assert "enterprise" in signals.markets

        assert "india" in signals.geographies

        assert "deeptech" in signals.themes

    # ==========================================================
    # Empty
    # ==========================================================

    def test_empty_document(self):
        signals = SignalExtractor().extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        assert signals.stage is None

        assert signals.industry == ()

        assert signals.business_models == ()

        assert signals.technologies == ()

        assert signals.markets == ()

        assert signals.geographies == ()

        assert signals.themes == ()

    # ==========================================================
    # Confidence
    # ==========================================================

    def test_confidence_range(self):
        text = """
Seed funding.

AI SaaS platform.

Enterprise software.
"""

        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert 0.0 <= signals.confidence <= 1.0

    def test_confidence_increases(self):
        extractor = SignalExtractor()

        empty = extractor.extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        full = extractor.extract(
            self.create_document(
                """
Seed funding.

AI SaaS platform.

Healthcare.

Enterprise.

India.

DeepTech.
"""
            ),
            self.create_chunks(
                """
Seed funding.

AI SaaS platform.

Healthcare.

Enterprise.

India.

DeepTech.
"""
            ),
        )

        assert full.confidence > empty.confidence

    # Duplicate signal detection
    def test_duplicate_industry(self):
        text = """
    Hospital management.
    
    Hospital analytics.
    
    Medical platform.
    """
    
        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert signals.industry == ("healthcare",)
   
    # Multiple technologies 
    def test_multiple_technologies(self):
        text = """
    AI powered IoT platform.
    """
    
        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert "ai" in signals.technologies
        assert "iot" in signals.technologies
   
    # Stage precedence 
    def test_first_stage_wins(self):
        text = """
    Pre-seed startup.
    
    Seed funding.
    """
    
        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert signals.stage == "pre_seed"
   
    # Case-insensitive extraction 
    def test_case_insensitive(self):
        text = """
    GENERATIVE AI
    SAAS
    ENTERPRISE
    """
    
        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert "ai" in signals.technologies
        assert "saas" in signals.business_models
        assert "enterprise" in signals.markets


    def test_semiconductor_ai_company(self):
    
        text = """
        Seed funding.
    
        AI powered RISC-V SoC.
    
        Enterprise customers.
    
        Bengaluru India.
    
        DeepTech.
        """
    
        signals = SignalExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert signals.stage == "seed"
    
        assert "semiconductor" in signals.industry
    
        assert "ai" in signals.technologies
    
        assert "enterprise" in signals.markets
    
        assert "india" in signals.geographies
    
        assert "deeptech" in signals.themes
        
