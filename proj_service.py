from flask import Flask, request, jsonify
from pyproj import CRS, Transformer

# Initialize the Flask application
app = Flask(__name__)

@app.route('/transform', methods=['GET'])
def transform_crs():
    """
    Transform coordinates from EPSG:4326 to a client-provided EPSG code.
    """
    try:
        # Read the target EPSG code from the query parameters
        target_epsg = request.args.get('epsg', type=int)

        if not target_epsg:
            return jsonify({"error": "Target EPSG code is required as a query parameter."}), 400

        # Create a transformer object
        transformer = Transformer.from_crs(4326, target_epsg)

        # Get the PROJ string
        proj_string = transformer.to_proj4()

        return jsonify({
            "source_epsg": 4326,
            "target_epsg": target_epsg,
            "proj4": proj_string
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the application
if __name__ == "__main__":
    app.run(debug=True)
