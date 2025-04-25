# src/kidscompass/charts.py

import matplotlib.pyplot as plt

def create_pie_chart(values: list[int], labels: list[str], filename: str):
    """
    Erstellt ein Tortendiagramm und speichert es als PNG.
    :param values: Liste der Werte (z.B. [Anwesend, Fehlend]).
    :param labels: Zugehörige Labels (z.B. ["Anwesend","Fehlend"]).
    :param filename: Pfad zur Ausgabedatei, z.B. "child_a.png".
    """
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.axis("equal")           # Kreis rund zeichnen
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
