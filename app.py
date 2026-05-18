import streamlit as st
import networkx as nx
from pathlib import Path
from pyvis.network import Network
import streamlit.components.v1 as components
import random

st.set_page_config(
    page_title="Genre Network Explorer",
    layout="wide"
)

DATA_PATH = Path("data/genre_network.gexf")


@st.cache_data
def load_graph():
    return nx.read_gexf(DATA_PATH)


G = load_graph()

# Use only the largest connected component.
connected_components = sorted(nx.connected_components(G), key=len, reverse=True)
giant_nodes = set(connected_components[0])
G_giant = G.subgraph(giant_nodes).copy()

st.title("From Metal to Pop")
st.subheader("Exploring musical genres through network science")

st.write(
    "Discover how musical genres connect through shared audio characteristics."
)

genres = sorted(G_giant.nodes())


if "source_genre" not in st.session_state:
    st.session_state.source_genre = "metal" if "metal" in genres else genres[0]

if "target_genre" not in st.session_state:
    st.session_state.target_genre = "pop" if "pop" in genres else genres[1]

col1, col2 = st.columns(2)

with col1:
    source = st.selectbox(
        "Start genre",
        genres,
        index=genres.index(st.session_state.source_genre),
        key="source_genre"
    )

with col2:
    target = st.selectbox(
        "Target genre",
        genres,
        index=genres.index(st.session_state.target_genre),
        key="target_genre"
    )

# Convert similarity into distance for shortest path search.
for u, v, data in G_giant.edges(data=True):
    similarity = float(data.get("weight", 1.0))
    data["distance"] = 1 - similarity

random_col1, random_col2 = st.columns([1, 3])

with random_col1:
    if st.button("Random journey"):
        random_source, random_target = random.sample(genres, 2)

        st.session_state.source_genre = random_source
        st.session_state.target_genre = random_target

        st.rerun()

with random_col2:
    st.info(f"Current journey: {source} → {target}")

if st.button("Find transition path"):
    try:
        path = nx.shortest_path(
            G_giant,
            source=source,
            target=target,
            weight="distance"
        )

        st.subheader("Suggested transition route")

        path_text = ""
        for i, genre in enumerate(path):
            if i < len(path) - 1:
                path_text += f"**{genre}** → "
            else:
                path_text += f"**{genre}**"

        st.markdown(path_text)

        st.subheader("Why these transitions?")

        for i in range(len(path) - 1):
            g1 = path[i]
            g2 = path[i + 1]
            similarity = float(G_giant[g1][g2].get("weight", 0))

            st.write(
                f"**{g1} → {g2}** "
                f"(similarity = {similarity:.3f})"
            )

    except nx.NetworkXNoPath:
        st.error("No path found between these genres.")


show_network = st.checkbox(
    "Show interactive network",
    value=False
)

st.caption("For the best experience, we recommend using a PC. Mobile devices may run the network visualization more slowly.")

if show_network:
    st.divider()
    st.subheader("Interactive Genre Network")

    st.write(
        "Use the search box inside the network to focus on a genre without reloading the page."
    )

    net = Network(
        height="700px",
        width="100%",
        bgcolor="#111111",
        font_color="white"
    )

    community_colors = {
        "0": "#B57EDC",
        "1": "#FF5C8A",
        "2": "#F5A623",
        "3": "#35C9FF",
        "4": "#2AA198",
        "5": "#7ED321"
    }

    for node, data in G_giant.nodes(data=True):
        community = str(data.get("community", "0"))
        degree = G_giant.degree(node)

        net.add_node(
            node,
            label=node if degree >= 5 else "",
            color=community_colors.get(community, "#999999"),
            size=8 + degree * 0.7,
            title=f"{node}<br>Degree: {degree}"
        )

    for u, v, data in G_giant.edges(data=True):
        similarity = float(data.get("weight", 1.0))

        net.add_edge(
            u,
            v,
            value=similarity,
            color="rgba(180,180,180,0.25)",
            title=f"Similarity: {similarity:.3f}"
        )

    net.force_atlas_2based(
        gravity=-120,
        central_gravity=0.01,
        spring_length=180,
        spring_strength=0.03,
        damping=0.8
    )

    net.save_graph("graph.html")

    with open("graph.html", "r", encoding="utf-8") as f:
        html = f.read()

    genre_options = "\n".join(
        [f'<option value="{genre}"></option>' for genre in sorted(G_giant.nodes())]
    )

    search_box = f"""
    <div style="
        padding: 12px;
        background: #111111;
        color: white;
        font-family: Arial, sans-serif;
    ">
        <label for="genreSearch" style="font-weight: bold; margin-right: 10px;">
            Search genre:
        </label>

        <input
            id="genreSearch"
            list="genreOptions"
            placeholder="type a genre, e.g. metal, pop, edm"
            style="
                padding: 9px;
                border-radius: 6px;
                min-width: 280px;
                border: 1px solid #444;
                background: #222222;
                color: white;
            "
        />

        <datalist id="genreOptions">
            {genre_options}
        </datalist>

        <button onclick="focusSelectedGenre()" style="
            padding: 9px 14px;
            margin-left: 8px;
            border-radius: 6px;
            border: none;
            background: #1DB954;
            color: white;
            font-weight: bold;
            cursor: pointer;
        ">
            Focus
        </button>

        <span id="searchMessage" style="
            margin-left: 12px;
            color: #ff7777;
            font-size: 13px;
        "></span>
    </div>

    <script type="text/javascript">
    const validGenres = new Set({sorted(G_giant.nodes())});

    function focusSelectedGenre() {{
        var selectedGenre = document.getElementById("genreSearch").value.trim();
        var message = document.getElementById("searchMessage");

        if (!validGenres.has(selectedGenre)) {{
            message.textContent = "Genre not found.";
            return;
        }}

        message.textContent = "";

        if (typeof network !== "undefined") {{
            network.focus(selectedGenre, {{
                scale: 2.5,
                animation: {{
                    duration: 800,
                    easingFunction: "easeInOutQuad"
                }}
            }});

            network.selectNodes([selectedGenre]);
        }}
    }}
    </script>
    """

    html = html.replace("<body>", "<body>" + search_box)

    components.html(html, height=780)