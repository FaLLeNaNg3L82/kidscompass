# src/kidscompass/charts.py

import matplotlib.pyplot as plt

def create_pie_chart(values: list[int], labels: list[str], filename: str, colors: list[str] = None, return_handles: bool = False, subtitle: str = None):
    """
    Erstellt ein Tortendiagramm und speichert es als PNG.
    :param values: Liste der Werte (z.B. [Anwesend, Fehlend]).
    :param labels: Zugehörige Labels (z.B. ["Anwesend","Fehlend"]).
    :param filename: Pfad zur Ausgabedatei, z.B. "child_a.png".
    :param colors: (Optional) Liste von Farben für die Segmente.
    :param return_handles: Wenn True, gibt (wedges, texts, autotexts) zurück (für weitere Anpassungen).
    :param subtitle: (Optional) Text, der unter das Diagramm geschrieben wird.
    """
    total = sum(values)
    # Wenn keine Daten da sind, lege ein kleines Platzhalter‐Bild an
    if total == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center", fontsize=14)
        ax.axis("off")
        if subtitle:
            fig.text(0.5, 0.02, subtitle, ha="center", va="bottom", fontsize=22, fontweight='bold')
        fig.savefig(filename, bbox_inches="tight")
        plt.close(fig)
        if return_handles:
            return [0], [0], [0]
        return

    # Ansonsten ganz normal zeichnen
    fig, ax = plt.subplots()
    if colors is not None:
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.1f%%", colors=colors)
    else:
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.axis("equal")           # Kreis rund zeichnen
    if subtitle:
        fig.text(0.5, 0.02, subtitle, ha="center", va="bottom", fontsize=22, fontweight='bold')
    fig.savefig(filename, bbox_inches="tight")
    if return_handles:
        plt.close(fig)
        return wedges, texts, autotexts
    plt.close(fig)
