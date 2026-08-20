"""
Tests for EntityExtractor.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.entities import EntityExtractor
from app.processors import DocumentContent


class TestEntityExtractor:
    """Tests for EntityExtractor."""

    @staticmethod
    def create_document(
        text: str,
        title: str = "Investment Document",
    ) -> DocumentContent:
        return DocumentContent(
            document_id=uuid4(),
            title=title,
            text=text,
            page_count=1,
            metadata={},
        )

    @staticmethod
    def create_chunks(
        text: str,
    ) -> list[Chunk]:
        return [
            Chunk(
                index=0,
                text=text,
                start_offset=0,
                end_offset=len(text),
                metadata={},
            )
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_name(self):
        extractor = EntityExtractor()

        assert extractor.name == "entities"

    def test_supports(self):
        extractor = EntityExtractor()

        document = self.create_document("Company: Investment OS")

        assert extractor.supports(document)

    # ------------------------------------------------------------------
    # Company
    # ------------------------------------------------------------------

    def test_extract_company(self):
        text = """
Company: SemSure
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name == "SemSure"

    def test_extract_startup_keyword(self):
        text = """
Startup: Investment OS
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name == "Investment OS"

    def test_extract_organization_keyword(self):
        text = """
Organization: BigEndian Semiconductor
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name == "BigEndian Semiconductor"

    def test_company_not_found(self):
        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document("No company mentioned."),
            self.create_chunks("No company mentioned."),
        )

        assert entities.company_name is None

    def test_empty_company_value(self):
        text = """
Company:
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name is None

    def test_company_whitespace_normalized(self):
        text = """
Company:   SemSure    Technologies   Pvt Ltd
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name == (
            "SemSure Technologies Pvt Ltd"
        )

    # ------------------------------------------------------------------
    # Founders
    # ------------------------------------------------------------------

    def test_extract_founders(self):
        text = """
Founders: Alice, Bob
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.founders == (
            "Alice",
            "Bob",
        )

    def test_extract_singular_founder(self):
        text = """
Founder: Alice
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.founders == (
            "Alice",
        )

    def test_duplicate_founders_removed(self):
        text = """
Founders: Alice, Bob, Alice
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.founders == (
            "Alice",
            "Bob",
        )

    def test_duplicate_founders_case_insensitive(self):
        text = """
Founders: Alice, alice, Bob
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.founders == (
            "Alice",
            "Bob",
        )

    def test_founder_whitespace_normalized(self):
        text = """
Founders:   Alice   Smith  ;   Bob   Kumar
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.founders == (
            "Alice Smith",
            "Bob Kumar",
        )

    # ------------------------------------------------------------------
    # Investors
    # ------------------------------------------------------------------

    def test_extract_investors(self):
        text = """
Investors: Lets Venture, Campus Angels
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.investors == (
            "Lets Venture",
            "Campus Angels",
        )

    def test_extract_singular_investor(self):
        text = """
Investor: Lets Venture
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.investors == (
            "Lets Venture",
        )

    # ------------------------------------------------------------------
    # Accelerators
    # ------------------------------------------------------------------

    def test_extract_accelerators(self):
        text = """
Accelerator: NSRCEL
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.accelerators == (
            "NSRCEL",
        )

    def test_extract_singular_accelerator(self):
        text = """
Accelerator: NSRCEL
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.accelerators == (
            "NSRCEL",
        )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    def test_extract_locations(self):
        text = """
Location: Bengaluru, India
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.locations == (
            "Bengaluru",
            "India",
        )

    def test_extract_singular_location(self):
        text = """
Location: Bengaluru
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.locations == (
            "Bengaluru",
        )

    def test_extract_plural_locations(self):
        text = """
Locations: Bengaluru, India
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.locations == (
            "Bengaluru",
            "India",
        )

    # ------------------------------------------------------------------
    # Sector
    # ------------------------------------------------------------------

    def test_extract_sector(self):
        text = """
Sector: Healthcare, AI
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.sectors == (
            "Healthcare",
            "AI",
        )

    def test_extract_singular_sector(self):
        text = """
Sector: Healthcare
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.sectors == (
            "Healthcare",
        )

    def test_extract_plural_sectors(self):
        text = """
Sectors: Healthcare, AI
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.sectors == (
            "Healthcare",
            "AI",
        )

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def test_extract_products(self):
        text = """
Products: Smart Camera, Edge Gateway
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.products == (
            "Smart Camera",
            "Edge Gateway",
        )

    def test_extract_singular_product(self):
        text = """
Product: Vision SoC
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.products == (
            "Vision SoC",
        )

    # ------------------------------------------------------------------
    # Technologies
    # ------------------------------------------------------------------

    def test_extract_technologies(self):
        text = """
Technologies: AI, RISC-V
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.technologies == (
            "AI",
            "RISC-V",
        )

    def test_extract_singular_technology(self):
        text = """
Technology: Computer Vision
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.technologies == (
            "Computer Vision",
        )

    def test_duplicate_technologies_case_insensitive(self):
        text = """
Technologies: AI, ai, RISC-V, RISC-V
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.technologies == (
            "AI",
            "RISC-V",
        )

    # ------------------------------------------------------------------
    # Empty values
    # ------------------------------------------------------------------

    def test_empty_entity_values_are_ignored(self):
        text = """
Company:
Founders:
Investors:
Products:
Technology:
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name is None
        assert entities.founders == ()
        assert entities.investors == ()
        assert entities.products == ()
        assert entities.technologies == ()

    # ------------------------------------------------------------------
    # Combined extraction
    # ------------------------------------------------------------------

    def test_extract_complete_document(self):
        text = """
Company: SemSure

Founders: Alice, Bob

Investors: Lets Venture, Campus Angels

Accelerator: NSRCEL

Location: Bengaluru

Sector: Healthcare

Products: Diagnostic Kit

Technology: AI
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert entities.company_name == "SemSure"

        assert entities.founders == (
            "Alice",
            "Bob",
        )

        assert entities.investors == (
            "Lets Venture",
            "Campus Angels",
        )

        assert entities.accelerators == (
            "NSRCEL",
        )

        assert entities.locations == (
            "Bengaluru",
        )

        assert entities.sectors == (
            "Healthcare",
        )

        assert entities.products == (
            "Diagnostic Kit",
        )

        assert entities.technologies == (
            "AI",
        )

    # ------------------------------------------------------------------
    # Empty document
    # ------------------------------------------------------------------

    def test_empty_document(self):
        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        assert entities.company_name is None
        assert entities.founders == ()
        assert entities.investors == ()
        assert entities.accelerators == ()
        assert entities.locations == ()
        assert entities.sectors == ()
        assert entities.products == ()
        assert entities.technologies == ()

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def test_confidence_range(self):
        text = """
Company: SemSure
Founders: Alice
"""

        extractor = EntityExtractor()

        entities = extractor.extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert 0.0 <= entities.confidence <= 1.0

    def test_confidence_increases_with_entity_fields(self):
        extractor = EntityExtractor()

        one_field = extractor.extract(
            self.create_document(
                "Company: SemSure"
            ),
            self.create_chunks(
                "Company: SemSure"
            ),
        )

        two_fields = extractor.extract(
            self.create_document(
                """
Company: SemSure
Founders: Alice
"""
            ),
            self.create_chunks(
                """
Company: SemSure
Founders: Alice
"""
            ),
        )

        assert two_fields.confidence > one_field.confidence
