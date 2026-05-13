# -*- coding: utf-8 -*-
"""Calcule numerice pentru întrebările 4–6 (seminar Bayes)."""


def q4():
    """Fig. 8: D → F, D → G (doar D, F, G)."""
    p_D = {1: 0.7, 0: 0.3}
    p_F_D = {1: {1: 0.8, 0: 0.2}, 0: {1: 0.5, 0: 0.5}}
    p_G_D = {1: {1: 0.25, 0: 0.75}, 0: {1: 0.65, 0: 0.35}}

    def p_joint(d, f, g):
        return p_D[d] * p_F_D[d][f] * p_G_D[d][g]

    table_d_fg = {}
    for f in (0, 1):
        for g in (0, 1):
            unnorm = {d: p_joint(d, f, g) for d in (0, 1)}
            s = sum(unnorm.values())
            table_d_fg[(f, g)] = {d: unnorm[d] / s for d in (0, 1)}

    p_G = {}
    for g in (0, 1):
        p_G[g] = sum(p_D[d] * p_G_D[d][g] for d in (0, 1))

    p_F_G = {}
    for g in (0, 1):
        p_F_G[g] = {}
        for f in (0, 1):
            p_F_G[g][f] = sum(p_D[d] * p_F_D[d][f] * p_G_D[d][g] for d in (0, 1)) / p_G[g]

    return table_d_fg, p_G, p_F_G


def q5():
    """Fig. 9: D și E fără arc între ele; G are părinți D, E."""
    p_E = {1: 0.25, 0: 0.75}
    p_D = {1: 0.7, 0: 0.3}
    p_G_de = {
        (1, 1): 0.9,
        (1, 0): 0.8,
        (0, 1): 0.6,
        (0, 0): 0.2,
    }

    def p_g(d, e, g):
        p1 = p_G_de[(d, e)]
        return p1 if g == 1 else (1 - p1)

    def p_joint_de(d, e):
        return p_D[d] * p_E[e]

    p_D_GE = {}
    for e in (0, 1):
        for g in (0, 1):
            unnorm = {d: p_joint_de(d, e) * p_g(d, e, g) for d in (0, 1)}
            s = sum(unnorm.values())
            p_D_GE[(g, e)] = {d: unnorm[d] / s for d in (0, 1)}

    return p_D, p_E, p_D_GE


def q6_bruteforce():
    """Fig. 10: p(A)p(B)p(C)p(D|A,B)p(E|C)p(F|D)p(G|D,E)."""
    p_A = {1: 0.6, 0: 0.4}
    p_B = {1: 0.8, 0: 0.2}
    p_C = {1: 0.1, 0: 0.9}

    def p_d_ab(a, b, d):
        if a == 1 and b == 1:
            return 0.9 if d == 1 else 0.1
        if a == 1 and b == 0:
            return 0.6 if d == 1 else 0.4
        if a == 0 and b == 1:
            return 0.6 if d == 1 else 0.4
        return 0.05 if d == 1 else 0.95

    def p_e_c(c, e):
        if c == 1:
            return 0.7 if e == 1 else 0.3
        return 0.2 if e == 1 else 0.8

    def p_f_d(d, f):
        if d == 1:
            return 0.8 if f == 1 else 0.2
        return 0.5 if f == 1 else 0.5

    def p_g_de(d, e, g):
        if d == 1 and e == 1:
            return 0.9 if g == 1 else 0.1
        if d == 1 and e == 0:
            return 0.8 if g == 1 else 0.2
        if d == 0 and e == 1:
            return 0.6 if g == 1 else 0.4
        return 0.2 if g == 1 else 0.8

    joint = {}
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                for d in (0, 1):
                    for e in (0, 1):
                        for f in (0, 1):
                            for g in (0, 1):
                                p = (
                                    p_A[a]
                                    * p_B[b]
                                    * p_C[c]
                                    * p_d_ab(a, b, d)
                                    * p_e_c(c, e)
                                    * p_f_d(d, f)
                                    * p_g_de(d, e, g)
                                )
                                joint[(a, b, c, d, e, f, g)] = p

    s = sum(joint.values())
    if abs(s - 1.0) > 1e-5:
        raise RuntimeError(f"joint sum {s}")

    def cond(query_fn, given_fn):
        num = 0.0
        den = 0.0
        for k, p in joint.items():
            if given_fn(k):
                den += p
                if query_fn(k):
                    num += p
        return num / den if den > 0 else float("nan")

    return {
        "P(B=1|F=1)": cond(lambda k: k[1] == 1 and k[5] == 1, lambda k: k[5] == 1),
        "P(B=1|F=0)": cond(lambda k: k[1] == 1 and k[5] == 0, lambda k: k[5] == 0),
        "P(A=1|¬F∩¬G)": cond(
            lambda k: k[0] == 1 and k[5] == 0 and k[6] == 0,
            lambda k: k[5] == 0 and k[6] == 0,
        ),
        "P(B=1|¬C)": cond(lambda k: k[1] == 1 and k[2] == 0, lambda k: k[2] == 0),
    }


if __name__ == "__main__":
    import json

    t4, pG, pFG = q4()
    print("Q4 p(D|F,G):", json.dumps({str(k): v for k, v in t4.items()}, indent=2))
    print("Q4 p(G):", pG)
    print("Q4 p(F|G):", json.dumps(pFG, indent=2))
    pD, pE, pDGE = q5()
    print("Q5a: p(D|E)=p(D) =>", pD)
    print("Q5b p(D|G,E):", json.dumps({str(k): v for k, v in pDGE.items()}, indent=2))
    print("Q6:", json.dumps({k: round(v, 6) for k, v in sorted(q6_bruteforce().items())}, indent=2))
