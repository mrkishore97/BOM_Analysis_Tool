import pandas as pd
import math
import tempfile
import os
from pyvis.network import Network
import streamlit as st

def visualize_bom_streamlit(df):
    """
    Visualize BOM in Streamlit using PyVis network with:
    - Color coding
    - Cost-based node sizing
    - Fixed positions for 5M nodes and code 6 node
    - Interactive edge highlighting on click
    - Legend
    - Download option
    """
    from pyvis.network import Network
    import math
    import tempfile
    import os

    # --- Define color mapping for codes ---
    color_map = {
        "6": "#636EFA",   # Blue
        "2M": "#EF553B",  # Red
        "3M": "#00CC96",  # Green
        "4M": "#AB63FA",  # Purple
        "5M": "#FFA15A",  # Orange
        "2B": "#19D3F3",  # Cyan
        "RAW": "#A9A9A9"
    }

    # --- Create PyVis network ---
    net = Network(height="800px", width="100%", directed=True, bgcolor="#ffffff", font_color="#000000")
    net.barnes_hut(gravity=-40000, central_gravity=0.0001, spring_length=30, spring_strength=0.1, damping=0.09, overlap=30)

    max_cost = df["total_costs"].max()
    min_cost = df["total_costs"].min()
    def scale_size(cost):
        return 25 if max_cost == min_cost else 20 + (30 * (cost - min_cost) / (max_cost - min_cost))

    def format_currency(value):
        return f"${value:,.2f}"

    fiveM_nodes = df[df["code"] == "5M"]["index"].tolist()
    n_fiveM = len(fiveM_nodes)
    fiveM_positions = {}

    # --- Add nodes and edges ---
    for idx, row in df.iterrows():
        node_label = f"{row['part_number']}\n{format_currency(row['total_costs'])}"
        title_text = f"""Part: {row['part_number']}
Description: {row['description'][:80]}...
COST BREAKDOWN:
Material Costs: {format_currency(row['material_costs'])}
Outside Costs: {format_currency(row['outside_costs'])}
Total Costs: {format_currency(row['total_costs'])}
Level: {row['level']} | Code: {row['code']} | Unit: {row['unit']}"""

        color = color_map.get(str(row["code"]), "#A9A9A9")
        size = scale_size(row["total_costs"])
        node_kwargs = {"label": node_label, "title": title_text, "color": color, "size": size, "font": {"size": 12}, "level": row["level"]}

        # Fixed positions for 5M nodes
        if str(row["code"]) == "5M":
            pos = fiveM_nodes.index(row["index"])
            angle = 2 * math.pi * pos / n_fiveM
            radius = 5000
            x = -100 + radius * math.cos(angle)
            y = -100 + radius * math.sin(angle)
            node_kwargs.update({"x": x, "y": y, "fixed": True})
            fiveM_positions[row["index"]] = (x, y)

        # Fix code 6 node
        elif str(row["code"]) == "6":
            node_kwargs.update({"x": -100, "y": -100, "fixed": True})

        net.add_node(row["index"], **node_kwargs)

        # Add edge to parent
        if "." in str(row["index"]):
            parent = ".".join(str(row["index"]).split(".")[:-1])
            if parent in df["index"].values:
                parent_row = df[df["index"] == parent].iloc[0]
                parent_color = color_map.get(str(parent_row["code"]), "#A9A9A9")
                net.add_edge(parent, row["index"], color=parent_color, width=1)

    # --- Save temporary HTML ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        temp_html_path = tmp_file.name
    net.save_graph(temp_html_path)

    # --- Read HTML and inject custom JS + legend ---
    with open(temp_html_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    edge_highlight_js = """
    <style>
        .legend-box {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: white;
            border: 2px solid #333;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 1000;
            font-family: Arial, sans-serif;
            font-size: 14px;
            min-width: 150px;
        }
        .legend-title { font-weight: bold; margin-bottom: 10px; text-align: center; color: #333; }
        .legend-item { display: flex; align-items: center; margin-bottom: 5px; }
        .legend-color { width: 16px; height: 16px; margin-right: 8px; border-radius: 3px; border: 1px solid #ccc; }
        .legend-label { color: #333; }
    </style>
    <script type="text/javascript">
        var lastHighlightedEdges = [];
        var originalEdgeColors = {};
        edges.forEach(function(edge) { originalEdgeColors[edge.id] = edge.color; });

        network.on("click", function (params) {
            lastHighlightedEdges.forEach(function(edgeId) {
                network.updateEdge(edgeId, {color: originalEdgeColors[edgeId]||'#848484', width:1});
            });
            lastHighlightedEdges = [];
            if(params.nodes.length>0){
                var selectedNode=params.nodes[0];
                network.getConnectedEdges(selectedNode).forEach(function(edgeId){
                    network.updateEdge(edgeId,{color:originalEdgeColors[edgeId]||'#848484',width:5});
                    lastHighlightedEdges.push(edgeId);
                });
            }
        });
    </script>
    """

    legend_html = """
    <div class="legend-box">
        <div class="legend-title">Node Types</div>
        <div class="legend-item"><div class="legend-color" style="background-color: #636EFA;"></div><div class="legend-label">6 - Main Assembly</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #EF553B;"></div><div class="legend-label">2M - Manufactured in House</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #00CC96;"></div><div class="legend-label">3M - Outside service (We supply Material)</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #AB63FA;"></div><div class="legend-label">4M - Assemblies</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #FFA15A;"></div><div class="legend-label">5M - Operations</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #19D3F3;"></div><div class="legend-label">2B - Bought out</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #A9A9A9;"></div><div class="legend-label">RAW - Raw Material</div></div>
    </div>
    """

    html_content = html_content.replace("</body>", edge_highlight_js + legend_html + "\n</body>")

    # Write modified HTML back
    with open(temp_html_path, 'w', encoding='utf-8') as file:
        file.write(html_content)

    # Return both the HTML content and file path for download
    with open(temp_html_path, 'r', encoding='utf-8') as file:
        components_html = file.read()

    return components_html, temp_html_path