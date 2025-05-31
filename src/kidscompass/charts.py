# src/kidscompass/charts.py

import matplotlib.pyplot as plt

def create_pie_chart(values: list[int], labels: list[str], filename: str):
    """
    Erstellt ein Tortendiagramm und speichert es als PNG.
    :param values: Liste der Werte (z.B. [Anwesend, Fehlend]).
    :param labels: Zugehörige Labels (z.B. ["Anwesend","Fehlend"]).
    :param filename: Pfad zur Ausgabedatei, z.B. "child_a.png".
    """
    total = sum(values)
    # Wenn keine Daten da sind, lege ein kleines Platzhalter‐Bild an
    if total == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center", fontsize=14)
        ax.axis("off")
        fig.savefig(filename, bbox_inches="tight")
        plt.close(fig)
        return

    # Ansonsten ganz normal zeichnen
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.axis("equal")           # Kreis rund zeichnen
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
