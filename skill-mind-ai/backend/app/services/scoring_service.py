def calculate_weighted_score(tech_count=0, experience_years=0, project_count=0, has_edu=False, cert_count=0,
                             tech_score=None, exp_score=None, proj_score=None, edu_score=None, cert_score=None):
    """
    Fresher-Focused Weighted Score Formula:
    30% Technical + 10% Experience + 35% Projects + 20% Education + 5% Certifications
    """
    # Use provided scores OR calculate from counts
    t_score = tech_score if tech_score is not None else min((tech_count / 10) * 100, 100)
    e_score = exp_score if exp_score is not None else min((experience_years / 5) * 100, 100)
    p_score = proj_score if proj_score is not None else min(project_count * 25, 100)
    ed_score = edu_score if edu_score is not None else (100 if has_edu else 0)
    c_score = cert_score if cert_score is not None else min(cert_count * 25, 100)

    final_score = (0.3 * t_score) + (0.1 * e_score) + (0.35 * p_score) + (0.2 * ed_score) + (0.05 * c_score)
    
    return round(final_score, 1), {
        "technical": t_score,
        "experience": e_score,
        "projects": p_score,
        "education": ed_score,
        "certifications": c_score
    }
