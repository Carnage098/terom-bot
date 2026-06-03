import matplotlib.pyplot as plt

def create_deck_graph(deck_data, filename):

    labels = []
    values = []

    for deck, count in deck_data:
        labels.append(deck)
        values.append(count)

    plt.figure(figsize=(8,5))
    plt.bar(labels, values)

    plt.title("Decks les plus joués")
    plt.ylabel("Nombre d'utilisations")

    plt.tight_layout()

    plt.savefig(filename)

    plt.close()
