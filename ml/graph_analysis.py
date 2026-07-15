"""
Graph analysis - two networks built from the fleet/order data:

1. Category co-occurrence graph (from hire_order_items): categories hired
   together on the same order become connected edges, weighted by frequency.
   Used for community detection (does the graph recover the real project
   clusters?) and centrality (which categories are the most "connective"
   cross-sell hubs).

2. Depot fleeting network (from stock_transfers): directed graph of
   depot-to-depot stock movements, weighted by transfer volume. Used to find
   which depot is the structural hub of the redistribution network.
"""
import json
from pathlib import Path
from itertools import combinations
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "ml" / "reports"
IMG = ROOT / "docs" / "images"
REPORTS.mkdir(parents=True, exist_ok=True)

NAVY, GREEN, BLUE, SLATE, RED, AMBER = "#0C1114", "#009B66", "#2A7ACC", "#3C5667", "#C0392B", "#D98E04"
PALETTE = [GREEN, BLUE, AMBER, "#8FA8B8", "#17B378", RED, SLATE, "#4A9FE0", "#9085E9", "#E87BA4"]

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "text.color": NAVY, "figure.facecolor": "white",
})

# =============================================================================
# 1) CATEGORY CO-OCCURRENCE GRAPH
# =============================================================================
items = pd.read_csv(RAW / "hire_order_items.csv")
baskets = items.groupby("order_id")["category"].apply(list)

edge_weights = Counter()
node_weights = Counter()
for basket in baskets:
    cats = sorted(set(basket))
    for c in cats:
        node_weights[c] += 1
    for a, b in combinations(cats, 2):
        edge_weights[(a, b)] += 1

G = nx.Graph()
for cat, w in node_weights.items():
    G.add_node(cat, weight=w)
for (a, b), w in edge_weights.items():
    if w >= 3:  # drop very weak/noisy edges
        G.add_edge(a, b, weight=w)

# for layout/visual clarity only: keep each node's 3 strongest edges (the
# centrality/community stats above are computed on the full graph, this
# pruned copy is just to stop a near-complete graph collapsing spring_layout)
G_viz = nx.Graph()
G_viz.add_nodes_from(G.nodes(data=True))
kept_edges = set()
for n in G.nodes():
    neighbors = sorted(G[n].items(), key=lambda kv: -kv[1]["weight"])[:3]
    for nbr, data in neighbors:
        kept_edges.add(tuple(sorted((n, nbr))))
for a, b in kept_edges:
    G_viz.add_edge(a, b, weight=G[a][b]["weight"])

# centrality
degree_c = nx.degree_centrality(G)
between_c = nx.betweenness_centrality(G, weight="weight")
communities = list(nx.algorithms.community.greedy_modularity_communities(G, weight="weight"))
community_of = {}
for i, comm in enumerate(communities):
    for node in comm:
        community_of[node] = i

cat_graph_stats = pd.DataFrame({
    "category": list(G.nodes()),
    "order_appearances": [node_weights[n] for n in G.nodes()],
    "degree_centrality": [round(degree_c[n], 4) for n in G.nodes()],
    "betweenness_centrality": [round(between_c[n], 4) for n in G.nodes()],
    "community": [community_of.get(n, -1) for n in G.nodes()],
}).sort_values("betweenness_centrality", ascending=False)
cat_graph_stats.to_csv(REPORTS / "category_graph_centrality.csv", index=False)

# visualize (pruned graph for layout clarity; color/size still reflect full-graph stats)
fig, ax = plt.subplots(figsize=(10, 8.5), dpi=200)
pos = nx.kamada_kawai_layout(G_viz, weight="weight")
node_sizes = [300 + node_weights[n] * 1.1 for n in G_viz.nodes()]
node_colors = [PALETTE[community_of.get(n, 0) % len(PALETTE)] for n in G_viz.nodes()]
edge_widths = [0.6 + G_viz[u][v]["weight"] / 15 for u, v in G_viz.edges()]
nx.draw_networkx_edges(G_viz, pos, width=edge_widths, edge_color="#C3CDD3", alpha=0.8, ax=ax)
nx.draw_networkx_nodes(G_viz, pos, node_size=node_sizes, node_color=node_colors, edgecolors="white",
                        linewidths=1.2, alpha=0.92, ax=ax)
