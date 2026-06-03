import pandas as pd

def export_matches(data, filename):

    df = pd.DataFrame(
        data,
        columns=[
            "Joueur",
            "Adversaire",
            "Score",
            "Deck",
            "Deck adverse",
            "Statut"
        ]
    )

    df.to_csv(
        filename,
        index=False
    )
