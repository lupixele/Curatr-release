# Owner: Lochan | Curatr — Baselines and scoring functions
# See Curatr-dev docs/members/02-lochan-maths-and-scoring.md
# PRACTICE — NOT REFERENCE DATA
#C = 
#m = 


def global_score(rating: float, vote_count: int, C: float, m: float) -> float:
    """Bayesian weighted score pulling raw rating toward global prior C."""
    return (vote_count * rating + m * C) / (vote_count + m)

def genre_score(rating: float, vote_count: int, C: float, m: float, G: float) -> float:
    """Genre-adjusted score evaluating performance relative to genre baseline G."""
    return C + (vote_count / (vote_count + m)) * (rating - G)

