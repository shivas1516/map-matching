from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
from pytrack.graph import graph, distance
from pytrack.analytics import visualization
from pytrack.matching import candidate, mpmatching_utils, mpmatching

app = Flask(__name__)

def load_and_process_data(file):
    df = pd.read_csv(file)
    latitude = df["latitude"].to_list()
    longitude = df["longitude"].to_list()
    points = [(lat, lon) for lat, lon in zip(latitude, longitude)]
    return points

def perform_map_matching(points):
    # Create BBOX
    north, east = np.max(np.array([*points]), 0)
    south, west = np.min(np.array([*points]), 0)
    
    # Extract road graph
    G = graph.graph_from_bbox(*distance.enlarge_bbox(north, south, west, east, 500), simplify=True, network_type='drive')
    
    # Extract candidates
    G_interp, candidates = candidate.get_candidates(G, points, interp_dist=5, closest=True, radius=30)
    
    # Extract trellis DAG graph
    trellis = mpmatching_utils.create_trellis(candidates)
    
    # Perform the map-matching process
    path_prob, predecessor = mpmatching.viterbi_search(G_interp, trellis, "start", "target")
    
    return G, G_interp, candidates, trellis, path_prob, predecessor

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    if file and file.filename.endswith('.csv'):
        points = load_and_process_data(file)
        
        # Perform map matching using pytrack
        G, G_interp, candidates, trellis, path_prob, predecessor = perform_map_matching(points)
        
        # Create a map centered at the first point
        loc = (np.mean([p[0] for p in points]), np.mean([p[1] for p in points]))
        maps = visualization.Map(location=loc, zoom_start=15)
        
        # Add the graph to the map
        maps.add_graph(G, plot_nodes=True)
        
        # Draw the candidates on the map
        maps.draw_candidates(candidates, 30)
        
        # Draw the map-matching path
        maps.draw_path(G_interp, trellis, predecessor)
        
        # Save the map visualization as an HTML file
        maps.save('static/map.html')
        
        return redirect(url_for('index'))
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