label_pos = {n: (x, y + 0.06) for n, (x, y) in pos.items()}
nx.draw_networkx_labels(G_viz, label_pos, font_size=8, font_color=NAVY, font_weight="bold", ax=ax)
ax.set_title("Category Co-Occurrence Network — \"Frequently Hired Together\"",
              fontsize=13, fontweight="bold", color=NAVY, loc="left", pad=14)
fig.text(0.02, 0.02, "Node size = order frequency  ·  Edge width = co-occurrence strength  ·  "
                       "Color = detected community (project-type cluster)  ·  "
                       "Shown: each category's 3 strongest links, for readability",
         fontsize=8.5, color=SLATE)
ax.axis("off")
plt.tight_layout(rect=(0, 0.03, 1, 1))
plt.savefig(IMG / "category_graph.png", facecolor="white")
plt.close()

# =============================================================================
# 2) DEPOT FLEETING NETWORK (directed)
# =============================================================================
flows = pd.read_csv(ROOT / "data" / "processed" / "depot_flows.csv")
DG = nx.DiGraph()
for _, r in flows.iterrows():
    DG.add_edge(r["from_depot"], r["to_depot"], weight=int(r["count"]))

in_strength = {n: sum(d["weight"] for _, _, d in DG.in_edges(n, data=True)) for n in DG.nodes()}
out_strength = {n: sum(d["weight"] for _, _, d in DG.out_edges(n, data=True)) for n in DG.nodes()}
between_depot = nx.betweenness_centrality(DG, weight="weight")
pagerank_depot = nx.pagerank(DG, weight="weight")

depot_graph_stats = pd.DataFrame({
    "depot": list(DG.nodes()),
    "inbound_transfers": [in_strength.get(n, 0) for n in DG.nodes()],
    "outbound_transfers": [out_strength.get(n, 0) for n in DG.nodes()],
    "net_flow": [in_strength.get(n, 0) - out_strength.get(n, 0) for n in DG.nodes()],
    "betweenness_centrality": [round(between_depot[n], 4) for n in DG.nodes()],
    "pagerank": [round(pagerank_depot[n], 4) for n in DG.nodes()],
}).sort_values("pagerank", ascending=False)
depot_graph_stats.to_csv(REPORTS / "depot_graph_centrality.csv", index=False)

fig, ax = plt.subplots(figsize=(8.5, 7.5), dpi=200)
pos2 = nx.circular_layout(DG, scale=0.85)
node_sizes2 = [500 + pagerank_depot[n] * 4500 for n in DG.nodes()]
for u, v, d in DG.edges(data=True):
    nx.draw_networkx_edges(DG, pos2, edgelist=[(u, v)], width=0.5 + d["weight"] / 5,
                            edge_color=BLUE, alpha=0.55, connectionstyle="arc3,rad=0.12",
                            arrowsize=14, node_size=node_sizes2, ax=ax)
nx.draw_networkx_nodes(DG, pos2, node_size=node_sizes2, node_color=GREEN, edgecolors="white",
                        linewidths=1.5, alpha=0.92, ax=ax)
# push labels outward from the circle center so they never overlap the node
label_pos2 = {n: (x * 1.22, y * 1.22) for n, (x, y) in pos2.items()}
nx.draw_networkx_labels(DG, label_pos2, font_size=9.5, font_color=NAVY, font_weight="bold", ax=ax)
ax.set_title("Depot Fleeting Network — Node Size = PageRank (Hub Importance)",
              fontsize=13, fontweight="bold", color=NAVY, loc="left", pad=14)
ax.set_xlim(-1.5, 1.5)
ax.set_ylim(-1.5, 1.5)
ax.axis("off")
plt.tight_layout()
plt.savefig(IMG / "depot_graph.png", facecolor="white")
plt.close()

# =============================================================================
# Summary
# =============================================================================
summary = {
    "category_graph": {
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "communities_detected": len(communities),
        "top_hub_categories": cat_graph_stats.head(5)[["category", "betweenness_centrality"]].to_dict("records"),
    },
    "depot_graph": {
        "top_hub_depot": depot_graph_stats.iloc[0]["depot"],
        "top_hub_pagerank": float(depot_graph_stats.iloc[0]["pagerank"]),
        "biggest_net_importer": depot_graph_stats.sort_values("net_flow", ascending=False).iloc[0]["depot"],
        "biggest_net_exporter": depot_graph_stats.sort_values("net_flow").iloc[0]["depot"],
    },
}
(REPORTS / "graph_analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nSaved: {IMG/'category_graph.png'}, {IMG/'depot_graph.png'}")
