from app.providers.evidence_search import EvidenceSearchProvider
from app.schemas.analysis import EvidenceSource


class DemoFixtureEvidenceProvider:
    """Static illustrative sources for the initial suspicious-message example."""

    _FIXTURES = (
        (
            ("sebi", "approved", "investment plan"),
            EvidenceSource(
                title="DEMO FIXTURE: SEBI investor resources",
                url="https://www.sebi.gov.in/",
                snippet=(
                    "Illustrative demo snippet only. This fixture does not represent "
                    "a retrieved SEBI page or establish that any plan was approved."
                ),
                published_date=None,
            ),
        ),
        (
            ("guaranteed", "return", "30%"),
            EvidenceSource(
                title="DEMO FIXTURE: RBI financial awareness",
                url="https://www.rbi.org.in/",
                snippet=(
                    "Illustrative demo snippet only. No investment plan or promised "
                    "return was checked against this fixture."
                ),
                published_date=None,
            ),
        ),
        (
            ("slots", "remaining", "200"),
            EvidenceSource(
                title="DEMO FIXTURE: investor education example",
                url="https://www.nism.ac.in/",
                snippet=(
                    "Illustrative demo snippet only. No source confirms the number "
                    "of available slots in the promotional message."
                ),
                published_date=None,
            ),
        ),
    )

    async def search(self, query: str) -> list[EvidenceSource]:
        normalized = query.lower()
        for terms, source in self._FIXTURES:
            if sum(term in normalized for term in terms) >= 2:
                return [source]
        return []
