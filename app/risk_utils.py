from app.models import RiskSeverity


def severity_for(risk_score: float) -> RiskSeverity:
    """Single source of truth for score -> severity band, so seeding and the
    live model never disagree on what counts as 'high' risk."""
    if risk_score >= 0.7:
        return RiskSeverity.high
    if risk_score >= 0.35:
        return RiskSeverity.watch
    return RiskSeverity.safe
